"""
test_diversify.py
=================
W3 — services/diversify 의 *순수 함수* (MMR + sector·constant sim) 단위 테스트.
correlation·embedding sim 은 DB·PG 의존이라 별도 통합 테스트.
"""

from __future__ import annotations

import pytest

from Back.FastAPI.services.diversify import (
    DEFAULT_LAMBDA,
    VALID_DIVERSIFY,
    make_sector_sim,
    mmr_rerank,
    normalize_diversify,
)


# ── normalize_diversify ────────────────────────────────────────────────────

@pytest.mark.parametrize("inp,exp", [
    (None,            "none"),
    ("",              "none"),
    (" ",             "none"),
    ("none",          "none"),
    ("Correlation",   "correlation"),
    ("EMBEDDING",     "embedding"),
    ("sector",        "sector"),
    ("balanced",      "none"),     # 알 수 없는 모드 → none (fail-soft)
])
def test_normalize_diversify(inp, exp):
    assert normalize_diversify(inp) == exp


def test_default_lambda_in_unit_range():
    assert 0.0 <= DEFAULT_LAMBDA <= 1.0


# ── mmr_rerank ─────────────────────────────────────────────────────────────

def test_lambda_1_equals_pure_score_order():
    """λ=1 — diversity penalty 0, score 내림차순."""
    rows = [
        {"ticker": "A", "score": 95.0},
        {"ticker": "B", "score": 80.0},
        {"ticker": "C", "score": 60.0},
        {"ticker": "D", "score": 40.0},
    ]
    out = mmr_rerank(rows, sim=lambda a, b: 0.0, lambda_=1.0, top_k=4)
    assert [r["ticker"] for r in out] == ["A", "B", "C", "D"]


def test_diversity_breaks_pure_score_order():
    """λ=0.3 — A·B 가 거리 0 이고 C 가 멀면 C 가 2nd 선택."""
    def sim(a, b):
        # A↔B 같은 클러스터 (거리 0), 나머지 거리 1.
        cluster = {"A", "B"}
        if a == b:
            return 0.0
        if {a, b} == cluster:
            return 0.0
        return 1.0
    rows = [
        {"ticker": "A", "score": 100.0},
        {"ticker": "B", "score": 99.0},
        {"ticker": "C", "score": 50.0},
        {"ticker": "D", "score": 0.0},
    ]
    out = mmr_rerank(rows, sim=sim, lambda_=0.3, top_k=2)
    # 첫 = A. 두 번째: B 는 A 와 거리 0, C 는 거리 1. λ=0.3 이라 다양성 가중.
    # value(B) = 0.3 * 0.99 + 0.7 * 0 = 0.297
    # value(C) = 0.3 * 0.5  + 0.7 * 1 = 0.85
    assert [r["ticker"] for r in out] == ["A", "C"]


def test_top_k_zero_returns_all():
    rows = [{"ticker": "A", "score": 1.0}, {"ticker": "B", "score": 2.0}]
    out = mmr_rerank(rows, sim=lambda a, b: 0.0, top_k=0)
    assert len(out) == len(rows)


def test_single_row_passthrough():
    rows = [{"ticker": "A", "score": 50.0}]
    out = mmr_rerank(rows, sim=lambda a, b: 0.0, top_k=10)
    assert out == rows


def test_lambda_out_of_range_raises():
    rows = [{"ticker": "A", "score": 1.0}, {"ticker": "B", "score": 2.0}]
    with pytest.raises(ValueError):
        mmr_rerank(rows, sim=lambda a, b: 0.0, lambda_=1.5, top_k=2)


def test_first_pick_is_top_score():
    rows = [
        {"ticker": "X", "score": 30.0},
        {"ticker": "Y", "score": 95.0},
        {"ticker": "Z", "score": 60.0},
    ]
    out = mmr_rerank(rows, sim=lambda a, b: 0.5, lambda_=0.5, top_k=1)
    assert out[0]["ticker"] == "Y"


def test_constant_score_returns_top_k_in_order():
    """모든 score 동일 → norm_scores=0 → diversity 만 효과."""
    rows = [{"ticker": t, "score": 50.0} for t in ["A", "B", "C", "D"]]
    out = mmr_rerank(rows, sim=lambda a, b: 1.0, lambda_=0.5, top_k=3)
    assert len(out) == 3


# ── sector sim ─────────────────────────────────────────────────────────────

def test_sector_sim_same_sector_zero():
    rows = [
        {"ticker": "A", "sector": "IT"},
        {"ticker": "B", "sector": "IT"},
        {"ticker": "C", "sector": "Bio"},
    ]
    sim = make_sector_sim(rows)
    assert sim("A", "B") == 0.0
    assert sim("A", "C") == 1.0
    assert sim("B", "C") == 1.0


def test_sector_sim_missing_returns_one():
    rows = [
        {"ticker": "A", "sector": "IT"},
        {"ticker": "B", "sector": None},
    ]
    sim = make_sector_sim(rows)
    assert sim("A", "B") == 1.0       # missing → 다양성 보상
    assert sim("A", "Z") == 1.0       # 모르는 ticker — 다양성 보상


def test_sector_diversify_picks_across_sectors():
    """sector sim + λ 낮음 → 같은 섹터 연속 선택 회피."""
    rows = [
        {"ticker": "I1", "score": 100.0, "sector": "IT"},
        {"ticker": "I2", "score":  95.0, "sector": "IT"},
        {"ticker": "B1", "score":  80.0, "sector": "Bio"},
        {"ticker": "F1", "score":  70.0, "sector": "Finance"},
    ]
    sim = make_sector_sim(rows)
    out = mmr_rerank(rows, sim=sim, lambda_=0.3, top_k=3)
    # 첫 = I1 (top score). 다음 = I2 (95) 거리 0  vs B1 (80) 거리 1.
    # value(I2) = 0.3 * (95-70)/30 + 0.7 * 0  ≈ 0.25
    # value(B1) = 0.3 * (80-70)/30 + 0.7 * 1  ≈ 0.80
    # → B1.
    assert out[0]["ticker"] == "I1"
    assert out[1]["ticker"] == "B1"


# ── VALID_DIVERSIFY ────────────────────────────────────────────────────────

def test_valid_diversify_set_complete():
    assert VALID_DIVERSIFY == {"none", "sector", "correlation", "embedding"}
