"""
test_eval_harness.py
====================
Tier 1.2 — 평가 하네스 단위 테스트.

DuckDB 의존 (data_loader) 은 통합 시연으로 별도 검증하고, 본 파일은
순수 함수 (slicers, metrics, reports) 만 단위 테스트.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from eval_harness.metrics import compute_metric_bundle
from eval_harness.reports import build_json, render_html
from eval_harness.slices  import (
    slice_by_cap_quartile,
    slice_by_regime,
    slice_by_sector,
    slice_by_time,
)


# ── 픽스처 ─────────────────────────────────────────────────────────────────

def _make_rows(n: int = 500) -> pd.DataFrame:
    """label·prob 가 약하게 calibrated 된 가짜 평가 데이터."""
    rng = np.random.default_rng(42)
    prob = rng.beta(2, 5, n)                    # 0.0~1.0 분포
    label = (rng.random(n) < prob).astype(int)
    sectors = rng.choice(["IT", "금융", "헬스케어"], size=n, p=[0.5, 0.3, 0.2])
    caps    = rng.choice(["Q1_small", "Q2", "Q3", "Q4_large"], size=n)
    years   = rng.choice(["2025", "2026"], size=n)
    regimes = rng.choice(["Up", "Down"], size=n, p=[0.6, 0.4])
    return pd.DataFrame({
        "date_int":     rng.integers(20260101, 20260430, n),
        "ticker":       [f"00{i:04d}" for i in range(n)],
        "label":        label,
        "prob":         prob,
        "sector":       sectors,
        "cap_quartile": caps,
        "year":         years,
        "regime":       regimes,
        "tier":         np.where(prob > 0.7, "A", "B"),
        "fwd_return":   prob - 0.3,             # prob 와 약하게 양의 상관.
    })


def _make_periods(n: int = 8) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame({
        "date_int":     20260101 + np.arange(n) * 20,
        "n_picks":      np.full(n, 100),
        "strat_return": rng.normal(0.02, 0.03, n),
        "bench_return": rng.normal(0.015, 0.02, n),
        "alpha":        rng.normal(0.005, 0.025, n),
    })


# ── 슬라이서 ──────────────────────────────────────────────────────────────

def test_time_slicer_groups_by_year():
    rows = _make_rows(500)
    out = slice_by_time(rows, pd.DataFrame(), min_count=50)
    assert all(s.dimension == "time" for s in out)
    assert {s.key for s in out} == {"2025", "2026"}


def test_sector_slicer_respects_min_count():
    rows = _make_rows(2000)
    out = slice_by_sector(rows, pd.DataFrame(), min_count=300)
    keys = {s.key for s in out}
    # 비율 — IT 1000 · 금융 600 · 헬스케어 400 (모두 통과).
    assert "IT" in keys
    assert "금융" in keys

    # 다음으로 min_count 를 더 빡빡하게 — 헬스케어만 제외.
    out_strict = slice_by_sector(rows, pd.DataFrame(), min_count=500)
    keys_strict = {s.key for s in out_strict}
    assert "헬스케어" not in keys_strict
    assert "IT" in keys_strict


def test_cap_slicer_orders_quartiles():
    rows = _make_rows(800)
    out = slice_by_cap_quartile(rows, pd.DataFrame(), min_count=50)
    keys = [s.key for s in out]
    # 정의된 순서대로.
    expected_order = ["Q1_small", "Q2", "Q3", "Q4_large"]
    assert keys == [k for k in expected_order if k in keys]


def test_regime_slicer_attaches_period_subset_when_possible():
    rows = _make_rows(800)
    periods = _make_periods(8)
    out = slice_by_regime(rows, periods, min_count=100)
    assert {s.key for s in out} <= {"Up", "Down"}
    for s in out:
        # regime 슬라이스는 자체 periods 부분집합을 가짐 (없을 수도 있음).
        assert s.dimension == "regime"


# ── 메트릭 번들 ────────────────────────────────────────────────────────────

def test_metric_bundle_full():
    rows = _make_rows(500)
    periods = _make_periods(8)
    m = compute_metric_bundle(rows, periods)
    d = m.to_dict()
    # 5개 메트릭 + 진단.
    assert d["n_rows"] == 500
    assert d["n_periods"] == 8
    assert d["auc"] is not None
    assert d["ece"] is not None
    assert d["sharpe"] is not None
    assert d["mdd"] is not None
    assert d["alpha_cum"] is not None
    # mdd 는 0 또는 음수.
    assert d["mdd"] <= 0


def test_metric_bundle_handles_single_class():
    rows = _make_rows(100).copy()
    rows["label"] = 0      # 모든 행이 0 → AUC undefined.
    m = compute_metric_bundle(rows, pd.DataFrame())
    d = m.to_dict()
    assert d["auc"] is None
    assert d["sharpe"] is None      # periods 없음.
    assert any("AUC" in n for n in d["notes"])


def test_metric_bundle_handles_no_periods():
    rows = _make_rows(200)
    m = compute_metric_bundle(rows, pd.DataFrame())
    d = m.to_dict()
    assert d["sharpe"] is None
    assert d["mdd"] is None
    assert d["alpha_cum"] is None
    assert d["auc"] is not None     # 분류 메트릭은 산출됨.


# ── 리포트 ─────────────────────────────────────────────────────────────────

def test_build_json_shape():
    overall = compute_metric_bundle(_make_rows(200), _make_periods(5)).to_dict()
    slices  = [{"dimension": "time", "key": "2026", "metrics": overall}]
    out = build_json(model_version="v9", overall=overall, slices=slices)
    assert out["schema_version"] == "1.0"
    assert out["model_version"] == "v9"
    assert "generated_at" in out
    assert out["overall"]["n_rows"] == 200
    assert len(out["slices"]) == 1


def test_render_html_smoke():
    overall = compute_metric_bundle(_make_rows(200), _make_periods(5)).to_dict()
    slices  = [
        {"dimension": "time",     "key": "2026",     "metrics": overall},
        {"dimension": "sector",   "key": "IT",       "metrics": overall},
        {"dimension": "cap_size", "key": "Q1_small", "metrics": overall},
        {"dimension": "regime",   "key": "Up",       "metrics": overall},
    ]
    html = render_html(model_version="v9", overall=overall, slices=slices)
    assert "<!doctype html>" in html
    assert "v9 평가 하네스" in html
    # 4 슬라이스 차원이 모두 섹션 제목으로 노출.
    for label in ("연도별", "섹터별", "시총", "시장 국면"):
        assert label in html
