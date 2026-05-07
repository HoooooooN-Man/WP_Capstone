"""
shap_extractor.py
=================
Tier 1.3 (PRD §4.4 / 차별화 §2.3) — LightGBM `pred_contrib` 결과에서
종목별 상위 K개 기여 피처를 추출하고 자연어로 변환하는 *순수 함수* 모듈.

설계 의도:
  - I/O(모델 로드, DuckDB 적재) 와 분리해 단위 테스트가 쉽도록 한다.
  - compute_shap.py(엔트리포인트) 가 본 모듈을 호출.
  - 라우터·서비스도 운영 환경에서 본 모듈의 자연어 변환부를 재사용 가능.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import yaml


# ── 자연어 매핑 ─────────────────────────────────────────────────────────────

_DESCRIPTIONS_CACHE: Optional[dict] = None


def load_descriptions(path: Optional[Path] = None) -> dict:
    """feature_descriptions.yaml 을 로드. 첫 호출 결과는 캐시."""
    global _DESCRIPTIONS_CACHE
    if _DESCRIPTIONS_CACHE is not None and path is None:
        return _DESCRIPTIONS_CACHE

    if path is None:
        path = Path(__file__).resolve().parent / "feature_descriptions.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if path == Path(__file__).resolve().parent / "feature_descriptions.yaml":
        _DESCRIPTIONS_CACHE = data
    return data


def describe_factor(
    safe_name: str,
    contribution: float,
    *,
    descriptions: Optional[dict] = None,
    col_name_map_inv: Optional[dict] = None,
) -> dict:
    """단일 기여 피처를 자연어 dict 로 변환.

    Returns
    -------
    {
      "feature":     "외국인_거래대금",   # 표시용 (orig 한글 우선)
      "contribution": 0.0421,
      "direction":   "positive" | "negative",
      "label":       "외국인 5일 순매수 양호",
      "display":     "외국인 순매수 (5일)",
    }
    """
    descs = descriptions if descriptions is not None else load_descriptions()
    inv = col_name_map_inv or {}

    # safe → orig 한글 우선 매핑.
    orig_name = inv.get(safe_name, safe_name)
    direction = "positive" if contribution >= 0 else "negative"

    # orig → safe 순서로 사전 lookup.
    entry = descs.get(orig_name) or descs.get(safe_name) or {}
    display = entry.get("display") or orig_name
    label = entry.get(direction) or _fallback_label(display, direction)

    return {
        "feature":      orig_name,
        "contribution": float(round(contribution, 6)),
        "direction":    direction,
        "label":        label,
        "display":      display,
    }


def _fallback_label(display: str, direction: str) -> str:
    """매핑이 없는 피처에 대한 안전한 일반 문구 (정직성 우선)."""
    if direction == "positive":
        return f"{display} 가 점수에 양의 방향으로 기여"
    return f"{display} 가 점수에 음의 방향으로 기여"


# ── SHAP 추출 ───────────────────────────────────────────────────────────────

def extract_top_factors(
    contributions_row: np.ndarray,
    feature_names: list[str],
    *,
    top_k: int = 3,
    min_abs: float = 1e-6,
    descriptions: Optional[dict] = None,
    col_name_map_inv: Optional[dict] = None,
) -> list[dict]:
    """LightGBM pred_contrib 의 한 행(피처 + 마지막 bias)에서 top-K 추출.

    Parameters
    ----------
    contributions_row : (n_features + 1,) ndarray
        LightGBM `predict(..., pred_contrib=True)` 결과의 한 행. 마지막 원소는 bias.
    feature_names : list[str]
        모델이 학습된 피처 순서 (safe ASCII 이름).
    top_k : int
        반환할 상위 기여 피처 수. 기본 3.
    min_abs : float
        절대값이 이 임계 미만이면 제외 (의미 없는 잡음 컷).
    """
    if contributions_row.shape[0] != len(feature_names) + 1:
        raise ValueError(
            f"contributions_row length {contributions_row.shape[0]} "
            f"!= n_features + 1 ({len(feature_names) + 1})"
        )

    # 마지막 원소(bias) 제외.
    contribs = contributions_row[:-1]

    # 절대값 기준 내림차순 인덱스.
    order = np.argsort(-np.abs(contribs))
    out: list[dict] = []
    for idx in order:
        c = float(contribs[idx])
        if abs(c) < min_abs:
            break
        out.append(describe_factor(
            feature_names[idx],
            c,
            descriptions=descriptions,
            col_name_map_inv=col_name_map_inv,
        ))
        if len(out) >= top_k:
            break
    return out


def serialize_top_factors(factors: list[dict]) -> str:
    """DuckDB VARCHAR 컬럼에 저장하기 위한 JSON 문자열."""
    return json.dumps(factors, ensure_ascii=False)


def deserialize_top_factors(text: Optional[str]) -> list[dict]:
    """API 응답 시점에 JSON → list[dict] 복원. None/빈 문자열은 빈 리스트."""
    if not text:
        return []
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []


# ── 배치 변환 ──────────────────────────────────────────────────────────────

def extract_top_factors_batch(
    contributions: np.ndarray,
    feature_names: list[str],
    *,
    top_k: int = 3,
    descriptions: Optional[dict] = None,
    col_name_map_inv: Optional[dict] = None,
) -> list[list[dict]]:
    """(n_rows, n_features+1) 행렬을 받아 행별 top-K 리스트를 반환."""
    if contributions.ndim != 2:
        raise ValueError(f"contributions must be 2D, got shape {contributions.shape}")

    out = []
    for row in contributions:
        out.append(extract_top_factors(
            row, feature_names,
            top_k=top_k,
            descriptions=descriptions,
            col_name_map_inv=col_name_map_inv,
        ))
    return out
