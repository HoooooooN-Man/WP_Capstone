"""
test_personalization.py
=======================
W2A — cohort 기반 reranking 순수 함수 단위 테스트.
"""

from __future__ import annotations

import pytest

from Back.FastAPI.services.personalization import (
    VALID_COHORTS,
    normalize_cohort,
    rerank_for_cohort,
)


# ── 정규화 ───────────────────────────────────────────────────────────────

def test_normalize_handles_none_and_empty():
    assert normalize_cohort(None) is None
    assert normalize_cohort("") is None
    assert normalize_cohort("   ") is None


def test_normalize_balanced_treated_as_none():
    assert normalize_cohort("balanced") is None
    assert normalize_cohort("BALANCED") is None


def test_normalize_unknown_cohort_returns_none():
    """알 수 없는 cohort 는 balanced 와 동치 (no-op)."""
    assert normalize_cohort("aggressive") is None
    assert normalize_cohort("dividend_xx") is None


def test_normalize_valid_lowercase():
    for c in ("conservative", "growth", "dividend", "value"):
        assert normalize_cohort(c) == c
        assert normalize_cohort(c.upper()) == c


def test_valid_cohorts_set_complete():
    assert VALID_COHORTS == {"conservative", "balanced", "growth", "dividend", "value"}


# ── balanced / None — no-op + top_k 컷 ─────────────────────────────────

def test_balanced_returns_input_order_top_k():
    rows = [{"ticker": f"00{i:04}", "score": 100 - i} for i in range(30)]
    out = rerank_for_cohort(rows, None, top_k=5)
    assert len(out) == 5
    assert [r["ticker"] for r in out] == ["000000", "000001", "000002", "000003", "000004"]


def test_balanced_top_k_zero_returns_all():
    rows = [{"ticker": "A", "score": 90}] * 25
    out = rerank_for_cohort(rows, "balanced", top_k=0)
    assert len(out) == 25


def test_unknown_cohort_falls_back_to_balanced():
    rows = [{"ticker": "A", "score": 80}, {"ticker": "B", "score": 70}]
    out = rerank_for_cohort(rows, "weird", top_k=10)
    assert [r["ticker"] for r in out] == ["A", "B"]


# ── conservative — 변동성 하위 50% ─────────────────────────────────────

def test_conservative_filters_high_volatility():
    rows = [
        {"ticker": "LO1", "score": 90, "volatility_60d": 0.10},
        {"ticker": "LO2", "score": 85, "volatility_60d": 0.12},
        {"ticker": "HI1", "score": 80, "volatility_60d": 0.30},
        {"ticker": "HI2", "score": 75, "volatility_60d": 0.40},
    ]
    out = rerank_for_cohort(rows, "conservative", top_k=10)
    tickers = {r["ticker"] for r in out}
    # 중앙값 0.21 이하만 — LO1, LO2.
    assert tickers == {"LO1", "LO2"}


def test_conservative_no_volatility_column_keeps_all():
    """volatility_60d 가 *전혀 없는* 입력 — 미필터 (graceful)."""
    rows = [{"ticker": "A", "score": 90}, {"ticker": "B", "score": 85}]
    out = rerank_for_cohort(rows, "conservative", top_k=10)
    assert len(out) == 2


# ── dividend — 2%↑ 필터 ───────────────────────────────────────────────

def test_dividend_filters_below_two_percent():
    rows = [
        {"ticker": "DIV", "score": 60, "dividend_yield": 0.04},
        {"ticker": "MID", "score": 80, "dividend_yield": 0.025},
        {"ticker": "LOW", "score": 90, "dividend_yield": 0.01},
        {"ticker": "NIL", "score": 70},   # 누락 → default 0.0
    ]
    out = rerank_for_cohort(rows, "dividend", top_k=10)
    tickers = {r["ticker"] for r in out}
    assert tickers == {"DIV", "MID"}


# ── value — PER<15 AND PBR<1.5 ────────────────────────────────────────

def test_value_filters_per_and_pbr():
    rows = [
        {"ticker": "OK",   "score": 70, "per": 12.0, "pbr": 1.0},
        {"ticker": "HIPER","score": 80, "per": 25.0, "pbr": 1.0},
        {"ticker": "HIPBR","score": 60, "per": 10.0, "pbr": 2.0},
        {"ticker": "NIL",  "score": 50},   # 누락 → default inf, 필터 탈락
    ]
    out = rerank_for_cohort(rows, "value", top_k=10)
    tickers = {r["ticker"] for r in out}
    assert tickers == {"OK"}


# ── growth — score + ret_lag_60d × 10 정렬 ────────────────────────────

def test_growth_boosts_momentum():
    rows = [
        {"ticker": "BIG_SCORE", "score": 90, "ret_lag_60d": 0.0},
        {"ticker": "MOMENTUM",  "score": 70, "ret_lag_60d": 0.05},   # 70 + 0.5 = 70.5
        {"ticker": "SUPER_MO",  "score": 60, "ret_lag_60d": 0.50},   # 60 + 5 = 65
    ]
    out = rerank_for_cohort(rows, "growth", top_k=10)
    # 정렬 키: 90, 70.5, 65 → BIG_SCORE > MOMENTUM > SUPER_MO.
    assert [r["ticker"] for r in out] == ["BIG_SCORE", "MOMENTUM", "SUPER_MO"]


def test_growth_does_not_mutate_input_rows():
    """row 자체에 임시 키를 추가하면 안 됨."""
    rows = [{"ticker": "A", "score": 80, "ret_lag_60d": 0.1}]
    rerank_for_cohort(rows, "growth", top_k=10)
    assert "_growth_boost" not in rows[0]
    assert set(rows[0].keys()) == {"ticker", "score", "ret_lag_60d"}


# ── 비정상 입력 graceful ────────────────────────────────────────────────

def test_handles_nan_and_string_in_numeric_columns():
    """숫자 컬럼에 None·NaN·문자열이 와도 default 로 안전 변환."""
    rows = [
        {"ticker": "OK",  "score": 70, "per": 10, "pbr": 1.0},
        {"ticker": "BAD", "score": 60, "per": "n/a", "pbr": float("nan")},
    ]
    out = rerank_for_cohort(rows, "value", top_k=10)
    # BAD 는 PER/PBR default=inf 라 필터 탈락.
    assert [r["ticker"] for r in out] == ["OK"]


def test_empty_input_returns_empty():
    assert rerank_for_cohort([], "conservative", top_k=10) == []
    assert rerank_for_cohort([], None, top_k=10) == []
