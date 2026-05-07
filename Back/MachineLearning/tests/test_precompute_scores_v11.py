"""
test_precompute_scores_v11.py
=============================
W7B Step 2 — score_and_tier 순수 함수 단위 테스트.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from precompute_scores_v11 import score_and_tier


def test_score_top_is_100_bottom_is_0():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-02"] * 5),
        "raw_score": [10.0, 5.0, 1.0, -2.0, -10.0],
    })
    out = score_and_tier(df.copy(), raw_col="raw_score")
    assert out["score"].max() == 100.0
    assert out["score"].min() == 0.0


def test_tier_thresholds_match_v9():
    """tier: D <40, C [40,60), B [60,80), A 80+."""
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-02"] * 5),
        # rank 1~5 → score 100, 75, 50, 25, 0
        "raw_score": [5.0, 4.0, 3.0, 2.0, 1.0],
    })
    out = score_and_tier(df.copy(), raw_col="raw_score").sort_values("raw_score", ascending=False).reset_index(drop=True)
    assert out.loc[0, "tier"] == "A"  # 100
    assert out.loc[1, "tier"] == "B"  # 75
    assert out.loc[2, "tier"] == "C"  # 50
    assert out.loc[3, "tier"] == "D"  # 25
    assert out.loc[4, "tier"] == "D"  # 0


def test_rank_independent_per_date():
    """그룹별 rank — date 별로 독립 백분위."""
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-02", "2026-01-02", "2026-01-03", "2026-01-03"]),
        "raw_score": [5.0, 1.0, 100.0, 50.0],
    })
    out = score_and_tier(df.copy(), raw_col="raw_score")
    g1 = out[out["date"] == pd.Timestamp("2026-01-02")]
    g2 = out[out["date"] == pd.Timestamp("2026-01-03")]
    # 각 그룹: 1등 100, 2등 0 (size=2 인 경우 pct = (1-1)/(1) = 0 → 100, (2-1)/1=1 → 0)
    assert g1["score"].max() == 100.0 and g1["score"].min() == 0.0
    assert g2["score"].max() == 100.0 and g2["score"].min() == 0.0


def test_singleton_group():
    """그룹 size 1 — score 100 (clip)."""
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-02"]),
        "raw_score": [3.14],
    })
    out = score_and_tier(df.copy(), raw_col="raw_score")
    assert out["score"].iloc[0] == 100.0
    assert out["tier"].iloc[0]  == "A"


def test_total_in_date_correct():
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-02"] * 3 + ["2026-01-03"] * 2),
        "raw_score": [1.0, 2.0, 3.0, 1.0, 2.0],
    })
    out = score_and_tier(df.copy(), raw_col="raw_score")
    assert (out[out["date"] == pd.Timestamp("2026-01-02")]["total_in_date"] == 3).all()
    assert (out[out["date"] == pd.Timestamp("2026-01-03")]["total_in_date"] == 2).all()
