"""
schemas/health.py
=================
헬스체크 / 모델 모니터링 응답 모델.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    status: str
    app: str
    version: str
    docs: str


class HealthResponse(BaseModel):
    status: str
    duckdb_exists: bool
    duckdb_path: str


class DailyScoreMetrics(BaseModel):
    """단일 거래일의 점수 분포 + 티어 분포 + prob 신호 강도."""
    date: str
    n: int = Field(..., description="해당 날짜의 종목 수")
    mean: Optional[float] = None
    median: Optional[float] = None
    stddev: Optional[float] = None
    p10: Optional[float] = None
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    p90: Optional[float] = None
    tier_a: int = 0
    tier_b: int = 0
    tier_c: int = 0
    tier_d: int = 0
    # prob_ensemble 신호 강도 (모니터링용)
    prob_mean:        Optional[float] = Field(None, description="prob_ensemble 평균")
    prob_std:         Optional[float] = Field(None, description="prob_ensemble 표준편차 (낮을수록 클러스터링 심함)")
    prob_min:         Optional[float] = None
    prob_max:         Optional[float] = None
    prob_cluster_pct: Optional[float] = Field(None, description="0.28~0.32 범위 종목 비율 (%)")


class MetricsSummary(BaseModel):
    """드리프트 감지 요약 + 신호 품질."""
    mean_of_means:   Optional[float] = None
    stddev_of_means: Optional[float] = None
    latest_mean:     Optional[float] = None
    drift_alert:     bool = Field(False, description="latest_mean 이 ±2σ 벗어났는지")
    # 신호 품질 (prob_std < 0.03 이면 모델 클러스터링 경고)
    avg_prob_std:    Optional[float] = Field(None, description="기간 평균 prob_std")
    prob_signal_ok:  Optional[bool]  = Field(None, description="avg_prob_std > 0.03 이면 True")


class MetricsResponse(BaseModel):
    status: str = "ok"
    model_version: Optional[str] = None
    window_days:   Optional[int] = None
    metrics:       list[DailyScoreMetrics] = []
    summary:       Optional[MetricsSummary] = None
    error:         Optional[str] = None
