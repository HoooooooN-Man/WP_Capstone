"""
test_statistics_metrics.py
==========================
Tier 1.1 — Sharpe·PSR·DSR 단위 테스트.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from statistics_metrics import (  # noqa: E402
    compute_sharpe_bundle,
    deflated_sharpe_ratio,
    excess_return_stats,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    sharpe_ratio,
)


# ── Sharpe ─────────────────────────────────────────────────────────────────

def test_sharpe_zero_for_constant_returns():
    r = np.array([0.001, 0.001, 0.001, 0.001])
    # std = 0 → Sharpe 정의 불가, 안전하게 0 반환 보장.
    assert sharpe_ratio(r) == 0.0


def test_sharpe_positive_for_positive_mean_low_variance():
    np.random.seed(42)
    r = np.random.normal(0.001, 0.005, 252)
    sr = sharpe_ratio(r)
    # 기대값 ~3 (mu=0.001, sd=0.005, periods=252).
    assert sr > 1.5


def test_sharpe_returns_zero_for_too_few_observations():
    assert sharpe_ratio(np.array([0.01])) == 0.0
    assert sharpe_ratio(np.array([])) == 0.0


# ── 모멘트 ─────────────────────────────────────────────────────────────────

def test_excess_return_stats_basic():
    np.random.seed(0)
    r = np.random.normal(0, 1, 1000)
    s = excess_return_stats(r)
    assert s["n"] == 1000
    assert abs(s["mean"]) < 0.1
    assert abs(s["std"] - 1.0) < 0.1
    # 정규분포 → kurt ≈ 3.
    assert abs(s["kurt"] - 3.0) < 0.5


# ── PSR ────────────────────────────────────────────────────────────────────

def test_psr_returns_half_for_zero_observed_sr_normal_returns():
    # 정규분포 + sr=0 → P(sr_observed > 0) = 0.5.
    psr = probabilistic_sharpe_ratio(0.0, n=100, skew=0.0, kurt=3.0, sr_threshold=0.0)
    assert abs(psr - 0.5) < 1e-6


def test_psr_increases_with_observed_sr():
    p_low  = probabilistic_sharpe_ratio(0.5, n=252, skew=0.0, kurt=3.0)
    p_high = probabilistic_sharpe_ratio(1.5, n=252, skew=0.0, kurt=3.0)
    assert p_high > p_low
    assert p_high > 0.95   # 명확하게 진실 가능성 높음.


def test_psr_decreases_with_smaller_sample():
    # 같은 SR 인데 n 이 작으면 신뢰도 하락.
    p_large = probabilistic_sharpe_ratio(1.0, n=1000, skew=0.0, kurt=3.0)
    p_small = probabilistic_sharpe_ratio(1.0, n=20,   skew=0.0, kurt=3.0)
    assert p_large > p_small


def test_psr_handles_tiny_sample():
    # n<4 → 0.5 (정보 부족) 로 안전 반환.
    assert probabilistic_sharpe_ratio(2.0, n=2, skew=0, kurt=3) == 0.5


# ── DSR ────────────────────────────────────────────────────────────────────

def test_dsr_equals_psr_zero_when_n_trials_one():
    # n_trials=1, var_across=0 → expected_max_sr = 0 → DSR = PSR(threshold=0).
    sr, n = 1.2, 252
    dsr = deflated_sharpe_ratio(sr, n, skew=0.0, kurt=3.0, n_trials=1)
    psr = probabilistic_sharpe_ratio(sr, n, skew=0.0, kurt=3.0, sr_threshold=0.0)
    assert abs(dsr - psr) < 1e-9


def test_dsr_strictly_lower_than_psr_for_many_trials():
    # 같은 관측 SR 인데 trial 수가 크면 DSR 이 더 낮아야 함 (selection bias 보정).
    sr, n = 1.2, 252
    psr = probabilistic_sharpe_ratio(sr, n, skew=0.0, kurt=3.0, sr_threshold=0.0)
    dsr = deflated_sharpe_ratio(sr, n, skew=0.0, kurt=3.0,
                                n_trials=200, sr_var_across_trials=0.5)
    assert dsr < psr


def test_expected_max_sharpe_zero_when_single_trial():
    assert expected_max_sharpe(1, 1.0) == 0.0
    assert expected_max_sharpe(10, 0.0) == 0.0


def test_expected_max_sharpe_grows_with_trials():
    e10  = expected_max_sharpe(10,  1.0)
    e100 = expected_max_sharpe(100, 1.0)
    assert e100 > e10 > 0.0


# ── Bundle ─────────────────────────────────────────────────────────────────

def test_compute_sharpe_bundle_round_trip():
    np.random.seed(7)
    r = np.random.normal(0.001, 0.01, 252)
    b = compute_sharpe_bundle(r)
    d = b.to_dict()
    expected_keys = {
        "n_observations", "mean_return", "std_return",
        "skewness", "kurtosis", "sharpe_ratio",
        "psr_threshold_0", "dsr_n1",
    }
    assert set(d.keys()) == expected_keys
    assert d["n_observations"] == 252
    assert isinstance(d["sharpe_ratio"], float)
    # n_trials=1 일 때 DSR == PSR(0).
    assert abs(d["psr_threshold_0"] - d["dsr_n1"]) < 1e-9
