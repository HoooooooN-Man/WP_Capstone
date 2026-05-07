"""
test_multi_labels.py
====================
W4 — 5 멀티 라벨 raw 값 계산 단위 테스트.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from multi_labels import (
    alpha_vs_benchmark,
    compute_all_labels,
    forward_return,
    forward_sharpe,
)


# ── forward_return ──────────────────────────────────────────────────────

def test_forward_return_basic_positive():
    close = np.array([100.0, 102.0, 105.0, 110.0, 110.0, 110.0])
    out = forward_return(close, horizon=3)
    # t=0: 110/100 - 1 = 0.10
    assert out[0] == pytest.approx(0.10, abs=1e-5)
    # 마지막 horizon 개는 NaN.
    assert np.isnan(out[-3:]).all()


def test_forward_return_negative():
    close = np.array([100.0, 95.0, 90.0])
    out = forward_return(close, horizon=2)
    # t=0: 90/100 - 1 = -0.10
    assert out[0] == pytest.approx(-0.10, abs=1e-5)
    assert np.isnan(out[1])
    assert np.isnan(out[2])


def test_forward_return_zero_base_returns_nan():
    """base 가 0 또는 음수면 NaN."""
    close = np.array([0.0, 100.0, 110.0])
    out = forward_return(close, horizon=2)
    assert np.isnan(out[0])


def test_forward_return_too_short_returns_all_nan():
    close = np.array([100.0, 105.0])
    out = forward_return(close, horizon=5)
    assert np.isnan(out).all()


def test_forward_return_zero_horizon_all_nan():
    close = np.array([100.0, 105.0, 110.0])
    out = forward_return(close, horizon=0)
    assert np.isnan(out).all()


# ── alpha_vs_benchmark ──────────────────────────────────────────────────

def test_alpha_outperforms_benchmark():
    """종목 +10% 상승, 벤치 +5% → alpha = +5%."""
    close = np.array([100.0, 0.0, 0.0, 0.0, 110.0])
    bench = np.array([100.0, 0.0, 0.0, 0.0, 105.0])
    a = alpha_vs_benchmark(close, bench, horizon=4)
    assert a[0] == pytest.approx(0.05, abs=1e-5)


def test_alpha_underperforms_negative():
    close = np.array([100.0, 0.0, 0.0, 95.0])
    bench = np.array([100.0, 0.0, 0.0, 105.0])
    a = alpha_vs_benchmark(close, bench, horizon=3)
    # -5% vs +5% → -10%
    assert a[0] == pytest.approx(-0.10, abs=1e-5)


def test_alpha_length_mismatch_raises():
    with pytest.raises(ValueError):
        alpha_vs_benchmark(np.array([1.0, 2.0]), np.array([1.0]), horizon=1)


# ── forward_sharpe ──────────────────────────────────────────────────────

def test_forward_sharpe_positive_for_steady_uptrend():
    """매일 +0.5% 안정 상승 — sharpe 매우 큼 (분산 ≈ 0)."""
    rng = np.random.default_rng(0)
    base = 100.0
    daily_returns = np.full(40, 0.005) + rng.normal(0, 1e-5, 40)
    close = [base]
    for r in daily_returns:
        close.append(close[-1] * (1 + r))
    close = np.array(close)
    out = forward_sharpe(close, horizon=20)
    # t=0 sharpe 양수 ·매우 큼 (μ/σ ≫ 1).
    assert out[0] > 5.0


def test_forward_sharpe_negative_for_downtrend():
    rng = np.random.default_rng(1)
    daily_returns = np.full(40, -0.005) + rng.normal(0, 1e-5, 40)
    close = [100.0]
    for r in daily_returns:
        close.append(close[-1] * (1 + r))
    close = np.array(close)
    out = forward_sharpe(close, horizon=20)
    assert out[0] < -5.0


def test_forward_sharpe_zero_volatility_returns_nan():
    """log return 이 모두 동일 → 표준편차 0 → NaN."""
    close = np.array([100.0] * 25, dtype=float)   # 변동 0
    close[1:] = 100.0 * (1.001 ** np.arange(1, 25))
    # 정확히 동일 increment 라 std → 0.
    out = forward_sharpe(close, horizon=20)
    assert np.isnan(out[0])


def test_forward_sharpe_too_short_all_nan():
    close = np.array([100.0, 101.0, 102.0])
    out = forward_sharpe(close, horizon=20)
    assert np.isnan(out).all()


# ── compute_all_labels 종합 ─────────────────────────────────────────────

def test_compute_all_labels_returns_seven_keys():
    rng = np.random.default_rng(2)
    close = 100 * np.cumprod(1 + rng.normal(0.001, 0.01, 100))
    bench = 100 * np.cumprod(1 + rng.normal(0.0005, 0.008, 100))
    out = compute_all_labels(close, bench)
    assert set(out.keys()) == {
        "fwd_return_5d", "fwd_return_20d", "fwd_return_60d",
        "alpha_5d", "alpha_20d", "alpha_60d",
        "sharpe_20d",
    }
    for k, v in out.items():
        assert v.shape == close.shape, f"{k} shape mismatch"


def test_compute_all_labels_horizon_60_largest_nan_tail():
    """60d 라벨이 가장 긴 NaN 꼬리를 가짐 — 5d < 20d < 60d 순."""
    close = 100 * np.cumprod(1 + np.full(80, 0.001))
    bench = 100 * np.cumprod(1 + np.full(80, 0.0005))
    out = compute_all_labels(close, bench)
    n5  = np.isnan(out["fwd_return_5d"]).sum()
    n20 = np.isnan(out["fwd_return_20d"]).sum()
    n60 = np.isnan(out["fwd_return_60d"]).sum()
    assert n5  == 5
    assert n20 == 20
    assert n60 == 60
    assert n5 < n20 < n60


def test_compute_all_labels_alpha_consistency():
    """alpha_5d = fwd_return_5d(stock) - fwd_return_5d(bench)."""
    rng = np.random.default_rng(3)
    close = 100 * np.cumprod(1 + rng.normal(0.001, 0.01, 50))
    bench = 100 * np.cumprod(1 + rng.normal(0.0005, 0.008, 50))
    out = compute_all_labels(close, bench)
    # alpha_5d 가 stock fwd - bench fwd 와 일치.
    bench_fwd = forward_return(bench, 5)
    expected = out["fwd_return_5d"] - bench_fwd
    # NaN 위치 동일.
    valid = ~np.isnan(out["alpha_5d"]) & ~np.isnan(expected)
    assert np.allclose(out["alpha_5d"][valid], expected[valid], atol=1e-5)
