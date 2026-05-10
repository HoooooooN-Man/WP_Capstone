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
