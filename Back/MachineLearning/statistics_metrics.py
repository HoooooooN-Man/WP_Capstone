"""
statistics_metrics.py
=====================
Tier 1.1 (PRD §3.5.4 / 캡스톤 §3.1) — 다중 검정 보정 통계.

본 모듈은 *순수 함수* 만 제공하며, I/O 는 부모 호출자가 담당.
Holdout 박제·평가 하네스·리포트 모두 본 모듈을 재사용한다.

핵심 지표:
  - sharpe_ratio(returns, periods_per_year)      — 단순 Sharpe
  - probabilistic_sharpe_ratio(sr, n, skew, kurt, sr_threshold=0)
        López de Prado (2014) Eq.13: PSR
  - deflated_sharpe_ratio(sr, n, skew, kurt, n_trials, sr_max_var)
        López de Prado (2014) Eq.20: DSR (Sharpe 의 multiple-testing 보정)

참고:
  - López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for
    Selection Bias, Backtest Overfitting, and Non-Normality."
    Journal of Portfolio Management.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


# ── 단순 통계 ──────────────────────────────────────────────────────────────

def sharpe_ratio(returns: np.ndarray, periods_per_year: int = 252) -> float:
    """
    단순 Sharpe (risk-free=0 가정). 캡스톤 holdout 평가의 기본값.

    returns: 수익률 시계열 (소수, 예: 0.01 = +1%)
    periods_per_year: 일별 252, 주별 52, 월별 12.
    """
    if len(returns) < 2:
        return 0.0
    r = np.asarray(returns, dtype=float)
    mu = float(np.mean(r))
    sd = float(np.std(r, ddof=1))
    if sd <= 0:
        return 0.0
    return mu / sd * math.sqrt(periods_per_year)


def excess_return_stats(returns: np.ndarray) -> dict:
    """returns 의 기본 모멘트 — DSR 계산용."""
    r = np.asarray(returns, dtype=float)
    n = int(len(r))
    if n < 4:
        return {"n": n, "mean": float(np.mean(r)) if n else 0.0,
                "std": 0.0, "skew": 0.0, "kurt": 0.0}
    mu = float(np.mean(r))
    sd = float(np.std(r, ddof=1))
    # Fisher 's definition (kurt - 3) — DSR 식이 expected 이미 빼는 형태.
    sk = float(stats.skew(r, bias=False))
    ku = float(stats.kurtosis(r, fisher=False, bias=False))   # 정규분포 = 3
    return {"n": n, "mean": mu, "std": sd, "skew": sk, "kurt": ku}


# ── PSR (Probabilistic Sharpe Ratio) ───────────────────────────────────────

def probabilistic_sharpe_ratio(
    sr_observed: float,
    n: int,
    skew: float,
    kurt: float,
    sr_threshold: float = 0.0,
) -> float:
    """
    PSR — observed SR 가 sr_threshold 보다 *진짜로* 높을 확률.
    López de Prado (2014) Eq.13.

    sr_observed: Sharpe (annualized 또는 그대로). 단, 같은 단위로 sr_threshold 표기.
    n: 관측 수.
    skew, kurt: returns 의 표본 왜도·첨도 (kurt 는 raw, 정규=3).
    """
    if n < 4:
        return 0.5
    # Sharpe 의 표준오차 (Mertens 의 비정규 보정).
    var_sr = (1 - skew * sr_observed + (kurt - 1) / 4.0 * sr_observed ** 2) / (n - 1)
    if var_sr <= 0:
        return 1.0 if sr_observed > sr_threshold else 0.0
    z = (sr_observed - sr_threshold) / math.sqrt(var_sr)
    return float(stats.norm.cdf(z))


# ── DSR (Deflated Sharpe Ratio) ────────────────────────────────────────────

def expected_max_sharpe(n_trials: int, sr_var_across_trials: float) -> float:
    """
    여러 trial 중 *우연히* 가장 높은 SR 의 기대값.
    López de Prado (2014) Eq.18 — Bailey & López de Prado approx.

    sr_var_across_trials: trial 간 SR 분산 (단일 trial 시 0 → 0 반환).
    """
    if n_trials <= 1 or sr_var_across_trials <= 0:
        return 0.0
    eulergamma = 0.5772156649015329
    a = (1 - eulergamma) * stats.norm.ppf(1 - 1.0 / n_trials)
    b = eulergamma * stats.norm.ppf(1 - 1.0 / (n_trials * math.e))
    return math.sqrt(sr_var_across_trials) * (a + b)


def deflated_sharpe_ratio(
    sr_observed: float,
    n: int,
    skew: float,
    kurt: float,
    n_trials: int = 1,
    sr_var_across_trials: float = 0.0,
) -> float:
    """
    DSR — 다중 검정(N trials) 중 *베스트* SR 가 진실일 확률.
    López de Prado (2014) Eq.20.

    n_trials=1 + sr_var_across_trials=0 → PSR(threshold=0) 와 동일.
    """
    sr_threshold = expected_max_sharpe(n_trials, sr_var_across_trials)
    return probabilistic_sharpe_ratio(sr_observed, n, skew, kurt, sr_threshold)


# ── 종합 결과 dataclass ────────────────────────────────────────────────────

@dataclass
class SharpeBundle:
    """Holdout 박제용 — Sharpe + 보정 통계 한 묶음."""
    n_observations: int
    mean_return: float
    std_return: float
    skewness: float
    kurtosis: float
    sharpe_ratio: float
    psr_threshold_0: float
    dsr_n1: float          # 단일 trial 가정 DSR (= PSR with threshold=0)

    def to_dict(self) -> dict:
        return {
            "n_observations":    self.n_observations,
            "mean_return":       round(self.mean_return, 6),
            "std_return":        round(self.std_return, 6),
            "skewness":          round(self.skewness, 4),
            "kurtosis":          round(self.kurtosis, 4),
            "sharpe_ratio":      round(self.sharpe_ratio, 4),
            "psr_threshold_0":   round(self.psr_threshold_0, 4),
            "dsr_n1":            round(self.dsr_n1, 4),
        }


def compute_sharpe_bundle(
    returns: np.ndarray,
    periods_per_year: int = 252,
) -> SharpeBundle:
    """
    Holdout 박제용: Sharpe + Mertens 보정 통계 + DSR(n=1) 한 번에.
    n_trials > 1 평가는 *향후* 모델 비교 시 별도 갱신.
    """
    s = excess_return_stats(returns)
    sr = sharpe_ratio(returns, periods_per_year)
    psr0 = probabilistic_sharpe_ratio(sr, s["n"], s["skew"], s["kurt"], 0.0)
    return SharpeBundle(
        n_observations=s["n"],
        mean_return=s["mean"],
        std_return=s["std"],
        skewness=s["skew"],
        kurtosis=s["kurt"],
        sharpe_ratio=sr,
        psr_threshold_0=psr0,
        dsr_n1=psr0,           # n_trials=1 일 때 DSR = PSR(0)
    )
