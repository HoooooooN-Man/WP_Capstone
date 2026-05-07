"""
test_embeddings_data.py
=======================
W3.5A — 시계열·augmentation 순수 함수 단위 테스트.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from embeddings.data import (
    AugmentParams,
    add_gaussian_noise,
    augment_series,
    extract_windows,
    mask_random,
    series_from_prices,
    time_jitter,
)


# ── series_from_prices ───────────────────────────────────────────────────

def test_series_shape_and_log_diff():
    close = np.array([100.0, 110.0, 121.0])     # +10%, +10%
    vol   = np.array([1000.0, 2000.0, 1000.0])  # ×2, ÷2
    s = series_from_prices(close, vol)
    assert s.shape == (2, 2)
    # 채널 0 (log return) ≈ log(1.1) twice
    assert np.allclose(s[:, 0], np.log(1.1), atol=1e-5)
    # 채널 1: log(2), log(0.5)
    assert s[0, 1] == pytest.approx(np.log(2.0), abs=1e-5)
    assert s[1, 1] == pytest.approx(np.log(0.5), abs=1e-5)


def test_series_handles_zero_volume_with_eps():
    """volume 0 인 거래정지 일은 eps 보정 — NaN/Inf 안 나옴."""
    close = np.array([100.0, 100.0, 100.0])
    vol   = np.array([1000.0, 0.0, 1000.0])
    s = series_from_prices(close, vol)
    assert s.shape == (2, 2)
    assert np.all(np.isfinite(s))


def test_series_too_short_returns_empty():
    assert series_from_prices(np.array([100.0]), np.array([1000.0])).shape == (0, 2)
    assert series_from_prices(np.array([]), np.array([])).shape == (0, 2)


def test_series_length_mismatch_raises():
    with pytest.raises(ValueError):
        series_from_prices(np.array([1.0, 2.0]), np.array([1.0]))


# ── extract_windows ──────────────────────────────────────────────────────

def test_extract_windows_shapes():
    series = np.zeros((100, 2), dtype=np.float32)
    out = extract_windows(series, window=60, stride=5)
    # starts: 0, 5, 10, ..., 40 → 9 windows.
    assert out.shape == (9, 60, 2)


def test_extract_windows_too_short_returns_empty():
    series = np.zeros((30, 2), dtype=np.float32)
    out = extract_windows(series, window=60, stride=5)
    assert out.shape == (0, 60, 2)


def test_extract_windows_validates_2d():
    with pytest.raises(ValueError):
        extract_windows(np.zeros((100,)), window=10, stride=1)


# ── mask_random ──────────────────────────────────────────────────────────

def test_mask_random_zeros_correct_count():
    rng = np.random.default_rng(42)
    w = np.ones((60, 2), dtype=np.float32)
    out = mask_random(w, mask_pct=0.20, rng=rng)
    # 20% of 60 = 12 시점 — 채널 모두 0.
    zero_rows = np.sum(np.all(out == 0.0, axis=1))
    assert zero_rows == 12


def test_mask_random_zero_pct_no_change():
    w = np.ones((60, 2), dtype=np.float32)
    out = mask_random(w, mask_pct=0.0)
    assert np.array_equal(out, w)


def test_mask_random_does_not_mutate_input():
    w = np.ones((60, 2), dtype=np.float32)
    mask_random(w, mask_pct=0.5)
    assert np.all(w == 1.0)


# ── add_gaussian_noise ───────────────────────────────────────────────────

def test_noise_zero_sigma_returns_copy():
    w = np.ones((10, 2), dtype=np.float32)
    out = add_gaussian_noise(w, sigma=0.0)
    assert np.array_equal(out, w)
    assert out is not w


def test_noise_changes_values_under_positive_sigma():
    rng = np.random.default_rng(7)
    w = np.zeros((100, 2), dtype=np.float32)
    out = add_gaussian_noise(w, sigma=0.1, rng=rng)
    # 표본 표준편차가 약 σ.
    assert 0.05 < out.std() < 0.15


# ── time_jitter ──────────────────────────────────────────────────────────

def test_time_jitter_zero_max_shift_no_change():
    w = np.arange(20, dtype=np.float32).reshape(10, 2)
    out = time_jitter(w, max_shift=0)
    assert np.array_equal(out, w)


def test_time_jitter_shifts_with_zero_pad():
    """positive shift → 앞쪽 zero-pad, 끝부분 잘림."""
    w = np.arange(20, dtype=np.float32).reshape(10, 2)
    # +1 shift 강제: rng.integers 가 1 반환하도록 monkey-patch.

    class _RNG:
        def integers(self, lo, hi): return 1

    out = time_jitter(w, max_shift=2, rng=_RNG())
    # out[0] should be zero (padded), out[1:] should match w[:-1].
    assert np.all(out[0] == 0.0)
    assert np.array_equal(out[1:], w[:-1])


def test_time_jitter_negative_shift_zero_pad_at_end():
    w = np.arange(20, dtype=np.float32).reshape(10, 2)

    class _RNG:
        def integers(self, lo, hi): return -1

    out = time_jitter(w, max_shift=2, rng=_RNG())
    assert np.all(out[-1] == 0.0)
    assert np.array_equal(out[:-1], w[1:])


# ── augment_series 통합 ───────────────────────────────────────────────────

def test_augment_series_preserves_shape():
    rng = np.random.default_rng(0)
    w = np.random.RandomState(0).randn(60, 2).astype(np.float32)
    out = augment_series(w, AugmentParams(), rng=rng)
    assert out.shape == w.shape
    assert out.dtype == np.float32


def test_augment_series_two_views_differ():
    """같은 입력에 두 번 augment 하면 *서로 다른* view 가 나와야 한다."""
    rng = np.random.default_rng(1)
    w = np.random.RandomState(1).randn(60, 2).astype(np.float32)
    v1 = augment_series(w, rng=rng)
    v2 = augment_series(w, rng=rng)
    assert not np.array_equal(v1, v2)


def test_augment_params_validates_pct_bounds():
    with pytest.raises(AssertionError):
        AugmentParams(mask_pct_low=0.5, mask_pct_high=0.3)
    with pytest.raises(AssertionError):
        AugmentParams(noise_sigma=-0.1)
