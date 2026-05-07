"""
test_triple_barrier.py
======================
Tier 1B 4.3 — Triple Barrier 라벨 단위 테스트.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from triple_barrier import (  # noqa: E402
    TripleBarrierParams,
    label_series,
    label_simple_binary,
    label_single,
)


# ── Triple Barrier 단일 라벨 ──────────────────────────────────────────────

def test_upper_barrier_hit_first_returns_1():
    # +10% 가 +7% 상단을 먼저 친다 → 1.
    prices = np.array([100.0, 105.0, 110.0, 95.0, 100.0])
    out = label_single(prices, t=0, params=TripleBarrierParams(0.07, 0.04, horizon=4))
    assert out == 1


def test_lower_barrier_hit_first_returns_0():
    # -5% 가 -4% 하단을 먼저 친다 → 0.
    prices = np.array([100.0, 99.0, 95.0, 110.0, 100.0])
    out = label_single(prices, t=0, params=TripleBarrierParams(0.07, 0.04, horizon=4))
    assert out == 0


def test_no_barrier_hit_uses_terminal_sign():
    # +3% 만 갔고 만료 시 +3% > 0 → 1.
    prices = np.array([100.0, 101.0, 102.0, 102.5, 103.0])
    out = label_single(prices, t=0, params=TripleBarrierParams(0.07, 0.04, horizon=4))
    assert out == 1


def test_no_barrier_hit_negative_terminal():
    # 변동 작고 만료 시 -2% → 0.
    prices = np.array([100.0, 100.5, 99.5, 99.0, 98.0])
    out = label_single(prices, t=0, params=TripleBarrierParams(0.07, 0.04, horizon=4))
    assert out == 0


def test_horizon_exceeds_series_returns_none():
    prices = np.array([100.0, 101.0, 102.0])
    out = label_single(prices, t=0, params=TripleBarrierParams(0.07, 0.04, horizon=20))
    assert out is None


def test_zero_or_negative_price_safe():
    prices = np.array([0.0, 100.0, 110.0])
    out = label_single(prices, t=0, params=TripleBarrierParams())
    assert out is None


# ── label_series ───────────────────────────────────────────────────────────

def test_label_series_marks_unfinishable_with_minus_one():
    # 짧은 시계열 — 마지막 horizon 행은 -1.
    prices = np.linspace(100, 110, 30)   # 단조 증가.
    p = TripleBarrierParams(0.07, 0.04, horizon=20)
    out = label_series(prices, p)
    # 처음 10 행은 +10% 도달 가능 → 1. 마지막 20 행은 -1 (horizon 부족).
    assert out[0] == 1
    assert (out[-20:] == -1).all()


def test_label_series_returns_correct_length():
    prices = np.linspace(100, 105, 40)
    out = label_series(prices, TripleBarrierParams(horizon=10))
    assert len(out) == 40


# ── 단순 이진 라벨 (비교 baseline) ─────────────────────────────────────────

def test_simple_binary_threshold_5pct():
    prices = np.array([100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 105.5])  # +5.5% in 6 steps
    out = label_simple_binary(prices, horizon=6, threshold=0.05)
    assert out[0] == 1


def test_simple_binary_below_threshold():
    prices = np.array([100.0] * 6 + [104.5])    # +4.5% < 5%
    out = label_simple_binary(prices, horizon=6, threshold=0.05)
    assert out[0] == 0
