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


class StockScoreList(BaseModel):
    """추천 목록 응답."""
    date:          str
    model_version: str
    total:         int
    items:         list[StockScore]


# ── 종목 이력 ──────────────────────────────────────────────────────────────────

class StockHistoryItem(BaseModel):
    """단일 종목의 날짜별 스코어 한 행."""
    date:           str
    ticker:         str
    name:           Optional[str]  = None
    sector:         Optional[str]  = None
    close:          Optional[float] = None
    prob_ensemble:  float
    score:          float
    tier:           str
    rank_in_date:   int
    total_in_date:  int
    model_version:  str


class StockHistory(BaseModel):
    """종목 이력 응답."""
    ticker:        str
    model_version: str
    total:         int
    items:         list[StockHistoryItem]


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
    score:         Optional[float] = None   # 최신 날짜 ML 점수
    tier:          Optional[str]  = None
    model_version: Optional[str]  = None
    latest_date:   Optional[str]  = None


class StockSearchList(BaseModel):
    query: str
    total: int
    items: list[StockSearchResult]
