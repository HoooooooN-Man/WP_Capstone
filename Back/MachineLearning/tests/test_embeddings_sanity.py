"""
test_embeddings_sanity.py
=========================
W3.5E — 4 sanity check 순수 함수 단위 테스트.

각 함수에 *PASS 가 명백한 합성 데이터* 와 *FAIL 이 명백한 데이터* 를 입력해
경계 동작을 검증.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from embeddings.sanity import (
    SanityResult,
    check_chaebol_proximity,
    check_correlation_alignment,
    check_embedding_rank,
    check_sector_proximity,
    run_all_sanity,
)


# ── 합성 데이터 헬퍼 ───────────────────────────────────────────────────────

def _make_sectorial_embeddings(rng, sectors_meta: list[tuple[str, int, np.ndarray, float]]):
    """
    각 섹터 (sector_id, n_tickers, center_vector, jitter) 로 부터 ticker·embedding 생성.
    embedding 은 center 근처에 jitter 만큼 흩뿌려짐.
    """
    embeddings = []
    tickers    = []
    sectors    = {}
    counter = 0
    for sec, n, center, jitter in sectors_meta:
        for _ in range(n):
            v = center + rng.normal(0, jitter, size=center.shape)
            v = v / (np.linalg.norm(v) + 1e-12)
            embeddings.append(v)
            t = f"{counter:06d}"
            tickers.append(t)
            sectors[t] = sec
            counter += 1
    return np.array(embeddings, dtype=np.float32), tickers, sectors


# ── 1) sector_proximity ────────────────────────────────────────────────────

def test_sector_proximity_passes_for_clustered_data():
    """섹터별 center 근처에 모이면 PASS."""
    rng = np.random.default_rng(0)
    centers = [rng.normal(0, 1, size=64) for _ in range(3)]
    centers = [c / np.linalg.norm(c) for c in centers]
    emb, tickers, sectors = _make_sectorial_embeddings(rng, [
        ("IT",      30, centers[0], 0.05),
        ("FINANCE", 30, centers[1], 0.05),
        ("HEALTH",  30, centers[2], 0.05),
    ])
    res = check_sector_proximity(emb, tickers, sectors, rng=rng)
    assert isinstance(res, SanityResult)
    assert res.passed is True
    assert res.detail["sector_avg_distance"] < res.detail["random_avg_distance"]


def test_sector_proximity_fails_for_random_data():
    """섹터 라벨과 임베딩이 무관 → FAIL."""
    rng = np.random.default_rng(1)
    N, D = 60, 64
    emb = rng.normal(size=(N, D)).astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    tickers = [f"{i:06d}" for i in range(N)]
    # 무작위 섹터 라벨.
    sec_choices = ["A", "B", "C"]
    sectors = {t: sec_choices[i % 3] for i, t in enumerate(tickers)}
    res = check_sector_proximity(emb, tickers, sectors, rng=rng)
    # 무관한 데이터에서 sector_avg ≈ random_avg → ratio ≈ 1.0, threshold 0.80 위반.
    assert res.passed is False


def test_sector_proximity_no_pairs_returns_fail():
    rng = np.random.default_rng(2)
    emb = rng.normal(size=(5, 64)).astype(np.float32)
    tickers = [f"{i:06d}" for i in range(5)]
    sectors = {tickers[0]: "X"}      # 섹터 1명 → 쌍 없음
    res = check_sector_proximity(emb, tickers, sectors, rng=rng)
    assert res.passed is False
    assert "no sector pairs" in res.detail["reason"]


# ── 2) correlation_alignment ───────────────────────────────────────────────

def test_correlation_alignment_passes():
    """상관 높은 쌍의 임베딩 거리가 작도록 합성."""
    rng = np.random.default_rng(3)
    N = 20
    # 쌍 (0,1),(2,3),... 가까운 임베딩, 나머지는 멀게.
    emb = rng.normal(size=(N, 32)).astype(np.float32)
    for i in range(0, N, 2):
        emb[i + 1] = emb[i] + 0.05 * rng.normal(size=32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)

    tickers = [f"{i:06d}" for i in range(N)]
    correlation = {}
    for i in range(0, N, 2):
        correlation[(tickers[i], tickers[i + 1])] = 0.85   # 높은 상관
    # 무작위 멀리 있는 쌍 — 낮은 상관.
    for _ in range(20):
        a, b = rng.choice(N, size=2, replace=False)
        if abs(int(a) - int(b)) > 1:
            correlation[(tickers[int(a)], tickers[int(b)])] = float(rng.uniform(0, 0.3))

    res = check_correlation_alignment(emb, tickers, correlation)
    assert res.passed is True
    assert res.detail["high_corr_avg_distance"] < res.detail["low_corr_avg_distance"]


def test_correlation_alignment_fails_when_buckets_empty():
    rng = np.random.default_rng(4)
    emb = rng.normal(size=(5, 16)).astype(np.float32)
    tickers = [f"{i:06d}" for i in range(5)]
    # 모두 중간 상관 → 어느 bucket 도 안 채움.
    correlation = {(tickers[0], tickers[1]): 0.5}
    res = check_correlation_alignment(emb, tickers, correlation)
    assert res.passed is False
    assert "insufficient pairs" in res.detail["reason"]


# ── 3) chaebol_proximity ───────────────────────────────────────────────────

def test_chaebol_proximity_passes_for_grouped_data():
    rng = np.random.default_rng(5)
    centers = [rng.normal(0, 1, size=64) for _ in range(3)]
    centers = [c / np.linalg.norm(c) for c in centers]
    emb, tickers, _ = _make_sectorial_embeddings(rng, [
        ("samsung", 8, centers[0], 0.05),
        ("lg",      8, centers[1], 0.05),
        ("sk",      8, centers[2], 0.05),
    ])
    # 추가로 무작위 비계열사 종목 30개.
    extra = rng.normal(size=(30, 64)).astype(np.float32)
    extra /= np.linalg.norm(extra, axis=1, keepdims=True)
    emb = np.vstack([emb, extra])
    extra_tickers = [f"X{i:05d}" for i in range(30)]
    tickers.extend(extra_tickers)
    groups = {t: ("samsung" if i < 8 else "lg" if i < 16 else "sk")
              for i, t in enumerate(tickers[:24])}
    res = check_chaebol_proximity(emb, tickers, groups, rng=rng)
    assert res.passed is True


def test_chaebol_proximity_no_groups_returns_fail():
    rng = np.random.default_rng(6)
    emb = rng.normal(size=(10, 16)).astype(np.float32)
    tickers = [f"{i:06d}" for i in range(10)]
    res = check_chaebol_proximity(emb, tickers, {}, rng=rng)
    assert res.passed is False
    assert "no group pairs" in res.detail["reason"]


# ── 4) embedding_rank ──────────────────────────────────────────────────────

def test_embedding_rank_passes_full_random():
    """64차원 무작위 가우시안 → effective rank 높음."""
    rng = np.random.default_rng(7)
    emb = rng.normal(size=(200, 64)).astype(np.float32)
    res = check_embedding_rank(emb, rank_threshold=50)
    assert res.passed is True
    assert res.detail["effective_rank"] >= 50


def test_embedding_rank_fails_collapsed():
    """모든 임베딩이 동일 → effective rank 1 → FAIL."""
    emb = np.tile(np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]), (50, 1)).astype(np.float32)
    res = check_embedding_rank(emb, rank_threshold=4)
    assert res.passed is False
    assert res.detail["reason"] == "zero variance"


def test_embedding_rank_fails_low_rank_subspace():
    """5차원 부분공간으로 압축된 64차원 임베딩 → effective rank ~5 → FAIL @ threshold 50."""
    rng = np.random.default_rng(8)
    base = rng.normal(size=(100, 5))
    proj = rng.normal(size=(5, 64))
    emb = (base @ proj).astype(np.float32)
    res = check_embedding_rank(emb, rank_threshold=50)
    assert res.passed is False
    assert res.detail["effective_rank"] < 50


def test_embedding_rank_too_small_input():
    res = check_embedding_rank(np.zeros((1, 64), dtype=np.float32))
    assert res.passed is False


# ── run_all_sanity 종합 ────────────────────────────────────────────────────

def test_run_all_sanity_with_partial_inputs():
    """sectors 만 주어진 경우 — sector + rank 두 검사만 실행."""
    rng = np.random.default_rng(9)
    centers = [rng.normal(0, 1, size=64) for _ in range(2)]
    centers = [c / np.linalg.norm(c) for c in centers]
    emb, tickers, sectors = _make_sectorial_embeddings(rng, [
        ("A", 20, centers[0], 0.05),
        ("B", 20, centers[1], 0.05),
    ])
    out = run_all_sanity(
        embeddings=emb, tickers=tickers,
        sectors=sectors,
        correlation=None, groups=None,
    )
    assert out["n_checks_run"] == 2     # sector + rank
    assert out["pass_threshold"] == 2
    assert out["overall_pass"] is (out["n_passed"] >= 2)


def test_run_all_sanity_records_check_names():
    rng = np.random.default_rng(10)
    emb = rng.normal(size=(30, 16)).astype(np.float32)
    out = run_all_sanity(
        embeddings=emb,
        tickers=[f"{i:06d}" for i in range(30)],
    )
    names = [c["name"] for c in out["checks"]]
    assert names == ["embedding_rank"]
