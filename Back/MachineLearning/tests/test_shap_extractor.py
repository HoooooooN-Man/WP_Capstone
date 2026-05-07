"""
test_shap_extractor.py
======================
Tier 1.3 (PRD §4.4) — SHAP 추출기·자연어 변환 단위 테스트.

I/O 의존성을 갖는 compute_shap.py 본체는 별도 통합 시나리오로 검증하고,
본 파일은 순수 함수 부분만 검증한다 (CI 환경에서도 통과 보장).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Back/MachineLearning import 경로.
_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from shap_extractor import (  # noqa: E402
    deserialize_top_factors,
    describe_factor,
    extract_top_factors,
    extract_top_factors_batch,
    load_descriptions,
    serialize_top_factors,
)


# ── 자연어 매핑 ─────────────────────────────────────────────────────────────

def test_descriptions_yaml_loads():
    descs = load_descriptions()
    assert isinstance(descs, dict)
    assert len(descs) >= 20
    # 핵심 피처 몇 개가 들어 있는지.
    assert "외국인_거래대금" in descs or "ROE" in descs
    assert "VIX" in descs


def test_describe_factor_uses_orig_korean_when_available():
    # safe → orig 역매핑이 있으면 한글 키로 lookup 한다.
    inv_map = {"feat_safe": "외국인_거래대금"}
    descs = load_descriptions()
    out = describe_factor("feat_safe", contribution=0.05,
                          descriptions=descs, col_name_map_inv=inv_map)
    assert out["feature"] == "외국인_거래대금"
    assert out["direction"] == "positive"
    assert "외국인" in out["display"]
    assert "외국인" in out["label"]


def test_describe_factor_negative_uses_negative_template():
    descs = load_descriptions()
    out = describe_factor("VIX", contribution=-0.03, descriptions=descs)
    assert out["direction"] == "negative"
    # negative 템플릿이 적용되어 부정 의미가 들어가야 함.
    assert any(w in out["label"] for w in ("부정", "부담", "약", "둔화"))


def test_describe_factor_falls_back_to_safe_name_when_unmapped():
    out = describe_factor("totally_unknown_feature", contribution=0.1,
                          descriptions={}, col_name_map_inv={})
    assert out["feature"] == "totally_unknown_feature"
    assert out["display"] == "totally_unknown_feature"
    # fallback 템플릿이 한국어로 채워졌는지.
    assert "기여" in out["label"]


# ── 추출기 ──────────────────────────────────────────────────────────────────

def test_extract_top_factors_picks_largest_absolute_values():
    # 5 features + bias.
    feature_names = ["a", "b", "c", "d", "e"]
    row = np.array([0.01, -0.5, 0.2, -0.3, 0.05, 0.0])  # 마지막은 bias
    out = extract_top_factors(row, feature_names, top_k=3,
                              descriptions={}, col_name_map_inv={})
    assert len(out) == 3
    # 절대값 순서: b(-0.5) > d(-0.3) > c(0.2).
    assert [f["feature"] for f in out] == ["b", "d", "c"]
    assert out[0]["direction"] == "negative"
    assert out[1]["direction"] == "negative"
    assert out[2]["direction"] == "positive"


def test_extract_top_factors_filters_below_min_abs():
    feature_names = ["a", "b", "c"]
    row = np.array([0.0, 1e-9, 1e-9, 0.0])  # 모두 잡음 수준
    out = extract_top_factors(row, feature_names, top_k=3, min_abs=1e-6,
                              descriptions={}, col_name_map_inv={})
    assert out == []


def test_extract_top_factors_validates_shape():
    feature_names = ["a", "b"]
    bad_row = np.array([0.1, 0.2])  # bias 누락
    with pytest.raises(ValueError, match="n_features"):
        extract_top_factors(bad_row, feature_names, top_k=2)


def test_batch_returns_one_per_row():
    feature_names = ["a", "b", "c"]
    contribs = np.array([
        [0.5, -0.1, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],     # 모두 0 → 빈 리스트
        [0.0, 0.4, -0.2, 0.0],
    ])
    out = extract_top_factors_batch(contribs, feature_names, top_k=3,
                                    descriptions={}, col_name_map_inv={})
    assert len(out) == 3
    assert len(out[0]) >= 1 and out[0][0]["feature"] == "a"
    assert out[1] == []
    assert out[2][0]["feature"] == "b"


# ── 직렬화 ─────────────────────────────────────────────────────────────────

def test_serialize_then_deserialize_roundtrip_korean():
    factors = [
        {"feature": "외국인_거래대금", "contribution": 0.05,
         "direction": "positive", "label": "외국인 5일 순매수 양호",
         "display": "외국인 순매수 (5일)"},
    ]
    s = serialize_top_factors(factors)
    # JSON 에 한글이 그대로 보존되어야 한다 (ensure_ascii=False).
    assert "외국인" in s
    out = deserialize_top_factors(s)
    assert out == factors


def test_deserialize_handles_none_and_garbage():
    assert deserialize_top_factors(None) == []
    assert deserialize_top_factors("") == []
    assert deserialize_top_factors("not json") == []
