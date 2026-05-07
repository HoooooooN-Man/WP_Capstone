"""
test_train_lambdarank_v11.py
============================
W5A — train_lambdarank_v11 의 *순수 함수* 단위 테스트.
DuckDB·PG·LightGBM 의존 없는 함수만 검증.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from train_lambdarank_v11 import (
    META_COLS,
    N_RELEVANCE_BINS,
    bin_relevance_per_group,
    select_feature_cols,
)


# ── bin_relevance_per_group ─────────────────────────────────────────────────

def test_bin_relevance_assigns_per_group_independently():
    """그룹별 *상대 순위* — 절대값 의존 X."""
    df = pd.DataFrame({
        "date":  pd.to_datetime(["2025-01-02"] * 4 + ["2025-01-03"] * 3),
        "label": [0.10, 0.05, 0.20, -0.01, 100.0, 50.0, 0.0],
    })
    rel = bin_relevance_per_group(df, n_bins=4)
    # group 1 (4 elements): -0.01 < 0.05 < 0.10 < 0.20 → ranks 1/2/3/4
    g1 = rel[:4]
    assert g1[3] == g1[g1.argmin()], "최저 라벨이 최저 relevance"
    assert g1[2] == g1[g1.argmax()], "최고 라벨이 최고 relevance"
    # group 2 (3 elements): 100, 50, 0 → 그룹 안에서 다시 binning
    g2 = rel[4:]
    assert g2[0] == g2.max(), "100 이 그룹2 최고"
    assert g2[2] == g2.min(), "0 이 그룹2 최저"


def test_bin_relevance_within_bin_range():
    df = pd.DataFrame({
        "date":  pd.to_datetime(["2025-01-02"] * 50),
        "label": np.random.default_rng(0).normal(size=50),
    })
    rel = bin_relevance_per_group(df, n_bins=N_RELEVANCE_BINS)
    assert rel.min() >= 0
    assert rel.max() <= N_RELEVANCE_BINS - 1


def test_bin_relevance_singleton_group():
    """그룹 크기 1 — 0 으로 처리."""
    df = pd.DataFrame({
        "date":  pd.to_datetime(["2025-01-02"]),
        "label": [0.5],
    })
    rel = bin_relevance_per_group(df, n_bins=4)
    assert rel.tolist() == [0]


# ── select_feature_cols ────────────────────────────────────────────────────

def test_select_feature_excludes_meta():
    df = pd.DataFrame({
        "ticker":  ["005930"],
        "date":    pd.to_datetime(["2025-01-02"]),
        "sector":  ["IT"],
        "exchange": ["KOSPI"],
        "label":   [0.5],
        "fwd_return_20d": [0.05],
        "close":   [70000.0],
        "RSI_14":  [55.5],
    })
    cols = select_feature_cols(df)
    assert "close"  in cols
    assert "RSI_14" in cols
    for meta in ["ticker", "date", "sector", "exchange", "label", "fwd_return_20d"]:
        assert meta not in cols


def test_select_feature_excludes_non_numeric():
    df = pd.DataFrame({
        "RSI_14":   [55.0, 60.0],
        "category": ["A", "B"],
    })
    cols = select_feature_cols(df)
    assert "RSI_14" in cols
    assert "category" not in cols


def test_select_feature_extra_cols_force_included():
    """임베딩 컬럼이 비-숫자 dtype 으로 추론될 가능성 대비 — extra_cols 로 강제 포함 가능."""
    df = pd.DataFrame({
        "RSI_14":  [55.0],
        "emb_00":  [0.1],
    })
    cols = select_feature_cols(df, extra_cols=["emb_00"])
    assert "emb_00" in cols


# ── META_COLS sanity ───────────────────────────────────────────────────────

def test_meta_cols_includes_all_label_columns():
    """fwd_return·alpha·sharpe 라벨이 META 에 포함돼 feature 로 새지 않음."""
    for c in ["fwd_return_5d", "fwd_return_20d", "fwd_return_60d",
              "alpha_5d", "alpha_20d", "alpha_60d", "sharpe_20d"]:
        assert c in META_COLS, f"{c} 가 META_COLS 에서 누락"
