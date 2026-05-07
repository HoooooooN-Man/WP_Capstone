"""
test_coverage.py
================
W8 축소 — services/coverage 의 *순수 함수* 단위 테스트.
"""

from __future__ import annotations

from Back.FastAPI.services.coverage import (
    DEFAULT_MIN_DAYS,
    coverage_status,
    filter_insufficient_coverage,
)


# ── coverage_status ────────────────────────────────────────────────────────

def test_status_ok_at_threshold():
    assert coverage_status(60) == "ok"
    assert coverage_status(61) == "ok"


def test_status_insufficient_below_threshold():
    assert coverage_status(0)  == "insufficient_data"
    assert coverage_status(59) == "insufficient_data"


def test_status_custom_threshold():
    assert coverage_status(30, min_days=30) == "ok"
    assert coverage_status(29, min_days=30) == "insufficient_data"


def test_default_min_days_is_60():
    assert DEFAULT_MIN_DAYS == 60


# ── filter_insufficient_coverage ───────────────────────────────────────────

def test_filter_keeps_only_sufficient():
    rows = [
        {"ticker": "A", "score": 95},   # 1000일
        {"ticker": "B", "score": 80},   # 30일 → 제외
        {"ticker": "C", "score": 60},   # 60일 (경계)
    ]
    days = {"A": 1000, "B": 30, "C": 60}
    kept, excluded = filter_insufficient_coverage(rows, days)
    assert [r["ticker"] for r in kept] == ["A", "C"]
    assert excluded == 1


def test_filter_excludes_unknown_ticker():
    """ticker_days 에 없는 종목은 *데이터 부재* — 제외 (안전 우선)."""
    rows = [{"ticker": "A", "score": 1}, {"ticker": "X", "score": 2}]
    days = {"A": 1000}
    kept, excluded = filter_insufficient_coverage(rows, days)
    assert [r["ticker"] for r in kept] == ["A"]
    assert excluded == 1


def test_filter_empty_input():
    kept, excluded = filter_insufficient_coverage([], {})
    assert kept == [] and excluded == 0


def test_filter_excludes_row_without_ticker():
    rows = [{"score": 1.0}, {"ticker": "A", "score": 2.0}]
    days = {"A": 1000}
    kept, excluded = filter_insufficient_coverage(rows, days)
    assert [r["ticker"] for r in kept] == ["A"]
    assert excluded == 1


def test_filter_custom_min_days():
    rows = [{"ticker": "A"}, {"ticker": "B"}]
    days = {"A": 100, "B": 50}
    kept, excluded = filter_insufficient_coverage(rows, days, min_days=80)
    assert [r["ticker"] for r in kept] == ["A"]
    assert excluded == 1


def test_filter_preserves_order():
    rows = [{"ticker": t} for t in ["C", "A", "B"]]
    days = {"A": 1000, "B": 1000, "C": 1000}
    kept, _ = filter_insufficient_coverage(rows, days)
    assert [r["ticker"] for r in kept] == ["C", "A", "B"]
