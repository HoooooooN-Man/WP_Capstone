"""
eval_harness/metrics/bundle.py
==============================
평가 하네스 메트릭 5종 한 묶음 (캡스톤 §3.2).

  - AUC          : 분류 — prob 의 ranking 능력
  - ECE          : 분류 — 캘리브레이션 (10-bin)
  - Sharpe       : 운용 — Tier A 평균 forward return 의 risk-adjusted (annualized)
  - MDD          : 운용 — period-wise equity curve 의 max drawdown
  - alpha vs KOSPI: 운용 — strategy - benchmark 누적 수익률 차

설계 의도:
  - 한 슬라이스(rows + periods) 에 대해 본 함수가 5개 메트릭을 일괄 산출.
  - rows 가 비어있거나 라벨이 1종(전부 0 또는 전부 1)이면 일부 메트릭은 None.
  - periods 가 비어있으면 운용 메트릭(Sharpe/MDD/alpha) 은 None.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

# 같은 패키지 안의 절대 임포트.
from calibration_metrics import expected_calibration_error
from statistics_metrics  import sharpe_ratio


PERIODS_PER_YEAR = 13   # 20거래일 단위 → 252/20 ≈ 13


@dataclass
class MetricBundle:
    """한 슬라이스의 5개 메트릭 + 진단 메타."""
    n_rows:   int
    n_periods: int
    auc:      Optional[float] = None
    ece:      Optional[float] = None
    sharpe:   Optional[float] = None
    mdd:      Optional[float] = None
    alpha_cum: Optional[float] = None   # cumulative strategy - cumulative benchmark
    notes:    list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        def _r(v):
            return None if v is None else round(float(v), 4)
        return {
            "n_rows":    int(self.n_rows),
            "n_periods": int(self.n_periods),
            "auc":       _r(self.auc),
            "ece":       _r(self.ece),
            "sharpe":    _r(self.sharpe),
            "mdd":       _r(self.mdd),
            "alpha_cum": _r(self.alpha_cum),
            "notes":     list(self.notes),
        }


# ── 분류 메트릭 ──────────────────────────────────────────────────────────────

def _safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> Optional[float]:
    if len(y_true) < 10:
        return None
    if len(np.unique(y_true)) < 2:
        return None
    try:
        return float(roc_auc_score(y_true, y_prob))
    except Exception:
        return None


def _safe_ece(y_true: np.ndarray, y_prob: np.ndarray) -> Optional[float]:
    if len(y_true) < 10:
        return None
    try:
        return float(expected_calibration_error(y_true, y_prob, n_bins=10))
    except Exception:
        return None


# ── 운용 메트릭 ──────────────────────────────────────────────────────────────

def _safe_sharpe(returns: np.ndarray) -> Optional[float]:
    if len(returns) < 2:
        return None
    return float(sharpe_ratio(returns, periods_per_year=PERIODS_PER_YEAR))


def _safe_mdd(returns: np.ndarray) -> Optional[float]:
    if len(returns) < 2:
        return None
    cum = np.cumprod(1 + returns)
    peak = np.maximum.accumulate(cum)
    drawdown = (cum / peak - 1.0)
    return float(drawdown.min())


def _safe_alpha_cum(strat: np.ndarray, bench: np.ndarray) -> Optional[float]:
    if len(strat) < 1 or len(bench) < 1:
        return None
    cum_s = float(np.prod(1 + strat) - 1)
    cum_b = float(np.prod(1 + bench) - 1)
    return cum_s - cum_b


# ── 번들 진입점 ──────────────────────────────────────────────────────────────

def compute_metric_bundle(rows: pd.DataFrame, periods: Optional[pd.DataFrame] = None) -> MetricBundle:
    """
    rows: (label, prob) 컬럼이 있어야 함 (data_loader 가 채워줌).
    periods: (strat_return, bench_return, alpha) 컬럼이 있어야 함.

    어떤 입력이 부족하면 그 메트릭만 None — 다른 메트릭은 계속 산출.
    """
    notes: list[str] = []

    # 분류.
    y_true = rows["label"].values     if "label" in rows.columns else np.array([])
    y_prob = rows["prob"].values      if "prob"  in rows.columns else np.array([])
    auc = _safe_auc(y_true, y_prob)
    ece = _safe_ece(y_true, y_prob)
    if auc is None and len(y_true) > 0 and len(np.unique(y_true)) < 2:
        notes.append("AUC undefined: only 1 class in slice")

    # 운용.
    if periods is not None and not periods.empty and {"strat_return", "bench_return"}.issubset(periods.columns):
        strat = periods["strat_return"].dropna().values
        bench = periods["bench_return"].dropna().values
        sharpe = _safe_sharpe(strat)
        mdd    = _safe_mdd(strat)
        alpha  = _safe_alpha_cum(strat, bench)
        n_periods = int(len(strat))
        if n_periods < 3:
            notes.append(f"financial metrics from only {n_periods} period(s) — interpret as illustrative")
    else:
        sharpe = mdd = alpha = None
        n_periods = 0

    return MetricBundle(
        n_rows=int(len(rows)),
        n_periods=n_periods,
        auc=auc, ece=ece,
        sharpe=sharpe, mdd=mdd, alpha_cum=alpha,
        notes=notes,
    )
