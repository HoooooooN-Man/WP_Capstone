"""
test_dart_features.py
=====================
차차기 W5C — dart_features 의 *순수 함수* 단위 테스트.
DuckDB·HTTP 의존 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dart_features import (
    CATEGORY_TO_DETAIL_TY,
    DEFAULT_LOOKBACK_DAYS,
    build_features_for_ticker,
    build_features_table,
    feature_column_names,
)


# ── CATEGORY 매핑 ──────────────────────────────────────────────────────────

def test_categories_complete():
    assert "buyback" in CATEGORY_TO_DETAIL_TY
    assert "capital_increase" in CATEGORY_TO_DETAIL_TY
    assert "earnings_report" in CATEGORY_TO_DETAIL_TY
    assert CATEGORY_TO_DETAIL_TY["buyback"]          == ("E001", "E002")
    assert CATEGORY_TO_DETAIL_TY["capital_increase"] == ("C001",)
    assert CATEGORY_TO_DETAIL_TY["earnings_report"]  == ("A001", "A002", "A003")


def test_default_lookback_30():
    assert DEFAULT_LOOKBACK_DAYS == 30


def test_feature_column_names_format():
    cols = feature_column_names()
    assert "dart_buyback_30d_count"           in cols
    assert "dart_buyback_30d_binary"          in cols
    assert "dart_capital_increase_30d_count"  in cols
    assert "dart_earnings_report_30d_binary"  in cols
    assert len(cols) == 6   # 3 categories × 2 (count + binary)


# ── build_features_for_ticker — 빈 입력 ─────────────────────────────────

def test_empty_disclosures_returns_zero_features():
    target = pd.Series(["2026-04-29", "2026-04-30"])
    feats = build_features_for_ticker(pd.DataFrame(), target)
    assert len(feats) == 2
    for col in feature_column_names():
        assert (feats[col] == 0).all()


# ── build_features_for_ticker — 정상 ──────────────────────────────────────

def _disc(rcept_dt, detail_ty):
    return {"rcept_dt": rcept_dt, "pblntf_detail_ty": detail_ty}


def test_buyback_count_in_window():
    """E001 / E002 가 lookback 안 → buyback count 누적."""
    disc = pd.DataFrame([
        _disc("20260415", "E001"),  # 14일 전
        _disc("20260420", "E002"),  # 9일 전
        _disc("20260301", "E001"),  # 59일 전 — 30일 window 밖
    ])
    target = pd.Series(["2026-04-29"])
    feats = build_features_for_ticker(disc, target)
    assert feats.loc[0, "dart_buyback_30d_count"]  == 2
    assert feats.loc[0, "dart_buyback_30d_binary"] == 1


def test_categories_independent():
    """카테고리 별 카운트 독립."""
    disc = pd.DataFrame([
        _disc("20260420", "E001"),  # buyback
        _disc("20260425", "C001"),  # capital_increase
        _disc("20260428", "A003"),  # earnings (Q)
    ])
    target = pd.Series(["2026-04-29"])
    feats = build_features_for_ticker(disc, target)
    assert feats.loc[0, "dart_buyback_30d_count"]          == 1
    assert feats.loc[0, "dart_capital_increase_30d_count"] == 1
    assert feats.loc[0, "dart_earnings_report_30d_count"]  == 1
    for cat in ("buyback", "capital_increase", "earnings_report"):
        assert feats.loc[0, f"dart_{cat}_30d_binary"] == 1


def test_unknown_detail_ty_ignored():
    """매핑 안 된 detail_ty 는 features 에 영향 X."""
    disc = pd.DataFrame([
        _disc("20260420", "B001"),   # 매핑 없음
        _disc("20260420", "E001"),   # buyback
    ])
    target = pd.Series(["2026-04-29"])
    feats = build_features_for_ticker(disc, target)
    assert feats.loc[0, "dart_buyback_30d_count"] == 1
    # B001 은 어디에도 안 잡힘.


def test_lookback_window_strict_upper_bound():
    """target d 의 lookback = (d - L, d]. d 자체는 *포함*."""
    disc = pd.DataFrame([
        _disc("20260429", "E001"),   # target d 와 동일
    ])
    target = pd.Series(["2026-04-29"])
    feats = build_features_for_ticker(disc, target, lookback_days=30)
    assert feats.loc[0, "dart_buyback_30d_count"] == 1


def test_lookback_window_excludes_too_old():
    """L+1 일 전은 제외."""
    disc = pd.DataFrame([
        _disc("20260330", "E001"),   # 30일 전 — 정확히 경계 (d - L 와 동일 → 제외)
    ])
    target = pd.Series(["2026-04-29"])
    feats = build_features_for_ticker(disc, target, lookback_days=30)
    # 2026-04-29 - 30d = 2026-03-30. window 정의 (start, end] → start 와 같으면 제외.
    assert feats.loc[0, "dart_buyback_30d_count"] == 0


def test_invalid_rcept_dt_dropped():
    """파싱 안 되는 rcept_dt 는 graceful drop."""
    disc = pd.DataFrame([
        _disc("invalid", "E001"),
        _disc("20260420", "E001"),
    ])
    target = pd.Series(["2026-04-29"])
    feats = build_features_for_ticker(disc, target)
    assert feats.loc[0, "dart_buyback_30d_count"] == 1


def test_multiple_target_dates():
    """target d 가 여러 개 — 각 d 마다 독립 window."""
    disc = pd.DataFrame([
        _disc("20260420", "E001"),
    ])
    target = pd.Series(["2026-04-22", "2026-05-25"])
    feats = build_features_for_ticker(disc, target, lookback_days=30)
    # d=04-22: 04-20 가 window 안 → count 1
    # d=05-25: 04-20 는 35일 전 → window 밖 → count 0
    assert feats.loc[0, "dart_buyback_30d_count"] == 1
    assert feats.loc[1, "dart_buyback_30d_count"] == 0


# ── build_features_table ────────────────────────────────────────────────────

def test_table_per_ticker_independence():
    """ticker A 의 disclosures 가 ticker B 의 features 에 영향 X."""
    disc = pd.DataFrame([
        {"stock_code": "005930", "rcept_dt": "20260420", "pblntf_detail_ty": "E001"},
        {"stock_code": "066570", "rcept_dt": "20260425", "pblntf_detail_ty": "A003"},
    ])
    target = pd.DataFrame([
        {"ticker": "005930", "date": "2026-04-29"},
        {"ticker": "066570", "date": "2026-04-29"},
        {"ticker": "035420", "date": "2026-04-29"},
    ])
    out = build_features_table(disc, target)
    assert len(out) == 3
    # 005930 — buyback 1
    s = out[out["ticker"] == "005930"].iloc[0]
    assert s["dart_buyback_30d_count"] == 1
    assert s["dart_earnings_report_30d_count"] == 0
    # 066570 — earnings 1
    s = out[out["ticker"] == "066570"].iloc[0]
    assert s["dart_buyback_30d_count"] == 0
    assert s["dart_earnings_report_30d_count"] == 1
    # 035420 — 공시 없음
    s = out[out["ticker"] == "035420"].iloc[0]
    assert s["dart_buyback_30d_count"] == 0
    assert s["dart_earnings_report_30d_count"] == 0


def test_table_empty_target_returns_empty_with_schema():
    out = build_features_table(pd.DataFrame(), pd.DataFrame(columns=["ticker", "date"]))
    expected_cols = ["ticker", "date"] + feature_column_names()
    assert list(out.columns) == expected_cols
    assert len(out) == 0
