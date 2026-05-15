"""
schemas/stocks.py
=================
API 응답용 Pydantic 모델 — 하위 호환 정책:
  - 기존 필드 삭제·이름 변경 금지
  - 신규 필드 추가 시 반드시 Optional + 기본값 None 으로 선언
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel

from .meta import ResponseMeta


# ── 종목 스코어 ────────────────────────────────────────────────────────────────

class StockScore(BaseModel):
    """단일 종목 × 날짜의 추천 점수 레코드."""
    date:           str
    ticker:         str
    name:           Optional[str]  = None
    sector:         Optional[str]  = None
    mid_sector:     Optional[str]  = None
    close:          Optional[float] = None

    # 모델별 확률 (0~1)
    prob_lgbm:      float
    prob_xgb:       float
    prob_cat:       float
    prob_ensemble:  float           # (lgbm + xgb + cat) / 3

    # 추천 수치화
    score:          float           # 1~100 (높을수록 좋음)
    tier:           str             # A / B / C / D
    rank_in_date:   int             # 해당 날짜 내 랭킹 (1 = 최상위)
    total_in_date:  int             # 해당 날짜 총 종목 수

    model_version:  str

    # ── 신뢰구간 (Tier 1.4 / 차별화 §2.1) ────────────────────────────────────
    # 세 모델 확률의 표본 표준편차. 클수록 모델 의견 불일치.
    prob_std:       Optional[float] = None
    # 점수 단위(1~100) 환산 표준편차. score ± score_std 형태로 UI 표시.
    score_std:      Optional[float] = None
    # 모델 의견 불일치 플래그. prob_std > DISAGREEMENT_THRESHOLD 일 때 True.
    model_disagreement: Optional[bool] = None

    # ── SHAP 기여 피처 (Tier 1.3 / 차별화 §2.3) ──────────────────────────────
    # 종목별 상위 3개 기여 피처 (자연어 라벨 포함). compute_shap.py 가 적재.
    # 각 원소: {feature, contribution, direction, label, display}
    top_factors:    Optional[list[dict]] = None

    # S3 전략 메타 (strategy=s3 일 때만 포함)
    regime:         Optional[int]   = None  # 1=상승, 0=하락(방어)
    regime_label:   Optional[str]   = None  # "상승" | "하락(방어)"
    position_scale: Optional[float] = None  # 1.0 또는 0.5

    # ── P0~P2 후처리 부착 필드 (PRD §8) ─────────────────────────────────────
    # P0-1: 4단계 신호 라벨
    signal_label:    Optional[str]   = None  # BUY / HOLD / SELL / WATCH
    signal_label_ko: Optional[str]   = None  # 매수 / 보유 / 매도 / 관망
    # P1-7: 별점 + 동종 섹터 백분위
    star_rating:         Optional[float] = None  # 0.5 단위 0-5
    percentile_in_sector: Optional[float] = None
    sector_rank:         Optional[int]   = None
    sector_total:        Optional[int]   = None
    # P0-2: 추천 후 누적 상승률
    cumulative_return_pct:  Optional[float] = None
    first_recommended_date: Optional[str]   = None
    days_since_rec:         Optional[int]   = None
    # P1-10: 헤드라인 한 줄
    headline:        Optional[str]   = None
    # 정합성 보강: 전일 대비 등락률
    change_pct:      Optional[float] = None
    # market cap 라벨 (선택 — 백엔드 미부착 시 None)
    market_cap_label: Optional[str]  = None


class StockScoreList(BaseModel):
    """추천 목록 응답."""
    date:          str
    model_version: str
    total:         int
    items:         list[StockScore]
    meta:          Optional[ResponseMeta] = None


# ── 종목 이력 ──────────────────────────────────────────────────────────────────

class StockHistoryItem(BaseModel):
    """단일 종목의 날짜별 스코어 한 행 (+ prices OHLCV·시총)."""
    date:               str
    ticker:             str
    name:               Optional[str]  = None
    sector:             Optional[str]  = None
    close:              Optional[float] = None
    open:               Optional[float] = None
    high:               Optional[float] = None
    low:                Optional[float] = None
    volume:             Optional[float] = None
    market_cap:         Optional[float] = None
    shares_outstanding: Optional[float] = None
    foreign_ratio:      Optional[float] = None
    prob_ensemble:      float
    score:              float
    tier:               str
    rank_in_date:       int
    total_in_date:      int
    model_version:      str


class StockHistory(BaseModel):
    """종목 이력 응답."""
    ticker:        str
    model_version: str
    total:         int
    items:         list[StockHistoryItem]
    meta:          Optional[ResponseMeta] = None


# ── 섹터 요약 ──────────────────────────────────────────────────────────────────

class SectorSummaryItem(BaseModel):
    sector:       str
    date:         str
    stock_count:  int
    avg_score:    float
    max_score:    float
    min_score:    float
    tier_a_count: int
    model_version: str


class SectorSummaryList(BaseModel):
    date:          str
    model_version: str
    total:         int
    items:         list[SectorSummaryItem]
    meta:          Optional[ResponseMeta] = None


# ── 공통 유틸 ──────────────────────────────────────────────────────────────────

class VersionsResponse(BaseModel):
    """사용 가능한 model_version 목록."""
    versions: list[str]
    latest:   Optional[str] = None


class DatesResponse(BaseModel):
    """사용 가능한 날짜 목록."""
    model_version: str
    dates:         list[str]
    latest:        Optional[str] = None


# ── 백테스트 ───────────────────────────────────────────────────────────────────

class BacktestSummaryResponse(BaseModel):
    """백테스트 성과 요약."""
    v8_walk_forward: Optional[str]       = None   # wf_performance_summary.txt 내용
    comparison:      Optional[list[Any]] = None   # comparison_summary.csv 행들


class BacktestMonthlyResponse(BaseModel):
    """월별 수익률 원시 데이터."""
    data: list[Any]


# ── 종목 검색 ──────────────────────────────────────────────────────────────────

class StockSearchResult(BaseModel):
    """검색 결과 단건."""
    ticker:        str
    name:          Optional[str]  = None
    sector:        Optional[str]  = None
    mid_sector:    Optional[str]  = None
    close:         Optional[float] = None   # 현재가 (scores.close)
    change_pct:    Optional[float] = None   # 전일 대비 등락률
    score:         Optional[float] = None   # 최신 날짜 ML 점수
    tier:          Optional[str]  = None
    model_version: Optional[str]  = None
    latest_date:   Optional[str]  = None
    # P0~P1 후처리 필드 (search_stocks 도 attach_* 호출함)
    signal_label:    Optional[str]   = None
    signal_label_ko: Optional[str]   = None
    star_rating:     Optional[float] = None
    percentile_in_sector: Optional[float] = None
    sector_rank:     Optional[int]   = None
    sector_total:    Optional[int]   = None


class StockSearchList(BaseModel):
    query: str
    total: int
    items: list[StockSearchResult]


# ── 현재가 ──────────────────────────────────────────────────────────────────────

class StockPrice(BaseModel):
    """종목 최신 현재가."""
    ticker:        str
    name:          Optional[str]  = None
    close:         Optional[float] = None
    current_price: Optional[float] = None   # close 의 별칭 (프론트 호환)
    open:          Optional[float] = None
    high:          Optional[float] = None
    low:           Optional[float] = None
    volume:        Optional[int]  = None
    date:          Optional[str]  = None


# ── 급상승 종목 ─────────────────────────────────────────────────────────────────

class RisingStockItem(BaseModel):
    """점수 급상승 종목 단건."""
    ticker:        str
    name:          Optional[str]  = None
    sector:        Optional[str]  = None
    score:         float
    score_prev:    float
    score_change:  float
    tier:          str
    date:          str
    model_version: str


class RisingStockList(BaseModel):
    total:         int
    date:          str
    model_version: str
    items:         list[RisingStockItem]


# ── 커스텀 백테스트 ─────────────────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    min_score:     float = 60.0
    top_k:         int   = 20
    rebalance:     str   = "monthly"    # "monthly" | "quarterly"
    start_date:    str   = "2023-01-01"
    end_date:      str   = "2024-12-31"
    model_version: str   = "latest"


class BacktestMonthlyItem(BaseModel):
    month:     str
    strategy:  float
    benchmark: float


class CustomBacktestResponse(BaseModel):
    total_return:     float
    benchmark_return: float
    mdd:              float
    sharpe:           float
    win_rate:         float
    trade_count:      int
    monthly:          list[BacktestMonthlyItem]
