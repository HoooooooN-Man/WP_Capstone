"""
api/users/cohort_portfolio.py
==============================
2026-05-19 v3 — ML 코호트별 종목 추천 + 사용자 직접 편집 (빼기/추가).

설계 (사용자 정정):
  - 수량/자본 계산 X — 추천 종목 리스트만
  - 사용자가 추천 10종에서 직접 빼거나 다른 종목 추가
  - quantity placeholder 0 으로 INSERT (NOT NULL 충족), 사용자가 실제 매수 시 quantity 채움
  - "리밸런싱" = 사용자가 종목 list 편집하여 다시 apply

엔드포인트:
  GET  /users/me/portfolio/cohort/{cohort}/preview
       - 8001 ML API → TOP K=10 picks 종목 list (ticker/name/score/signal/현재가)
  POST /users/me/portfolio/cohort/{cohort}/apply
       - body picks=[tickers] 있으면 그 종목 list 로 INSERT (사용자 편집 결과)
       - body picks 없으면 ML 자동 fetch 사용
       - 기존 동일 cohort holdings soft-delete 후 신규 INSERT (quantity=0 placeholder)
  GET  /users/me/portfolio/cohort/{cohort}
       - 현재 보유 cohort 종목 (enrich)
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import User, UserHolding, UserHoldingHistory
from .users import _require_current_user
from .portfolio import _audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users/me/portfolio/cohort", tags=["cohort_portfolio"])

VALID_COHORTS = {"conservative", "balanced", "growth", "dividend", "value"}
ML_API_BASE = os.getenv("ML_API_BASE", "http://127.0.0.1:8001")
TOP_K = 10


# ── 스키마 ────────────────────────────────────────────────────────────────────

class CohortPick(BaseModel):
    """추천 종목 1건 — 수량/자본 계산 없음, 정보 표시만."""
    ticker:        str
    name:          Optional[str] = None
    sector:        Optional[str] = None
    score:         Optional[float] = None
    tier:          Optional[str] = None
    signal_label:  Optional[str] = None
    current_price: float


class CohortPreview(BaseModel):
    cohort:        str
    n_picks:       int
    picks:         List[CohortPick]
    is_advice:     bool = False


class ApplyRequest(BaseModel):
    """apply body. tickers 지정 시 사용자 편집 결과 그대로 INSERT.

    tickers 미지정/빈 list 이면 ML 자동 TOP K 사용.
    수량 정보 없이 종목 list 만 — quantity=0 placeholder 로 INSERT.
    """
    tickers: Optional[List[str]] = None


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _normalize_cohort(c: str) -> str:
    cl = (c or "").strip().lower()
    if cl not in VALID_COHORTS:
        raise HTTPException(
            status_code=400,
            detail=f"허용된 cohort: {sorted(VALID_COHORTS)}",
        )
    return cl


def _resolve_trading_date(target_date: date) -> str:
    """target_date 이하 가장 가까운 영업일 — scores 테이블 기반. 없으면 target 그대로."""
    from .portfolio import _get_market_con
    con = _get_market_con()
    if con is None:
        return target_date.isoformat()
    try:
        row = con.execute(
            "SELECT CAST(MAX(date) AS VARCHAR) FROM scores WHERE date <= ? AND model_version='regime_dep'",
            [target_date.isoformat()],
        ).fetchone()
        if row and row[0]:
            actual = row[0]
            if "-" not in actual and len(actual) == 8:
                actual = f"{actual[:4]}-{actual[4:6]}-{actual[6:8]}"
            return actual
    except Exception as e:
        logger.warning("nearest trading date lookup 실패: %s", e)
    return target_date.isoformat()


def _fetch_ml_picks(cohort: str, top_k: int = TOP_K, as_of: Optional[str] = None) -> list[dict]:
    """8001 ML API 호출 — cohort 별 TOP K 추천. as_of 지정 시 그 시점 추천."""
    params: dict = {"cohort": cohort, "diversify": "correlation", "top_k": top_k}
    if as_of:
        params["date"] = as_of
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get(f"{ML_API_BASE}/api/v1/stocks/recommendations", params=params)
            r.raise_for_status()
            data = r.json()
            return data.get("items") or []
    except httpx.HTTPError as e:
        logger.warning("ML API 호출 실패 (%s, as_of=%s): %s", cohort, as_of, e)
        raise HTTPException(status_code=503, detail=f"ML 추천 서비스 응답 없음: {e}")


def _build_preview(cohort: str, as_of: Optional[str] = None) -> CohortPreview:
    """ML picks → 종목 list 반환. as_of 지정 시 그 시점 추천 (백테 모드)."""
    items = _fetch_ml_picks(cohort, TOP_K, as_of=as_of)
    picks: list[CohortPick] = []
    for it in items:
        price = float(it.get("close") or 0)
        if price <= 0:
            continue
        picks.append(CohortPick(
            ticker=str(it.get("ticker") or "").zfill(6),
            name=it.get("name"),
            sector=it.get("sector"),
            score=it.get("score"),
            tier=it.get("tier"),
            signal_label=it.get("signal_label"),
            current_price=price,
        ))
    return CohortPreview(cohort=cohort, n_picks=len(picks), picks=picks)


_all_stocks_cache: dict[str, dict] = {}
_all_stocks_cache_ts: float = 0.0


def _fetch_prices_for_tickers(tickers: list[str]) -> dict[str, dict]:
    """사용자가 추가한 외부 종목의 current_price/name/sector.

    ML API 의 recommendations?top_k=0 (전체 ~2,300 종목) 으로 cache 후 lookup.
    cache TTL 5분 — preview 와 동기화.
    """
    global _all_stocks_cache, _all_stocks_cache_ts
    import time as _t
    if not tickers:
        return {}
    if _t.time() - _all_stocks_cache_ts > 300 or not _all_stocks_cache:
        try:
            with httpx.Client(timeout=15.0) as client:
                r = client.get(
                    f"{ML_API_BASE}/api/v1/stocks/recommendations",
                    params={"top_k": 0},
                )
                r.raise_for_status()
                data = r.json()
                fresh: dict[str, dict] = {}
                for it in (data.get("items") or []):
                    t = str(it.get("ticker") or "").zfill(6)
                    if not t:
                        continue
                    fresh[t] = {
                        "name": it.get("name"),
                        "sector": it.get("sector"),
                        "close": float(it.get("close") or 0),
                    }
                _all_stocks_cache = fresh
                _all_stocks_cache_ts = _t.time()
        except httpx.HTTPError as e:
            logger.warning("전체 stocks 캐시 갱신 실패: %s", e)
    return {t: _all_stocks_cache[t] for t in tickers if t in _all_stocks_cache}


# ── 엔드포인트 ───────────────────────────────────────────────────────────────

@router.get("/{cohort}/preview", response_model=CohortPreview, summary="코호트 추천 종목 list (수량 X)")
def preview_cohort_portfolio(
    cohort: str,
    days_ago: int = Query(0, ge=0, le=365, description="0=현재 추천, N=N일 전 ML 추천"),
    current_user: User = Depends(_require_current_user),
):
    """ML cohort TOP K 추천. days_ago=0 이면 현재, N 이면 N일 전 시점 추천 (백테 모드)."""
    c = _normalize_cohort(cohort)
    if days_ago == 0:
        return _build_preview(c)
    from datetime import timedelta as _td
    target = date.today() - _td(days=days_ago)
    as_of = _resolve_trading_date(target)
    return _build_preview(c, as_of=as_of)


@router.post("/{cohort}/apply", summary="코호트 종목 list 저장 (사용자 편집 반영)")
def apply_cohort_portfolio(
    cohort: str,
    body: ApplyRequest = ApplyRequest(),
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """기존 동일 cohort 종목 soft-delete + 신규 INSERT (quantity=0 placeholder).

    body.tickers 지정 시 그 종목들로 (사용자 편집 결과), 미지정이면 ML 자동 TOP K.
    quantity=0 = "추천만 저장, 실제 매수 안 함" 의미. 사용자가 추후 마이 포트폴리오에서 수량 채움.
    """
    c = _normalize_cohort(cohort)

    # 1. 종목 list 결정
    if body.tickers:
        tickers = [str(t).zfill(6) for t in body.tickers if t]
        price_meta = _fetch_prices_for_tickers(tickers)
        picks: list[CohortPick] = []
        for t in tickers:
            m = price_meta.get(t, {})
            price = float(m.get("close") or 0)
            if price <= 0:
                continue
            picks.append(CohortPick(
                ticker=t,
                name=m.get("name"),
                sector=m.get("sector"),
                current_price=price,
            ))
    else:
        preview = _build_preview(c)
        picks = preview.picks
    if not picks:
        raise HTTPException(status_code=400, detail="저장할 종목이 없습니다")

    # 2. 기존 동일 cohort holdings soft-delete (audit)
    now = datetime.utcnow()
    existing = (
        db.query(UserHolding)
        .filter(
            UserHolding.user_id == current_user.user_id,
            UserHolding.cohort == c,
            UserHolding.deleted_at.is_(None),
        )
        .all()
    )
    for h in existing:
        h.deleted_at = now
        _audit(db, h, action="rebalance_deleted")

    # 3. 신규 INSERT — quantity=0 placeholder (NOT NULL constraint 충족)
    today = date.today()
    inserted: list[dict] = []
    for p in picks:
        avg_price_dec = Decimal(str(p.current_price)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP,
        )
        new_h = UserHolding(
            user_id=current_user.user_id,
            ticker=p.ticker,
            quantity=0,                                  # placeholder
            avg_price=avg_price_dec,
            bought_at=today,
            memo=f"[cohort={c}] {p.name or p.ticker} · score={p.score or '-'}",
            cohort=c,
        )
        db.add(new_h)
        db.flush()
        _audit(db, new_h, action="cohort_applied")
        inserted.append({
            "ticker": p.ticker,
            "name": p.name,
            "current_price": p.current_price,
            "score": p.score,
            "signal_label": p.signal_label,
        })
    db.commit()
    return {
        "cohort": c,
        "n_picks": len(inserted),
        "picks": inserted,
        "is_advice": False,
    }


@router.post("/{cohort}/historical-test", summary="과거 시점에 모델이 추천했던 종목 백테 (look-ahead 차단)")
def historical_test(
    cohort: str,
    days_ago: int = Query(30, ge=1, le=365, description="N일 전 시점의 ML 추천"),
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """**N일 전 시점에 모델이 추천했던** TOP K 종목을 그 시점 종가로 entry.

    핵심: 오늘 추천 종목을 N일 전 가격으로 시뮬 = look-ahead bias.
    이 endpoint 는 ML API 의 `?date=YYYY-MM-DD` 를 사용해 진짜 그 시점의 cohort
    추천을 가져옴 → 그 종목들이 오늘까지 어떻게 됐는지 = 진정한 forward 백테.
    """
    from datetime import timedelta as _td
    c = _normalize_cohort(cohort)
    target_date = date.today() - _td(days=days_ago)
    as_of_str = _resolve_trading_date(target_date)
    target_date = date.fromisoformat(as_of_str)

    # 1. N일 전 ML 추천 종목 (그 시점 cohort TOP K, close = 그 시점 종가)
    items = _fetch_ml_picks(c, TOP_K, as_of=as_of_str)
    actual_as_of = as_of_str
    if not items:
        raise HTTPException(status_code=404, detail=f"{as_of_str} 시점 추천 결과 없음")

    # 2. 기존 cohort holdings soft-delete
    now = datetime.utcnow()
    existing = (
        db.query(UserHolding)
        .filter(
            UserHolding.user_id == current_user.user_id,
            UserHolding.cohort == c,
            UserHolding.deleted_at.is_(None),
        )
        .all()
    )
    for h in existing:
        h.deleted_at = now
        _audit(db, h, action="hist_replaced")

    # 3. 신규 INSERT — entry_price = 그 시점 close (ML 응답의 close 그대로)
    target_date_dt = date.fromisoformat(actual_as_of) if isinstance(actual_as_of, str) else target_date
    inserted = 0
    for it in items:
        ticker = str(it.get("ticker") or "").zfill(6)
        if not ticker:
            continue
        entry_price = float(it.get("close") or 0)
        if entry_price <= 0:
            continue
        avg_price_dec = Decimal(str(entry_price)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP,
        )
        new_h = UserHolding(
            user_id=current_user.user_id,
            ticker=ticker,
            quantity=0,
            avg_price=avg_price_dec,
            bought_at=target_date_dt,
            memo=f"[cohort={c}] {actual_as_of} ML 추천 · score={it.get('score')} · {it.get('name') or ticker}",
            cohort=c,
        )
        db.add(new_h)
        db.flush()
        _audit(db, new_h, action="cohort_hist_test")
        inserted += 1
    db.commit()
    return {
        "cohort": c,
        "as_of": actual_as_of,
        "days_ago": days_ago,
        "n_picks": inserted,
        "message": f"{actual_as_of} 시점 ML 추천 종목을 entry. 현재 가격 대비 수익률 확인",
    }


@router.get("/{cohort}", summary="현재 저장된 cohort 종목 list + 선정 후 수익률")
def get_cohort_portfolio(
    cohort: str,
    current_user: User = Depends(_require_current_user),
    db: Session = Depends(get_db),
):
    """cohort 종목 list + 선정 시점 가격(avg_price) 대비 현재가 수익률.

    각 종목: entry_price / entry_date / return_pct / days_since_pick
    Summary: 균등 가중 평균 수익률, best/worst pick, win_rate.
    """
    c = _normalize_cohort(cohort)
    rows = (
        db.query(UserHolding)
        .filter(
            UserHolding.user_id == current_user.user_id,
            UserHolding.cohort == c,
            UserHolding.deleted_at.is_(None),
        )
        .order_by(UserHolding.created_at.asc())
        .all()
    )
    # 최신가 + ML 메타
    tickers = list({r.ticker for r in rows})
    price_meta = _fetch_prices_for_tickers(tickers) if tickers else {}
    try:
        latest = _build_preview(c)
        score_map = {p.ticker: p for p in latest.picks}
    except Exception:
        score_map = {}

    items = []
    returns: list[float] = []
    today = date.today()
    for r in rows:
        meta = price_meta.get(r.ticker, {})
        ml = score_map.get(r.ticker)
        entry_price = float(r.avg_price)
        current_price = float(meta.get("close") or entry_price)
        return_pct = ((current_price / entry_price - 1.0) * 100.0) if entry_price > 0 else 0.0
        # B61 split detection — 비현실적 수익률 차단
        split_suspected = abs(return_pct) > 300.0
        if split_suspected:
            return_pct_out = None
        else:
            return_pct_out = round(return_pct, 2)
            returns.append(return_pct)
        days_since_pick = (today - r.bought_at).days if r.bought_at else None

        items.append({
            "id": r.id,
            "ticker": r.ticker,
            "name": (
                meta.get("name")
                or ((r.memo or "").split("·")[0].strip().split("] ")[-1] if r.memo else r.ticker)
            ),
            "sector": meta.get("sector"),
            "entry_price": round(entry_price, 2),
            "entry_date": r.bought_at.isoformat() if r.bought_at else None,
            "current_price": round(current_price, 2),
            "return_pct": return_pct_out,
            "days_since_pick": days_since_pick,
            "split_event_suspected": split_suspected,
            "score": ml.score if ml else None,
            "signal_label": ml.signal_label if ml else None,
            "in_ml_recommendation": ml is not None,
            "added_at": r.created_at.isoformat() if r.created_at else None,
        })

    # Summary — 균등 가중 평균 수익률 + 최대/최소 + 승률
    if returns:
        avg_return = sum(returns) / len(returns)
        win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100.0
        best = max(items, key=lambda x: (x.get("return_pct") or -1e9))
        worst = min(items, key=lambda x: (x.get("return_pct") or 1e9))
        summary = {
            "n_picks": len(items),
            "n_valid_returns": len(returns),
            "avg_return_pct": round(avg_return, 2),
            "best_pick": {"ticker": best["ticker"], "name": best["name"], "return_pct": best["return_pct"]},
            "worst_pick": {"ticker": worst["ticker"], "name": worst["name"], "return_pct": worst["return_pct"]},
            "win_rate_pct": round(win_rate, 1),
        }
    else:
        summary = {
            "n_picks": len(items),
            "n_valid_returns": 0,
            "avg_return_pct": None,
            "best_pick": None,
            "worst_pick": None,
            "win_rate_pct": None,
        }

    return {
        "cohort": c,
        "total": len(items),
        "items": items,
        "summary": summary,
        "is_advice": False,
    }
