"""
feature_schema.py
=================
차차기 W4 — v11 모델의 67 features 학습-운영 schema 정합 검증.

배경:
  차기 W7A 후행 발견: 51 supply features (foreign·short·investor amounts) 가
  학습 noise 였음. 67 holdout-호환 features 가 v11a_prime baseline 의 standard.
  v11a_prime_allowlist.json (단순 list) 을 *데이터구조 + 검증 함수* 로 격상.

설계:
  - FEATURE_SCHEMA_V11: 67 features 명시 (name + category).
    category="numeric": int·float 모두 허용 (LightGBM 자동 캐스팅).
    category="categorical": string. 현재 v11 은 numeric 전용.
  - validate_alignment(df) → list[Mismatch]: 누락·dtype 카테고리 불일치 탐지.
  - 학습·추론 진입점에서 호출 → 명시적 schema drift 차단.

학습-운영 일치는 dtype 정확한 일치(int64 vs float64)가 아닌 *카테고리 일치* 로 정의.
이유: 운영 환경 parquet 의 OHLCV 가 int↔float 사이를 오가는 것은 빈번하나
LightGBM 동작에 영향 0. *카테고리 불일치* (numeric 기대인데 object 등) 만 차단.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


# ── 67 features schema (v11a_prime baseline) ─────────────────────────────────

# allowlist JSON 이 single source of truth — 차기 W7A 에서 추출된 실제 67.
# 모듈 로드 시점에 1회 읽고 frozen tuple 로 보관. 모두 numeric (현 baseline 가정).
_ALLOWLIST_PATH = Path(__file__).parent / "v11a_prime_allowlist.json"


def _load_feature_names() -> tuple[str, ...]:
    if not _ALLOWLIST_PATH.exists():
        raise FileNotFoundError(
            f"v11a_prime_allowlist.json 없음: {_ALLOWLIST_PATH}. "
            "차기 W7A 박제 자산 — 절대 이동·삭제 금지."
        )
    with open(_ALLOWLIST_PATH, encoding="utf-8") as f:
        names = json.load(f)
    if not isinstance(names, list) or len(names) != 67:
        raise ValueError(f"allowlist 67개 list 기대, got {type(names).__name__} len={len(names)}")
    return tuple(str(n) for n in names)


FEATURE_NAMES_V11: tuple[str, ...] = _load_feature_names()
FEATURE_CATEGORY_V11: dict[str, str] = {n: "numeric" for n in FEATURE_NAMES_V11}


# ── 검증 결과 자료구조 ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class Mismatch:
    column:   str
    issue:    str         # "missing" | "wrong_category"
    expected: str         # "numeric" | "categorical"
    actual:   str         # 실제 dtype 문자열 또는 "<absent>"

    def __str__(self) -> str:
        return f"[{self.issue}] {self.column}: expected {self.expected}, got {self.actual}"


# ── 검증 함수 ──────────────────────────────────────────────────────────────

def validate_alignment(
    df:       pd.DataFrame,
    *,
    schema:   dict[str, str] = FEATURE_CATEGORY_V11,
    required: Iterable[str] | None = None,
) -> list[Mismatch]:
    """df 가 schema 기대와 일치하는지 검증.
    누락 + 카테고리 불일치를 탐지. 정확한 dtype (int64 vs float64) 차이는 무시.
    """
    cols = set(df.columns)
    out: list[Mismatch] = []
    targets = list(required) if required is not None else list(schema.keys())
    for name in targets:
        expected_cat = schema.get(name, "numeric")
        if name not in cols:
            out.append(Mismatch(column=name, issue="missing",
                                expected=expected_cat, actual="<absent>"))
            continue
        s = df[name]
        if expected_cat == "numeric":
            if not pd.api.types.is_numeric_dtype(s):
                out.append(Mismatch(column=name, issue="wrong_category",
                                    expected="numeric", actual=str(s.dtype)))
        elif expected_cat == "categorical":
            if not (pd.api.types.is_string_dtype(s)
                    or isinstance(s.dtype, pd.CategoricalDtype)):
                out.append(Mismatch(column=name, issue="wrong_category",
                                    expected="categorical", actual=str(s.dtype)))
    return out


def assert_aligned(df: pd.DataFrame, *, where: str = "<unknown>",
                   schema: dict[str, str] = FEATURE_CATEGORY_V11,
                   required: Iterable[str] | None = None) -> None:
    """학습·추론 진입점에서 호출. 불일치 시 ValueError raise (실패 즉시 차단)."""
    mismatches = validate_alignment(df, schema=schema, required=required)
    if mismatches:
        head = "\n  ".join(str(m) for m in mismatches[:10])
        more = f"\n  ... and {len(mismatches) - 10} more" if len(mismatches) > 10 else ""
        raise ValueError(
            f"feature schema mismatch at {where} ({len(mismatches)} issue(s)):\n  {head}{more}"
        )


# ── allowlist JSON 호환 ─────────────────────────────────────────────────────

def load_allowlist_json(path: str | Path) -> list[str]:
    """v11a_prime_allowlist.json 형식 호환 — schema 와 교차 검증용."""
    with open(path, encoding="utf-8") as f:
        cols = json.load(f)
    if not isinstance(cols, list):
        raise ValueError(f"allowlist JSON 은 리스트여야: {path}")
    return [str(c) for c in cols]


def schema_features() -> list[str]:
    """schema 의 feature 이름 리스트. allowlist 형식과 호환."""
    return list(FEATURE_NAMES_V11)
