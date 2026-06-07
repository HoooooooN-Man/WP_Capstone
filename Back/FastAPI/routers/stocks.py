"""
routers/stocks.py
=================
종목 추천·이력·섹터 관련 엔드포인트.
모두 /api/v1/ 접두사는 main.py에서 prefix로 부착.
"""

from __future__ import annotations

import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request

from ..services import data as svc
from ..services.ab_split import resolve_variant
from ..services.confidence import annotate_confidence
from ..services.coverage import filter_insufficient_coverage, load_ticker_days
from ..services.diversify import (
    make_correlation_sim,
    make_embedding_sim,
    make_sector_sim,
    mmr_rerank,
    normalize_diversify,
)
from ..services.market_events import detect_market_regime
from ..services.personalization import rerank_for_cohort
from ..schemas.meta import attach_meta
from ..schemas.stocks import (
    StockScore,
    StockScoreList,
    StockHistory,
    StockHistoryItem,
    SectorSummaryList,
    SectorSummaryItem,
    VersionsResponse,
    DatesResponse,
    StockSearchResult,
    StockSearchList,
    StockPrice,
    RisingStockList,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


# ── UI 메타 후처리 lite ────────────────────────────────────────────────────────
# Front_v2 가 기대하는 signal_label / star_rating / change_pct / market_cap_label 등을
# tier·score·prices(어제 대비) 로부터 채워주는 단순 후처리. claude branch 의 풀버전
# (B5 star_rating 절대 임계, B15 momentum-aware signal) 의 lite 대체.
_PRICE_CACHE: dict = {"date": None, "yest": {}, "mcap": {}}

def _refresh_price_cache(as_of_date: str | None):
    """오늘 한 번만 어제 close 및 시가총액 캐싱."""
    if _PRICE_CACHE["date"] == as_of_date and _PRICE_CACHE["yest"]:
        return
    try:
        import duckdb
        from ..core.config import DUCKDB_PATH
        # date 컬럼이 BIGINT(yyyymmdd) 형식 — '2026-04-29' → 20260429 로 변환
        as_of_int = int(as_of_date.replace("-", "")) if as_of_date and "-" in as_of_date else int(as_of_date)
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        rows = con.execute("""
            WITH d AS (
              SELECT DISTINCT date FROM prices
              WHERE date <= ? ORDER BY date DESC LIMIT 2
            )
            SELECT p.ticker, p.date, p.close, p.market_cap
            FROM prices p JOIN d ON p.date = d.date
        """, [as_of_int]).fetchall()
        con.close()
        by_date: dict = {}
        for tk, dt, cl, mc in rows:
            by_date.setdefault(int(dt), {})[tk] = (cl, mc)
        dates_sorted = sorted(by_date.keys())
        if len(dates_sorted) >= 2:
            yest_map = by_date[dates_sorted[0]]
            _PRICE_CACHE["yest"] = {t: cl for t, (cl, _) in yest_map.items() if cl}
        if dates_sorted:
            today_map = by_date[dates_sorted[-1]]
            _PRICE_CACHE["mcap"] = {t: mc for t, (_, mc) in today_map.items() if mc}
        _PRICE_CACHE["date"] = as_of_date
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"_refresh_price_cache err: {e}")


def _signal_label_lite(tier: str, score: float) -> tuple[str, str]:
    """tier+score → signal_label (영문, 한글). claude B15 풀버전 대체."""
    if tier == "A" and score >= 80:
        return "BUY", "매수"
    if tier in ("A", "B") and score >= 60:
        return "HOLD", "보유"
    if tier == "D" or score < 40:
        return "SELL", "매도"
    return "WATCH", "관망"


def _star_rating_lite(tier: str, score: float) -> float:
    """tier 기반 별점 (1.0~5.0). claude B5 절대 임계 대체."""
    if tier == "A":
        return 5.0 if score >= 90 else 4.5
    if tier == "B":
        return 4.0 if score >= 70 else 3.5
    if tier == "C":
        return 3.0
    return 2.0


def _mcap_label(market_cap: float | None) -> str | None:
    if not market_cap or market_cap <= 0:
        return None
    if market_cap >= 10_000_000_000_000:
        return "대형"
    if market_cap >= 1_000_000_000_000:
        return "중형"
    return "소형"


def _compute_30d_returns(tickers: list[str]) -> dict[str, float]:
    """ticker → 최근 30거래일 누적수익률(%). prices 의 latest close / latest-30 close - 1."""
    if not tickers: return {}
    from ..core.config import DUCKDB_PATH
    import duckdb
    out: dict[str, float] = {}
    try:
        with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
            ph = ",".join(["?"] * len(tickers))
            rows = con.execute(f"""
                WITH recent AS (
                    SELECT ticker, date, close,
                           ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rk
                    FROM prices
                    WHERE close IS NOT NULL AND ticker IN ({ph})
                )
                SELECT cur.ticker, cur.close AS cur_c, prv.close AS prv_c
                FROM (SELECT * FROM recent WHERE rk=1) cur
                JOIN (SELECT * FROM recent WHERE rk=30) prv ON cur.ticker = prv.ticker
                WHERE prv.close > 0
            """, tickers).fetchall()
        for t, c, p in rows:
            if c and p and p > 0:
                out[t] = round((float(c) / float(p) - 1) * 100, 2)
    except Exception:
        pass
    return out


def _attach_ui_fields(rows: list[dict]):
    """rows 각 dict 에 signal_label/star_rating/change_pct/market_cap_label/headline 부착."""
    if not rows:
        return
    as_of = rows[0].get("date")
    _refresh_price_cache(as_of)
    yest = _PRICE_CACHE.get("yest", {})
    mcap = _PRICE_CACHE.get("mcap", {})
    # 30일 누적수익률 일괄 산출
    tickers = [r.get("ticker") for r in rows if r.get("ticker")]
    cum30 = _compute_30d_returns(tickers)
    for r in rows:
        tier = r.get("tier") or "C"
        score = float(r.get("score") or 0)
        close = r.get("close")
        # signal
        sig, sig_ko = _signal_label_lite(tier, score)
        r["signal_label"] = sig
        r["signal_label_ko"] = sig_ko
        # star
        r["star_rating"] = _star_rating_lite(tier, score)
        # change_pct / change_value
        tk = r.get("ticker")
        y = yest.get(tk)
        if close and y and y > 0:
            r["change_value"] = round(close - y, 2)
            r["change_pct"] = round((close - y) / y * 100, 2)
        else:
            r["change_value"] = None
            r["change_pct"] = None
        # market cap label
        r["market_cap_label"] = _mcap_label(mcap.get(tk))
        # headline (lite) — 섹터·점수 조합
        sec = r.get("sector") or r.get("mid_sector") or ""
        r["headline"] = f"{sec} · 점수 {score:.1f} · {sig_ko}" if sec else f"점수 {score:.1f} · {sig_ko}"
        # 30일 누적수익률 (prices 의 latest close / latest-30 close - 1)
        r["cumulative_return_pct"] = cum30.get(tk)
        r.setdefault("first_recommended_date", None)
        r.setdefault("days_since_rec", None)


# ── 버전·날짜 메타 ─────────────────────────────────────────────────────────────

@router.get("/versions", response_model=VersionsResponse, summary="사용 가능한 model_version 목록")
def list_versions():
    versions = svc.get_available_versions()  # inserted_at DESC 순 (v9 먼저)
    return VersionsResponse(
        versions=versions,
        latest=versions[0] if versions else None,
    )


@router.get("/dates", response_model=DatesResponse, summary="사용 가능한 날짜 목록")
def list_dates(
    model_version: str = Query("latest", description="모델 버전 (예: v7, latest)"),
):
    try:
        dates = svc.get_available_dates(model_version)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return DatesResponse(
        model_version=model_version,
        dates=dates,
        latest=dates[-1] if dates else None,
    )


# ── 추천 목록 ──────────────────────────────────────────────────────────────────

@router.get("/recommendations", response_model=StockScoreList, summary="종목 추천 목록")
def get_recommendations(
    request:       Request,
    date:          Optional[str]   = Query(None,      description="조회 날짜 YYYY-MM-DD (생략 시 최신)"),
    model_version: str             = Query("latest",  description="모델 버전 (예: v9, latest)"),
    sector:        Optional[str]   = Query(None,      description="섹터 필터 (예: IT, 금융)"),
    top_k:         int             = Query(20,        ge=0, le=500, description="상위 N개 (0=전체)"),
    min_score:     float           = Query(0.0,       ge=0, le=100, description="최소 점수 필터"),
    strategy:      str             = Query("base",    description="선별 전략: base(기본) | s3(v9 S3: prob Top-150 + 레짐 신호)"),
    cohort:        Optional[str]   = Query(None,      description="W2 — conservative/balanced/growth/dividend/value (기본 None=balanced)"),
    diversify:     Optional[str]   = Query(None,      description="W3 — none(default)/correlation(권장)/sector/embedding"),
):
    """
    날짜·섹터·점수 필터로 추천 종목을 내림차순으로 반환합니다.

    - **model_version=latest** → 가장 최근 적재된 버전 자동 선택
    - **top_k=0** → 전체 반환
    - **min_score=60** → B티어 이상(60점 이상)만 반환
    - **strategy=s3** → v9 S3 전략: prob 상위 150 + KOSPI 레짐 신호 포함
    - **cohort** → W2 cohort reranking (None/balanced 시 no-op = 기존 동작)
      "내 관심사 기반 정렬" — 자문이 아닌 정보 정렬.
    """
    if strategy not in ("base", "s3"):
        strategy = "base"

    # W7B: model_version="latest" 일 때 user/session hash 로 A/B 분기.
    # env AB_SPLIT 미설정 시 default "latest:100" — 분배 OFF, 기존 동작 유지.
    split = resolve_variant(
        user_id=request.headers.get("x-user-id"),
        session_id=request.headers.get("x-session-id"),
        override=model_version,
    )
    effective_version = split.variant

    # W2: cohort 명시 시 reranking 후 일부가 필터링 될 수 있어 더 큰 풀로 가져온 뒤 자름.
    # W3: diversify 활성 시 MMR 후보 풀이 커야 다양성 효과 — 동일 패턴.
    # cohort·diversify None 일 때는 기존 동작 그대로 (캐시 키 호환성 — CLAUDE.md §반드시 지킬 것 2번).
    diversify_mode = normalize_diversify(diversify)
    needs_pool = bool(cohort) or (diversify_mode != "none")
    fetch_top_k = max(top_k * 3, 100) if (top_k > 0 and needs_pool) else top_k

    try:
        rows = svc.get_recommendations(
            date=date,
            model_version=effective_version,
            sector=sector,
            top_k=fetch_top_k,
            min_score=min_score,
            strategy=strategy,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not rows:
        raise HTTPException(status_code=404, detail="해당 날짜·조건에 맞는 데이터가 없습니다.")

    rows = annotate_confidence(rows)

    # W8 신규 상장 60일 룰. ticker_days 조회 → 미달 종목 제외.
    coverage_excluded = 0
    if rows:
        from ..core.config import DUCKDB_PATH as _DDB_W8
        ref_date = rows[0].get("date") or date
        try:
            tdays = load_ticker_days(
                str(_DDB_W8), [r["ticker"] for r in rows], as_of_date=ref_date,
            )
            rows, coverage_excluded = filter_insufficient_coverage(rows, tdays)
        except Exception:
            # 데이터 부재 등 — graceful no-op (기존 동작 유지).
            coverage_excluded = 0

    # W2 cohort 후처리. 컬럼 부재 시 graceful no-op (현 응답엔 finance/volatility 없음).
    # cohort 와 diversify 가 같이 명시되면 cohort 가 더 큰 풀에서 자르지 않게 *cohort 자르기 보류*.
    cohort_top_k = 0 if (diversify_mode != "none" and top_k > 0) else top_k
    rows = rerank_for_cohort(rows, cohort, top_k=cohort_top_k)

    if not rows:
        raise HTTPException(
            status_code=404, detail="선택한 정렬 조건에 맞는 종목이 없습니다.",
        )

    # W3 MMR 다양성 후처리. 권장 활성 모드 = correlation (sanity 검증된 유일 sim).
    if diversify_mode != "none" and len(rows) > 1:
        if diversify_mode == "sector":
            sim_func = make_sector_sim(rows)
        elif diversify_mode == "correlation":
            from ..core.config import DUCKDB_PATH as _DDB
            tickers = [r["ticker"] for r in rows]
            sim_func = make_correlation_sim(tickers, duckdb_path=str(_DDB))
        elif diversify_mode == "embedding":
            from ..core.config import DUCKDB_PATH as _DDB
            tickers = [r["ticker"] for r in rows]
            # 차차기 W3 — emb_v2 가 운영 default (분포 내 추론, correlation 신호 강화).
            ckpt = os.environ.get("EMB_CHECKPOINT",
                                  r"E:\Capstone Data\project_data\models\emb_v2.pt")
            sim_func = make_embedding_sim(tickers, checkpoint_path=ckpt, duckdb_path=str(_DDB))
        else:
            sim_func = None
        if sim_func is not None:
            rows = mmr_rerank(rows, sim=sim_func, top_k=top_k or len(rows))

    # ── UI 메타 후처리 (Front_v2 호환) ────────────────────────────────────────
    # tier·score 기반 단순 매핑 + 어제 close 대비 change_pct 계산.
    # claude branch 의 attach_signal_label 풀버전이 아니라 main 백엔드용 lite 버전.
    _attach_ui_fields(rows)

    items = [StockScore(**r) for r in rows]
    resolved_date = items[0].date if items else (date or "")
    # W7B: 응답 메타의 model_version 은 *실제 점수 출처* (items[0]) 우선.
    # items 가 비면 split.variant 그대로 (분배 결과 알리기).
    resolved_ver  = items[0].model_version if items else effective_version

    payload = StockScoreList(
        date=resolved_date,
        model_version=resolved_ver,
        total=len(items),
        items=items,
    )
    # W8 시장 레짐 (KOSPI 직전 변화율). graceful — 데이터 부재 시 normal.
    try:
        from ..core.config import DUCKDB_PATH as _DDB_W8R
        regime = detect_market_regime(
            duckdb_path=str(_DDB_W8R), as_of_date=resolved_date or None,
        )
    except Exception:
        regime = "normal"

    # W1C: impression_id 자동. W2: cohort. W7B: ab_*. W3: diversify. W8: coverage·regime.
    return attach_meta(
        payload,
        request,
        model_version=resolved_ver,
        as_of_date=resolved_date,
        is_impression=True,
        cohort=cohort or None,
        diversify=diversify_mode if diversify_mode != "none" else None,
        ab_bucket=split.bucket,
        ab_via=split.via,
        coverage_excluded=coverage_excluded if coverage_excluded > 0 else None,
        market_regime=regime,
    )


# ── 종목 상세 이력 ─────────────────────────────────────────────────────────────

@router.get("/{ticker}/history", response_model=StockHistory, summary="종목 스코어 이력")
def get_stock_history(
    ticker:        str,
    request:       Request,
    model_version: str           = Query("latest", description="모델 버전"),
    start_date:    Optional[str] = Query(None,     description="시작일 YYYY-MM-DD"),
    end_date:      Optional[str] = Query(None,     description="종료일 YYYY-MM-DD"),
):
    """특정 종목의 날짜별 추천 점수 이력을 반환합니다 (차트·분석용)."""
    try:
        rows = svc.get_stock_history(
            ticker=ticker,
            model_version=model_version,
            start_date=start_date,
            end_date=end_date,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not rows:
        raise HTTPException(status_code=404, detail=f"종목 {ticker} 데이터를 찾을 수 없습니다.")

    items = [StockHistoryItem(**r) for r in rows]
    resolved_ver = items[0].model_version if items else model_version

    payload = StockHistory(
        ticker=ticker.zfill(6),
        model_version=resolved_ver,
        total=len(items),
        items=items,
    )
    last_date = items[-1].date if items else None
    return attach_meta(
        payload,
        request,
        model_version=resolved_ver,
        as_of_date=last_date,
    )


# ── 섹터 요약 ──────────────────────────────────────────────────────────────────

@router.get("/sectors/summary", response_model=SectorSummaryList, summary="섹터별 평균 점수 요약")
def get_sector_summary(
    request:       Request,
    date:          Optional[str] = Query(None,     description="조회 날짜 (생략 시 최신)"),
    model_version: str           = Query("latest", description="모델 버전"),
):
    """섹터별 평균·최대·최소 점수 및 A티어 종목 수를 반환합니다."""
    try:
        rows = svc.get_sector_summary(date=date, model_version=model_version)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not rows:
        raise HTTPException(status_code=404, detail="해당 조건의 섹터 데이터가 없습니다.")

    items = [SectorSummaryItem(**r) for r in rows]
    resolved_date = items[0].date if items else (date or "")
    resolved_ver  = items[0].model_version if items else model_version

    payload = SectorSummaryList(
        date=resolved_date,
        model_version=resolved_ver,
        total=len(items),
        items=items,
    )
    return attach_meta(
        payload,
        request,
        model_version=resolved_ver,
        as_of_date=resolved_date,
    )


# ── 종목 검색 ──────────────────────────────────────────────────────────────────

@router.get("/search", response_model=StockSearchList, summary="종목 검색 (티커·회사명)")
def search_stocks(
    q:             str           = Query(..., min_length=1, description="검색 키워드 (티커 또는 회사명)"),
    model_version: str           = Query("latest", description="모델 버전"),
    limit:         int           = Query(20, ge=1, le=100, description="최대 결과 수"),
):
    """
    티커 코드 또는 회사명 키워드로 종목을 검색합니다.
    가장 최신 날짜 기준의 ML 점수·티어를 함께 반환합니다.
    """
    try:
        rows = svc.search_stocks(q=q, model_version=model_version, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    items = [StockSearchResult(**r) for r in rows]
    return StockSearchList(query=q, total=len(items), items=items)


# ── 종목 현재가 ────────────────────────────────────────────────────────────────

@router.get("/{ticker}/price", response_model=StockPrice, summary="종목 최신 현재가")
def get_stock_price(ticker: str):
    """prices 테이블 기준 가장 최신 종가(현재가)를 반환합니다."""
    try:
        data = svc.get_stock_price(ticker)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if data is None:
        raise HTTPException(status_code=404, detail=f"종목 {ticker} 의 가격 데이터가 없습니다.")

    return StockPrice(**data)


# ── 급상승 종목 ────────────────────────────────────────────────────────────────

@router.get("/rising", response_model=RisingStockList, summary="전일 대비 급상승 종목")
def get_rising_stocks(
    model_version: str = Query("latest", description="모델 버전"),
    limit:         int = Query(20, ge=1, le=100, description="반환 종목 수"),
):
    """최신 날짜 기준 전 거래일 대비 ML 점수 변화량(score_change) 상위 종목을 반환합니다."""
    try:
        data = svc.get_rising_stocks(model_version=model_version, limit=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    items = data.get("items", [])
    return RisingStockList(
        total=data.get("total", len(items)),
        date=data.get("date", ""),
        model_version=data.get("model_version", model_version),
        items=items,
    )


# ── Stub endpoints (Front_v2 종목 상세 페이지 호환) ─────────────────────────
# 백엔드에 산출 로직 미구현 (radar·fairvalue·dividend·peers·outcome).
# Frontend 가 404 graceful 처리 못 해 console 에러 발생 → 200 + 빈 응답 stub.
# 실제 산출 구현 후 이 stub 들을 정식 endpoint 로 교체.

@router.get("/{ticker}/radar", summary="5요인 진단 (섹터 내 백분위)")
def get_radar(ticker: str):
    """5요인(성장·수익·안전·독점·현금) — 같은 wics 섹터 종목들 사이의 백분위로 산출.

    각 raw 지표(rev_growth_yoy 등)를 섹터 내 PERCENT_RANK 로 0~100 변환 후 평균.
    NULL 지표는 그 축 점수를 50(중립) 으로 폴백 → PER/PBR 같은 단조함수 클리핑 문제 회피.
    """
    from ..core.config import DUCKDB_PATH
    import duckdb, logging
    log = logging.getLogger(__name__)
    t = ticker.zfill(6)
    try:
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        try:
            sec = con.execute(
                "SELECT wics_large_name FROM stocks WHERE ticker=?", [t]
            ).fetchone()
            sector = sec[0] if sec else None
            if not sector:
                return {"groups": None, "sector_average": None, "ticker": t}

            # 섹터 내 latest finance + 백분위
            rows = con.execute("""
                WITH lt AS (
                    SELECT ticker, MAX(base_date) AS d
                    FROM finance
                    WHERE base_date IS NOT NULL
                    GROUP BY ticker
                ),
                peer AS (
                    SELECT f.ticker, f.roe, f.op_margin, f.net_margin,
                           f.debt_ratio, f.current_ratio,
                           f.rev_growth_yoy, f.op_growth_yoy
                    FROM lt JOIN finance f ON f.ticker=lt.ticker AND f.base_date=lt.d
                    JOIN stocks st ON f.ticker=st.ticker
                    WHERE st.wics_large_name=?
                ),
                ranked AS (
                    SELECT ticker, roe, op_margin, net_margin,
                           debt_ratio, current_ratio, rev_growth_yoy, op_growth_yoy,
                           100 * PERCENT_RANK() OVER (ORDER BY rev_growth_yoy ASC NULLS FIRST) AS rev_pr,
                           100 * PERCENT_RANK() OVER (ORDER BY op_growth_yoy  ASC NULLS FIRST) AS opg_pr,
                           100 * PERCENT_RANK() OVER (ORDER BY roe            ASC NULLS FIRST) AS roe_pr,
                           100 * PERCENT_RANK() OVER (ORDER BY op_margin      ASC NULLS FIRST) AS opm_pr,
                           100 * PERCENT_RANK() OVER (ORDER BY net_margin     ASC NULLS FIRST) AS nm_pr,
                           100 * PERCENT_RANK() OVER (ORDER BY debt_ratio     DESC NULLS FIRST) AS dbt_pr,
                           100 * PERCENT_RANK() OVER (ORDER BY current_ratio  ASC NULLS FIRST) AS cur_pr
                    FROM peer
                )
                SELECT * FROM ranked WHERE ticker=?
            """, [sector, t]).fetchone()
            if not rows:
                return {"groups": None, "sector_average": None, "ticker": t}
            (_tk, roe, opm, nm, dbt, cur, rev, opg,
             rev_pr, opg_pr, roe_pr, opm_pr, nm_pr, dbt_pr, cur_pr) = rows

            def axis(prs, nulls):
                # 모든 raw 지표가 NULL 이면 50(중립). 일부만 NULL 이면 그 항만 50 으로 대체 후 평균.
                vals = [50.0 if (raw is None) else float(pr)
                        for pr, raw in zip(prs, nulls)]
                return round(max(0.0, min(100.0, sum(vals) / len(vals))), 1)

            growth        = axis([rev_pr, opg_pr], [rev, opg])
            profitability = axis([roe_pr, opm_pr], [roe, opm])
            safety        = axis([dbt_pr, cur_pr], [dbt, cur])
            moat          = axis([opm_pr], [opm])           # 영업이익률 = 가격결정력 proxy
            cashflow      = axis([nm_pr], [nm])             # 순이익률 = 현금창출 proxy
            groups = {"growth": growth, "profitability": profitability,
                       "safety": safety, "moat": moat, "cashflow": cashflow}

            # 섹터 평균: 정의상 50 (백분위 평균). frontend 비교축으로만 사용.
            sec_avg = {"growth": 50.0, "profitability": 50.0,
                        "safety": 50.0, "moat": 50.0, "cashflow": 50.0}
            return {"groups": groups, "sector_average": sec_avg, "ticker": t}
        finally:
            con.close()
    except Exception as e:
        log.exception(f"[radar] {t} 실패: {e}")
        return {"groups": None, "sector_average": None, "ticker": t}


@router.get("/{ticker}/fairvalue", summary="적정주가 (PER·PBR 멀티플)")
def get_fairvalue(ticker: str):
    """섹터 PER × EPS + 섹터 PBR × BPS 평균. EPS≤0 이면 PBR 단독.
    self_PER 은 섹터 PER 의 2배로 cap 후 평균.
    """
    from ..core.config import DUCKDB_PATH
    import duckdb, logging
    log = logging.getLogger(__name__)
    t = ticker.zfill(6)
    try:
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        try:
            r = con.execute("""
                SELECT f.eps, f.bps, f.per, f.pbr, st.wics_large_name
                FROM finance f LEFT JOIN stocks st ON f.ticker=st.ticker
                WHERE f.ticker=? AND f.base_date IS NOT NULL
                ORDER BY f.base_date DESC LIMIT 1
            """, [t]).fetchone()
            if not r:
                return {"ticker": t, "current_price": None, "fair_value": None,
                        "deviation_pct": None, "band_ko": None, "inputs": None}
            eps, bps, self_per, self_pbr, sector = r
            # 현재가 (prices 최신 종가)
            cp_r = con.execute(
                "SELECT close FROM prices WHERE ticker=? ORDER BY date DESC LIMIT 1", [t]
            ).fetchone()
            current_price = float(cp_r[0]) if cp_r else None

            # 섹터 PER/PBR 중앙값 (양수만, 10-90 trim 효과는 median 으로 충분)
            sec_per = sec_pbr = None
            if sector:
                sec_r = con.execute("""
                    WITH lt AS (
                        SELECT ticker, MAX(base_date) AS d FROM finance
                        WHERE base_date IS NOT NULL GROUP BY ticker
                    )
                    SELECT
                        MEDIAN(f.per) FILTER (WHERE f.per > 0 AND f.per < 200),
                        MEDIAN(f.pbr) FILTER (WHERE f.pbr > 0 AND f.pbr < 20)
                    FROM lt JOIN finance f ON f.ticker=lt.ticker AND f.base_date=lt.d
                    JOIN stocks st ON f.ticker=st.ticker
                    WHERE st.wics_large_name=?
                """, [sector]).fetchone()
                if sec_r:
                    sec_per = float(sec_r[0]) if sec_r[0] is not None else None
                    sec_pbr = float(sec_r[1]) if sec_r[1] is not None else None

            eps_f = float(eps) if eps is not None else None
            bps_f = float(bps) if bps is not None else None
            self_per_f = float(self_per) if self_per is not None else None
            self_pbr_f = float(self_pbr) if self_pbr is not None else None

            # PER ratio 산식 (current_price × sec_per / self_per): EPS/BPS 절대값 의존 회피
            # self_per 가 sec_per 보다 크면 자기가 비싸다 → 적정가 < 현재가
            fair_per_value = None
            if current_price and self_per_f and self_per_f > 0 and sec_per:
                capped_self = min(self_per_f, sec_per * 2)  # 거품 cap
                fair_per_value = current_price * sec_per / capped_self

            # PBR ratio 산식 (current_price × sec_pbr / self_pbr)
            fair_pbr_value = None
            if current_price and self_pbr_f and self_pbr_f > 0 and sec_pbr:
                capped_pbr = min(self_pbr_f, sec_pbr * 2)
                fair_pbr_value = current_price * sec_pbr / capped_pbr

            # 최종 적정가: 둘 다 있으면 평균, 하나만 있으면 그것
            cands = [v for v in (fair_per_value, fair_pbr_value) if v is not None and v > 0]
            fair_value = sum(cands) / len(cands) if cands else None

            deviation_pct = None
            band_ko = None
            if fair_value and current_price:
                deviation_pct = (current_price / fair_value - 1) * 100
                d = deviation_pct
                if   d >=  20: band_ko = "매우고평가"
                elif d >=  10: band_ko = "고평가"
                elif d >  -10: band_ko = "적정"
                elif d >  -20: band_ko = "저평가"
                else:          band_ko = "매우저평가"

            return {
                "ticker": t,
                "current_price": round(current_price, 1) if current_price else None,
                "fair_value":    round(fair_value, 1) if fair_value else None,
                "deviation_pct": round(deviation_pct, 2) if deviation_pct is not None else None,
                "band_ko": band_ko,
                "inputs": {
                    "eps": eps_f, "bps": bps_f,
                    "sector_per":   round(sec_per, 2) if sec_per else None,
                    "sector_pbr":   round(sec_pbr, 2) if sec_pbr else None,
                    "self_per_med": self_per_f,
                    "self_pbr_med": self_pbr_f,
                },
            }
        finally:
            con.close()
    except Exception as e:
        log.exception(f"[fairvalue] {t} 실패: {e}")
        return {"ticker": t, "current_price": None, "fair_value": None,
                "deviation_pct": None, "band_ko": None, "inputs": None}


@router.get("/{ticker}/dividend", summary="배당 점수 (5축 가중 — D-P-G + 안정성 + 성장)")
def get_dividend(ticker: str):
    """5축 가중평균:
      yield     (수익률)        25% — 배당수익률 백분위 (전체 universe)
      payout    (배당성향)      20% — payout ratio 50~70% 가 적정 (sweet spot)
      growth    (성장)         20% — rev_growth_yoy 백분위 (배당 지속능력)
      continuity(연속성)        20% — 최근 4 분기 모두 dy>0 여부
      safety    (재무 안전)     15% — debt_ratio 역백분위 (낮을수록 ↑)
    """
    from ..core.config import DUCKDB_PATH
    import duckdb, logging
    log = logging.getLogger(__name__)
    t = ticker.zfill(6)
    try:
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        try:
            # latest 1행 + 최근 4분기 dy 시퀀스
            r = con.execute("""
                WITH lt AS (
                    SELECT ticker, MAX(base_date) AS d FROM finance
                    WHERE base_date IS NOT NULL GROUP BY ticker
                ),
                ranked AS (
                    SELECT f.ticker, f.dividend_yield, f.eps, f.net_profit,
                           f.rev_growth_yoy, f.debt_ratio,
                           100 * PERCENT_RANK() OVER (ORDER BY f.dividend_yield ASC NULLS FIRST) AS dy_pr,
                           100 * PERCENT_RANK() OVER (ORDER BY f.rev_growth_yoy ASC NULLS FIRST) AS rg_pr,
                           100 * PERCENT_RANK() OVER (ORDER BY f.debt_ratio DESC NULLS FIRST) AS dbt_pr
                    FROM lt JOIN finance f ON f.ticker=lt.ticker AND f.base_date=lt.d
                )
                SELECT * FROM ranked WHERE ticker=?
            """, [t]).fetchone()
            if not r:
                return {"ticker": t, "total_score": None, "yield_pct": None, "scores": None}
            _, dy, eps, net_p, rg, dbt, dy_pr, rg_pr, dbt_pr = r

            # payout 추정: dps/eps. 50~70% 가 sweet spot (적정 점수 100), 그 외 가우시안 감쇠.
            payout_score = 50.0
            try:
                dps_row = con.execute(
                    "SELECT dps FROM finance WHERE ticker=? AND base_date IS NOT NULL ORDER BY base_date DESC LIMIT 1",
                    [t]).fetchone()
                if dps_row and dps_row[0] and eps and eps > 0:
                    payout = float(dps_row[0]) / float(eps)
                    # sweet spot 0.6 ±0.1 → 100점, ±0.3 → ~50점
                    payout_score = max(0.0, min(100.0, 100 * (1 - (abs(payout - 0.6) / 0.4)**2)))
            except Exception:
                pass

            # 연속성: 최근 4분기 모두 dividend_yield>0
            cont_rows = con.execute("""
                SELECT dividend_yield FROM finance
                WHERE ticker=? AND base_date IS NOT NULL
                ORDER BY base_date DESC LIMIT 4
            """, [t]).fetchall()
            cont_score = (sum(1 for x in cont_rows if x[0] and x[0] > 0) / 4) * 100 if cont_rows else 0.0

            # NULL 폴백 50
            yield_score  = float(dy_pr)  if dy  is not None else 50.0
            growth_score = float(rg_pr)  if rg  is not None else 50.0
            safety_score = float(dbt_pr) if dbt is not None else 50.0

            # 가중평균
            W = {"yield": 0.25, "payout": 0.20, "growth": 0.20, "continuity": 0.20, "safety": 0.15}
            total = (
                yield_score  * W["yield"]      +
                payout_score * W["payout"]     +
                growth_score * W["growth"]     +
                cont_score   * W["continuity"] +
                safety_score * W["safety"]
            )
            return {
                "ticker": t,
                "total_score": round(total, 1),
                "yield_pct": round(float(dy) * 100, 2) if dy is not None else None,
                "scores": {
                    "yield_score":      round(yield_score, 1),
                    "payout_score":     round(payout_score, 1),
                    "growth_score":     round(growth_score, 1),
                    "continuity_score": round(cont_score, 1),
                    "safety_score":     round(safety_score, 1),
                },
                "weights": W,
            }
        finally:
            con.close()
    except Exception as e:
        log.exception(f"[dividend] {t} 실패: {e}")
        return {"ticker": t, "total_score": None, "yield_pct": None, "scores": None}


@router.get("/{ticker}/peers", summary="경쟁사 (동일 섹터 + 시총 유사)")
def get_peers(ticker: str, limit: int = Query(8, ge=1, le=20)):
    """같은 wics_large_name 섹터 내 시총 ±50% 범위 종목 (시총 거리 기준 정렬)."""
    from ..core.config import DUCKDB_PATH
    import duckdb, logging
    log = logging.getLogger(__name__)
    t = ticker.zfill(6)
    try:
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        try:
            # 자신의 sector + 시총 (prices latest market_cap)
            self_r = con.execute("""
                WITH lt AS (SELECT ticker, MAX(date) AS d FROM prices GROUP BY ticker)
                SELECT st.wics_large_name, p.market_cap, st.name
                FROM stocks st JOIN lt ON lt.ticker=st.ticker
                JOIN prices p ON p.ticker=lt.ticker AND p.date=lt.d
                WHERE st.ticker=?
            """, [t]).fetchone()
            if not self_r or self_r[0] is None or self_r[1] is None:
                return {"ticker": t, "items": []}
            sector, self_cap, _self_name = self_r
            cap_lo, cap_hi = self_cap * 0.5, self_cap * 1.5

            # 동섹터 + 시총 ±50% + latest scores (score, tier) — model_version 중복 방지
            rows = con.execute("""
                WITH lt_p AS (SELECT ticker, MAX(date) AS d FROM prices GROUP BY ticker),
                     latest_score AS (
                        SELECT ticker, score, tier,
                               ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC, model_version) AS rk
                        FROM scores
                     )
                SELECT st.ticker, st.name, p.market_cap, p.close,
                       ls.score, ls.tier
                FROM stocks st
                JOIN lt_p ON lt_p.ticker=st.ticker
                JOIN prices p ON p.ticker=lt_p.ticker AND p.date=lt_p.d
                LEFT JOIN latest_score ls ON ls.ticker=st.ticker AND ls.rk=1
                WHERE st.wics_large_name=? AND st.ticker!=?
                  AND p.market_cap BETWEEN ? AND ?
                ORDER BY ABS(p.market_cap - ?)
                LIMIT ?
            """, [sector, t, cap_lo, cap_hi, self_cap, limit]).fetchall()

            items = [{
                "ticker": r[0], "name": r[1],
                "market_cap": float(r[2]) if r[2] else None,
                "close": float(r[3]) if r[3] else None,
                "score": float(r[4]) if r[4] else None,
                "tier": r[5],
            } for r in rows]
            return {"ticker": t, "sector": sector, "items": items}
        finally:
            con.close()
    except Exception as e:
        log.exception(f"[peers] {t} 실패: {e}")
        return {"ticker": t, "items": []}


@router.get("/{ticker}/outcome", summary="최근 30일 수익률")
def get_outcome(ticker: str):
    """prices 의 최근 30거래일 종가 비교 = (last/prev_30 - 1) × 100."""
    from ..core.config import DUCKDB_PATH
    import duckdb
    t = ticker.zfill(6)
    try:
        with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
            rows = con.execute("""
                SELECT close FROM prices WHERE ticker=? AND close IS NOT NULL
                ORDER BY date DESC LIMIT 31
            """, [t]).fetchall()
            if len(rows) >= 30 and rows[0][0] and rows[-1][0]:
                pct = (rows[0][0] / rows[-1][0] - 1) * 100
                return {"ticker": t, "cumulative_return_pct": round(pct, 2)}
    except Exception:
        pass
    return {"ticker": t, "cumulative_return_pct": None}


# ── 승부주 (winners) — stub ──────────────────────────────────────────────
# 8001 ML 서버에서 별도 winners endpoint 가 별도 라우터에 등록될 수 있으나
# 현재 미구현 → 빈 응답으로 404 회피.
from fastapi import APIRouter as _AR  # noqa: E402

winners_router = _AR(tags=["winners"])

@winners_router.get("/winners", summary="승부주 — ML 0.6 + HV-normalized vol 0.4")
def get_winners(days_back: int = Query(8, ge=1, le=60), top_k: int = Query(5, ge=1, le=10)):
    """승부주 산식 (최근 1주일 9개 후보 백테스트 1위):
        combined = ml_rank_pct × 0.6 + vol_norm_rank_pct × 0.4
        vol_norm = ((high − low) / close) / HV60
        HV60     = 60거래일 일간수익률 표준편차 × √252
        대상     = A티어, cooldown = 7거래일

    백테스트 결과 (25 추천, 최근 5거래일 5/29~6/5):
        median = −0.71% (1위), mean = −2.16% (2위), win = 20.0% (1위)
    의미: 일중 진폭이 자기 종목의 평소 변동성 대비 큰 종목 = 단기 이벤트성 진입 신호.
    """
    from ..core.config import DUCKDB_PATH
    import duckdb, logging
    from datetime import timedelta
    log = logging.getLogger(__name__)
    try:
        con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
        try:
            # 일자별 A티어 + 변동성 결합 점수
            # vol = max((high-low)/close, |chg|/100). chg = 전일대비 변동률 (prices.lag 사용)
            rows = con.execute("""
                WITH dates AS (
                    SELECT DISTINCT date FROM scores ORDER BY date DESC LIMIT ?
                ),
                px AS (
                    SELECT
                        ticker,
                        date,
                        close,
                        high,
                        low,
                        LAG(close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close
                    FROM prices
                    WHERE close IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL
                ),
                px_ret AS (
                    SELECT *,
                        CASE WHEN prev_close IS NOT NULL AND prev_close > 0
                             THEN (CAST(close AS DOUBLE) - prev_close) / prev_close
                             ELSE NULL END AS ret_1d
                    FROM px
                ),
                px_hv AS (
                    SELECT *,
                        STDDEV(ret_1d) OVER (
                            PARTITION BY ticker ORDER BY date
                            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                        ) * SQRT(252) AS hv60
                    FROM px_ret
                ),
                px_vol AS (
                    SELECT
                        ticker,
                        date,
                        close,
                        -- HV-normalized 일중 진폭 = ((H-L)/C) / HV60
                        -- 일중 진폭이 자기 종목 평소 변동성 대비 큰 종목 = 단기 이벤트 신호
                        CASE
                            WHEN hv60 IS NOT NULL AND hv60 > 0 AND close > 0
                            THEN ((CAST(high AS DOUBLE) - low) / close) / hv60
                            ELSE 0
                        END AS vol
                    FROM px_hv
                ),
                joined AS (
                    SELECT
                        s.date,
                        s.ticker,
                        s.name,
                        s.score,
                        s.close AS s_close,
                        v.vol,
                        v.close AS p_close
                    FROM scores s
                    JOIN dates d ON s.date = d.date
                    LEFT JOIN px_vol v ON v.ticker = s.ticker
                        AND v.date = CAST(strftime(CAST(s.date AS DATE), '%Y%m%d') AS BIGINT)
                    WHERE s.tier = 'A'
                ),
                ranked AS (
                    SELECT
                        date, ticker, name, score, s_close, p_close, vol,
                        PERCENT_RANK() OVER (PARTITION BY date ORDER BY score ASC) AS ml_pct,
                        PERCENT_RANK() OVER (PARTITION BY date ORDER BY COALESCE(vol, 0) ASC) AS vol_pct
                    FROM joined
                ),
                scored AS (
                    SELECT
                        date, ticker, name, score, s_close, p_close, vol,
                        (ml_pct * 0.6 + vol_pct * 0.4) AS combined,
                        ROW_NUMBER() OVER (PARTITION BY date
                            ORDER BY (ml_pct * 0.6 + vol_pct * 0.4) DESC) AS rk
                    FROM ranked
                )
                SELECT date, ticker, name, score, COALESCE(p_close, s_close) AS close, vol, combined
                FROM scored WHERE rk <= ?
                ORDER BY date DESC, rk
            """, [days_back, max(50, top_k * 20)]).fetchall()

            # 현재가 (최신 prices.close) 일괄
            cp_rows = con.execute("""
                WITH lt AS (SELECT ticker, MAX(date) AS d FROM prices GROUP BY ticker)
                SELECT p.ticker, p.close FROM lt JOIN prices p ON p.ticker=lt.ticker AND p.date=lt.d
            """).fetchall()
            cp = {t: float(c) for t, c in cp_rows if c is not None}

            # 적정가(target_price) 일괄 산출 — fairvalue ratio 산식과 동일
            #   target = current_price × sec_per / capped_self_per  (PER+PBR 평균)
            target_rows = con.execute("""
                WITH lt_f AS (
                    SELECT ticker, MAX(base_date) AS d FROM finance
                    WHERE base_date IS NOT NULL GROUP BY ticker
                ),
                self_meta AS (
                    SELECT f.ticker, f.per AS self_per, f.pbr AS self_pbr, st.wics_large_name AS sector
                    FROM lt_f JOIN finance f ON f.ticker=lt_f.ticker AND f.base_date=lt_f.d
                    LEFT JOIN stocks st ON f.ticker=st.ticker
                ),
                sec_med AS (
                    SELECT st.wics_large_name AS sector,
                           MEDIAN(f.per) FILTER (WHERE f.per > 0 AND f.per < 200) AS sec_per,
                           MEDIAN(f.pbr) FILTER (WHERE f.pbr > 0 AND f.pbr < 20) AS sec_pbr
                    FROM lt_f JOIN finance f ON f.ticker=lt_f.ticker AND f.base_date=lt_f.d
                    JOIN stocks st ON f.ticker=st.ticker
                    WHERE st.wics_large_name IS NOT NULL
                    GROUP BY st.wics_large_name
                )
                SELECT sm.ticker, sm.self_per, sm.self_pbr, sd.sec_per, sd.sec_pbr
                FROM self_meta sm
                LEFT JOIN sec_med sd ON sd.sector = sm.sector
            """).fetchall()
            fv_inputs = {t: (sp, spb, sep, spb_sec) for t, sp, spb, sep, spb_sec in target_rows}

            def _target_for(ticker_t: str, cur_price: float | None) -> float | None:
                if not cur_price: return None
                inp = fv_inputs.get(ticker_t)
                if not inp: return None
                self_per, self_pbr, sec_per, sec_pbr = inp
                cands = []
                if self_per and self_per > 0 and sec_per:
                    capped = min(float(self_per), float(sec_per) * 2)
                    if capped > 0: cands.append(cur_price * float(sec_per) / capped)
                if self_pbr and self_pbr > 0 and sec_pbr:
                    capped = min(float(self_pbr), float(sec_pbr) * 2)
                    if capped > 0: cands.append(cur_price * float(sec_pbr) / capped)
                if not cands: return None
                return round(sum(cands) / len(cands), 1)

            # 7거래일 cooldown
            last_picked = {}  # ticker -> date
            groups: dict = {}
            for date_v, ticker, name, score, close, vol, combined in rows:
                if ticker in last_picked:
                    if (date_v - last_picked[ticker]).days < 7:
                        continue
                bucket = groups.setdefault(date_v, [])
                if len(bucket) >= top_k:
                    continue
                last_picked[ticker] = date_v
                rec_price = float(close) if close is not None else None
                cur = cp.get(ticker)
                cum = None
                if rec_price and cur and rec_price > 0:
                    cum = round((cur / rec_price - 1) * 100, 2)
                target = _target_for(ticker, cur)
                bucket.append({
                    "ticker": ticker, "name": name,
                    "recommend_price": rec_price,
                    "score": round(float(score), 1) if score is not None else None,
                    "cumulative_return_pct": cum,
                    "target_price": target,
                    "split_event_suspected": (cum is not None and cum < -50),
                    # 새 산식 디버그/표시 필드 (frontend 가 무시해도 OK)
                    "daily_vol_pct": round(float(vol) * 100, 2) if vol is not None else None,
                    "combined_score": round(float(combined) * 100, 1) if combined is not None else None,
                })

            items = [{"date": d.isoformat(), "winners": ws}
                     for d, ws in sorted(groups.items(), reverse=True)]
            return {"model_version": "blended_w0.3", "items": items}
        finally:
            con.close()
    except Exception as e:
        log.exception(f"[winners] 실패: {e}")
        return {"model_version": "blended_w0.3", "items": []}

@winners_router.get("/cohort-backtest/{cohort}", summary="코호트 백테스트 — stub")
def get_cohort_backtest(cohort: str):
    """K10·H20 16개월 코호트 백테스트. 미구현 시 빈 응답."""
    return {
        "cohort": cohort, "n_months": 0,
        "avg_return_pct": None, "cum_return_pct": None,
        "win_rate_pct": None, "sharpe": None, "max_drawdown": None,
    }


SECTOR_KEYWORDS = {
    "IT":                  ["반도체", "디스플레이", "전자", "스마트폰", "AI", "인공지능", "데이터센터"],
    "금융":                ["은행", "보험", "증권", "금융지주", "금리"],
    "에너지":              ["에너지", "석유", "가스", "원유"],
    "산업재":              ["조선", "건설", "기계", "방위산업", "항공", "물류"],
    "헬스케어":            ["제약", "바이오", "의료기기", "신약"],
    "경기소비재":          ["자동차", "유통", "백화점", "엔터테인먼트", "게임", "여행"],
    "필수소비재":          ["식품", "음료", "담배", "화장품"],
    "소재":                ["화학", "철강", "비철금속", "이차전지"],
    "커뮤니케이션서비스":  ["통신", "광고", "미디어", "포털"],
    "유틸리티":            ["전력", "수도", "도시가스"],
}

@router.get("/{ticker}/news", summary="종목명 매칭 + 섹터 키워드 매칭 뉴스")
def get_stock_news(ticker: str, limit: int = Query(8, ge=1, le=30)):
    """매칭 우선순위:
    1) Redis item.title 에 종목명 단어경계 매칭 → match_via='title'
    2) report 본문(executive_brief + main_themes.explanation 등)에 종목명 등장 → 그 카테고리 TOP → match_via='report_body'
    3) report 본문에 섹터 키워드(wics_large_name 매핑) 등장 → 그 카테고리 TOP → match_via='sector'
    """
    import re as _re, json as _json
    from ..core.config import DUCKDB_PATH
    import duckdb, os
    t = ticker.zfill(6)
    try:
        with duckdb.connect(str(DUCKDB_PATH), read_only=True) as con:
            r = con.execute("SELECT name, wics_large_name FROM stocks WHERE ticker=?", [t]).fetchone()
            if not r or not r[0]:
                return {"ticker": t, "items": []}
            name, sector = r[0], r[1]
    except Exception:
        return {"ticker": t, "items": []}
    try:
        import redis
        rd = redis.Redis(
            host=os.getenv("WEBNEWS_REDIS_HOST") or os.getenv("REDIS_HOST", "100.67.30.5"),
            port=int(os.getenv("WEBNEWS_REDIS_PORT", os.getenv("REDIS_PORT", 6380))),
            password=(os.getenv("WEBNEWS_REDIS_PASSWORD") or os.getenv("REDIS_QUEUE_PASSWORD")
                     or os.getenv("REDIS_PASSWORD")),
            db=0, decode_responses=True, socket_timeout=5,
        )
        rd.ping()
    except Exception:
        return {"ticker": t, "items": []}
    # 앞: 영문/숫자/한글 단어 일부 차단. 뒤: 영문/숫자만 차단 (한글 조사 '와/이/가/는' 등 허용).
    pat = _re.compile(rf"(?<![\w가-힣]){_re.escape(name)}(?![\w])")
    matched_ids = set()
    matched = []
    # 1) title 직접 매칭
    item_keys = list(rd.scan_iter(match="webnews:*:item:*"))
    for k in item_keys:
        try:
            h = rd.hgetall(k)
            title = h.get("title") or ""
            if pat.search(title):
                iid = h.get("id")
                if iid in matched_ids: continue
                matched_ids.add(iid)
                matched.append({
                    "news_id": iid, "title": title, "source": h.get("publisher"),
                    "published_at": h.get("published_at"), "url": h.get("google_news_url"),
                    "category": h.get("category_id"), "category_label": h.get("category_label"),
                    "score": float(h.get("score") or 0), "match_via": "title",
                })
        except Exception:
            continue
    # 2) report 본문 매칭 — 카테고리별 report 의 executive_brief + main_themes.explanation 에서 종목명 찾음.
    # 매칭되면 그 카테고리의 TOP item 들을 "본문 언급" 으로 첨부.
    matched_cats = set()
    for k in rd.scan_iter(match="webnews:*:report:*"):
        try:
            raw = rd.get(k)
            if not raw: continue
            d = _json.loads(raw)
            # 매칭 대상 텍스트 합치기
            texts = [d.get("executive_brief") or "", d.get("one_line") or ""]
            for theme in (d.get("main_themes") or []):
                if isinstance(theme, dict):
                    texts.append(theme.get("explanation") or "")
                    texts.append(theme.get("market_relevance") or "")
            for sig in (d.get("sector_signals") or []):
                if isinstance(sig, dict):
                    texts.append(sig.get("reason") or "")
            joined = "\n".join(texts)
            if pat.search(joined):
                parts = k.split(":")
                if len(parts) >= 4:
                    date_str, cat = parts[1], parts[3]
                    matched_cats.add((date_str, cat))
        except Exception:
            continue
    # 3) 섹터 키워드 매칭 — item title 직접 매칭으로 변경
    #    (이전: LLM report 본문 키워드 등장만으로 카테고리 TOP 전부 부착 → 무관 뉴스 다수 유입.
    #     예: '소재' 섹터 종목에 '대한민국' 카테고리 정치/스포츠 뉴스가 매칭됨)
    sector_kw_list = SECTOR_KEYWORDS.get(sector or "", [])
    if sector_kw_list:
        sec_pat = _re.compile(
            rf"(?<![\w가-힣])(?:{'|'.join(_re.escape(k) for k in sector_kw_list)})(?![\w])"
        )
        for k in item_keys:
            try:
                h = rd.hgetall(k)
                title = h.get("title") or ""
                if not sec_pat.search(title):
                    continue
                iid = h.get("id")
                if iid in matched_ids:
                    continue
                matched_ids.add(iid)
                matched.append({
                    "news_id": iid, "title": title, "source": h.get("publisher"),
                    "published_at": h.get("published_at"), "url": h.get("google_news_url"),
                    "category": h.get("category_id"), "category_label": h.get("category_label"),
                    "score": float(h.get("score") or 0), "match_via": "sector",
                })
            except Exception:
                continue

    def _attach_category_top(cat: str, via: str, top_k: int):
        try:
            rank_dates = set()
            for rk in rd.scan_iter(match=f"webnews:*:rank:{cat}"):
                ps = rk.split(":")
                if len(ps) >= 3: rank_dates.add(ps[1])
            if not rank_dates: return
            latest = sorted(rank_dates, reverse=True)[0]
            ranked = rd.zrevrange(f"webnews:{latest}:rank:{cat}", 0, top_k - 1, withscores=True)
            for iid, sc in ranked:
                if iid in matched_ids: continue
                h = rd.hgetall(f"webnews:{latest}:item:{iid}")
                if not h: continue
                matched_ids.add(iid)
                matched.append({
                    "news_id": iid, "title": h.get("title"), "source": h.get("publisher"),
                    "published_at": h.get("published_at"), "url": h.get("google_news_url"),
                    "category": cat, "category_label": h.get("category_label"),
                    "score": float(sc), "match_via": via,
                })
        except Exception:
            return

    # report 본문에 종목명 등장 시 그 카테고리 TOP 5 부착
    for cat in {c for _, c in matched_cats}:
        _attach_category_top(cat, via="report_body", top_k=5)

    # 정렬 우선순위: title > report_body > sector, 그 안에서 최신순
    via_order = {"title": 0, "report_body": 1, "sector": 2}
    matched.sort(key=lambda x: (
        via_order.get(x.get("match_via", ""), 9),
        -(int(x.get("published_at", "")[:10].replace("-", "") or 0) if x.get("published_at") else 0),
    ))
    return {"ticker": t, "name": name, "sector": sector, "items": matched[:limit]}
