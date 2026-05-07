"""
test_market_events.py
=====================
W8 축소 — services/market_events 의 *순수 함수* (classify_regime) 단위 테스트.
load_kospi_daily_change 는 데이터 어댑터라 별도 통합 테스트.
"""

from __future__ import annotations

import math

from Back.FastAPI.services.market_events import (
    EXTREME_THRESHOLD,
    classify_regime,
)


def test_extreme_threshold_default():
    assert EXTREME_THRESHOLD == -0.03


def test_normal_at_zero_change():
    assert classify_regime(0.0) == "normal"


def test_normal_for_positive_change():
    assert classify_regime(0.05) == "normal"


def test_extreme_at_threshold():
    """경계값 -3.0% 정확히 → extreme (≤ 비교)."""
    assert classify_regime(-0.03) == "extreme_volatility"


def test_extreme_below_threshold():
    assert classify_regime(-0.05) == "extreme_volatility"
    assert classify_regime(-0.10) == "extreme_volatility"


def test_normal_just_above_threshold():
    assert classify_regime(-0.029) == "normal"


def test_nan_returns_normal():
    """NaN/inf — 보수적 default."""
    assert classify_regime(float("nan")) == "normal"


def test_invalid_input_returns_normal():
    assert classify_regime(None)  == "normal"      # type: ignore[arg-type]
    assert classify_regime("foo") == "normal"      # type: ignore[arg-type]


def test_custom_threshold():
    assert classify_regime(-0.04, threshold=-0.05) == "normal"
    assert classify_regime(-0.06, threshold=-0.05) == "extreme_volatility"
