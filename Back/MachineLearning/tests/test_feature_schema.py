"""
test_feature_schema.py
======================
차차기 W4 — feature_schema 의 schema 정합 검증 함수 단위 테스트.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from feature_schema import (
    FEATURE_CATEGORY_V11,
    FEATURE_NAMES_V11,
    Mismatch,
    assert_aligned,
    load_allowlist_json,
    schema_features,
    validate_alignment,
)


# ── schema 자체 ─────────────────────────────────────────────────────────────

def test_schema_has_67_features():
    assert len(FEATURE_NAMES_V11) == 67


def test_schema_all_numeric():
    """현 baseline — 67 모두 numeric."""
    assert all(cat == "numeric" for cat in FEATURE_CATEGORY_V11.values())


def test_schema_no_duplicates():
    assert len(FEATURE_NAMES_V11) == len(set(FEATURE_NAMES_V11))


def test_schema_features_helper():
    """schema_features() 가 list 반환 + allowlist 호환."""
    feats = schema_features()
    assert isinstance(feats, list)
    assert len(feats) == 67
    assert feats == list(FEATURE_NAMES_V11)


# ── validate_alignment ──────────────────────────────────────────────────────

def _df_all_numeric() -> pd.DataFrame:
    """모든 67 features 를 numeric 으로 채운 sample df."""
    rng = np.random.default_rng(0)
    data = {n: rng.random(10).astype(np.float32) for n in FEATURE_NAMES_V11}
    return pd.DataFrame(data)


def test_aligned_no_mismatch():
    df = _df_all_numeric()
    assert validate_alignment(df) == []


def test_int_and_float_both_pass_numeric():
    """카테고리 일치만 검증 — int64 와 float64 둘 다 numeric → 통과."""
    df = _df_all_numeric()
    df["open"] = df["open"].astype(np.int64)   # OHLCV 가 int 일 수도
    assert validate_alignment(df) == []


def test_missing_column_detected():
    df = _df_all_numeric().drop(columns=["RSI_14"])
    out = validate_alignment(df)
    assert len(out) == 1
    assert out[0].column == "RSI_14"
    assert out[0].issue  == "missing"
    assert out[0].actual == "<absent>"


def test_string_in_numeric_slot_detected():
    """numeric 기대 컬럼이 string → wrong_category."""
    df = _df_all_numeric()
    df["close"] = ["foo"] * 10
    out = validate_alignment(df)
    assert len(out) == 1
    assert out[0].column   == "close"
    assert out[0].issue    == "wrong_category"
    assert out[0].expected == "numeric"


def test_multiple_mismatches_listed():
    df = _df_all_numeric().drop(columns=["RSI_14", "MACD"])
    df["close"] = ["x"] * 10
    out = validate_alignment(df)
    assert len(out) == 3
    issues = sorted(m.issue for m in out)
    assert issues == ["missing", "missing", "wrong_category"]


def test_required_subset():
    """required 인자로 일부만 검증."""
    df = _df_all_numeric().drop(columns=["RSI_14"])
    # RSI_14 필수 아님 → 통과
    out = validate_alignment(df, required=["close", "open"])
    assert out == []


# ── assert_aligned ──────────────────────────────────────────────────────────

def test_assert_aligned_ok_when_match():
    df = _df_all_numeric()
    assert_aligned(df, where="test")    # raise X


def test_assert_aligned_raises_with_message():
    df = _df_all_numeric().drop(columns=["RSI_14"])
    with pytest.raises(ValueError) as exc:
        assert_aligned(df, where="train_cache")
    msg = str(exc.value)
    assert "train_cache" in msg
    assert "RSI_14" in msg
    assert "missing" in msg


# ── Mismatch dataclass ──────────────────────────────────────────────────────

def test_mismatch_str_format():
    m = Mismatch(column="x", issue="missing", expected="numeric", actual="<absent>")
    assert "x" in str(m) and "missing" in str(m) and "numeric" in str(m)


# ── allowlist JSON 호환 ────────────────────────────────────────────────────

def test_load_allowlist_json_ok(tmp_path):
    import json as _json
    p = tmp_path / "alist.json"
    p.write_text(_json.dumps(["a", "b", "c"]), encoding="utf-8")
    assert load_allowlist_json(p) == ["a", "b", "c"]


def test_load_allowlist_rejects_non_list(tmp_path):
    import json as _json
    p = tmp_path / "alist.json"
    p.write_text(_json.dumps({"x": 1}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_allowlist_json(p)


def test_schema_matches_real_allowlist():
    """schema 가 v11a_prime_allowlist.json 과 정확히 일치 — single source of truth."""
    repo_root = Path(__file__).resolve().parents[1]
    allowlist = load_allowlist_json(repo_root / "v11a_prime_allowlist.json")
    assert allowlist == list(FEATURE_NAMES_V11)


# ── 차차기 W5D — DART schema ───────────────────────────────────────────────

def test_dart_schema_has_6_features():
    from feature_schema import FEATURE_NAMES_V11_DART
    assert len(FEATURE_NAMES_V11_DART) == 6


def test_dart_schema_all_numeric():
    from feature_schema import FEATURE_CATEGORY_V11_DART
    assert all(cat == "numeric" for cat in FEATURE_CATEGORY_V11_DART.values())


def test_dart_schema_matches_dart_features_module():
    """W5D 핵심 — schema 와 dart_features.feature_column_names() 가 *정확히 일치*."""
    from feature_schema import FEATURE_NAMES_V11_DART
    from dart_features import feature_column_names
    assert list(FEATURE_NAMES_V11_DART) == feature_column_names()


def test_full_schema_is_base_plus_dart():
    from feature_schema import (
        FEATURE_NAMES_V11, FEATURE_NAMES_V11_DART, FEATURE_NAMES_V11_FULL,
    )
    assert len(FEATURE_NAMES_V11_FULL) == 73
    assert FEATURE_NAMES_V11_FULL == FEATURE_NAMES_V11 + FEATURE_NAMES_V11_DART


def test_full_schema_no_overlap():
    from feature_schema import FEATURE_NAMES_V11, FEATURE_NAMES_V11_DART
    assert not (set(FEATURE_NAMES_V11) & set(FEATURE_NAMES_V11_DART))
