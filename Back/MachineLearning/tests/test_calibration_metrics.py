"""
test_calibration_metrics.py
===========================
Tier 1B 4.1 — ECE·Brier·Reliability 단위 테스트.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from calibration_metrics import (  # noqa: E402
    brier_score,
    calibration_bundle,
    expected_calibration_error,
    per_slice_ece,
    reliability_diagram,
)


# ── ECE ────────────────────────────────────────────────────────────────────

def test_perfect_calibration_zero_ece():
    """정확히 calibrated: prob=0.5 인 1000건 중 정확히 절반이 양성."""
    np.random.seed(0)
    y_prob = np.full(1000, 0.5)
    # 절반은 1, 절반은 0.
    y_true = np.array([1] * 500 + [0] * 500)
    np.random.shuffle(y_true)
    assert expected_calibration_error(y_true, y_prob, n_bins=10) < 0.01


def test_completely_miscalibrated_high_ece():
    """모델이 1.0 으로 자신만만하지만 실제로는 0% 양성 → ECE = 1.0."""
    y_true = np.zeros(100, dtype=int)
    y_prob = np.ones(100)
    assert expected_calibration_error(y_true, y_prob, n_bins=10) > 0.99


def test_ece_bounded_zero_to_one():
    np.random.seed(1)
    y_true = np.random.randint(0, 2, 500)
    y_prob = np.random.random(500)
    e = expected_calibration_error(y_true, y_prob, 10)
    assert 0.0 <= e <= 1.0


def test_ece_handles_empty():
    assert expected_calibration_error(np.array([]), np.array([])) == 0.0


def test_ece_validates_prob_range():
    with pytest.raises(ValueError):
        expected_calibration_error(np.array([0, 1]), np.array([-0.1, 1.5]))


# ── Brier ──────────────────────────────────────────────────────────────────

def test_brier_zero_for_perfect_prediction():
    y_true = np.array([1, 0, 1, 0])
    y_prob = np.array([1.0, 0.0, 1.0, 0.0])
    assert brier_score(y_true, y_prob) == 0.0


def test_brier_quarter_for_random_50():
    y_true = np.array([1, 0, 1, 0])
    y_prob = np.array([0.5, 0.5, 0.5, 0.5])
    assert abs(brier_score(y_true, y_prob) - 0.25) < 1e-9


# ── Reliability Diagram ────────────────────────────────────────────────────

def test_reliability_returns_n_bins():
    np.random.seed(2)
    y_true = np.random.randint(0, 2, 500)
    y_prob = np.random.random(500)
    bins = reliability_diagram(y_true, y_prob, n_bins=10)
    assert len(bins) == 10
    assert all(b.bin_lower < b.bin_upper for b in bins)
    assert sum(b.count for b in bins) == 500


def test_reliability_empty_input():
    assert reliability_diagram(np.array([]), np.array([])) == []


# ── Bundle ─────────────────────────────────────────────────────────────────

def test_calibration_bundle_round_trip():
    np.random.seed(3)
    y_prob = np.linspace(0.05, 0.95, 200)
    # 약하게 calibrated: 양성 빈도가 prob 와 비례.
    y_true = (np.random.random(200) < y_prob).astype(int)
    b = calibration_bundle(y_true, y_prob, n_bins=10)
    d = b.to_dict()
    assert set(d.keys()) == {"n_observations", "n_bins", "ece", "brier", "bins"}
    assert d["n_observations"] == 200
    assert len(d["bins"]) == 10
    # reasonably calibrated → ECE 작아야 함.
    assert d["ece"] < 0.15


# ── Per-slice ──────────────────────────────────────────────────────────────

def test_per_slice_ece_groups_correctly():
    np.random.seed(4)
    y_true = np.random.randint(0, 2, 600)
    y_prob = np.random.random(600)
    slice_keys = np.array(["A"] * 200 + ["B"] * 200 + ["C"] * 200)
    out = per_slice_ece(y_true, y_prob, slice_keys, n_bins=10, min_count=50)
    assert set(out.keys()) == {"A", "B", "C"}
    for k in "ABC":
        assert out[k]["n"] == 200
        assert "ece" in out[k]


def test_per_slice_ece_skips_below_min_count():
    y_true = np.array([1, 0, 1, 0, 1])
    y_prob = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
    keys   = np.array(["A", "A", "B", "C", "C"])
    out = per_slice_ece(y_true, y_prob, keys, n_bins=5, min_count=3)
    # A=2 (skip), B=1 (skip), C=2 (skip).
    assert out == {}
