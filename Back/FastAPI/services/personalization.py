"""
services/personalization.py
===========================
W2 — Cohort 기반 reranking (08_recommendation_logic_improvements.md §3.2 1단계).

설계 원칙:
  - 모델 재학습 0. 서빙 *후처리* 로만 cohort 별 ranking 변형.
  - **`cohort=None` 또는 `"balanced"` → no-op**. 기존 동작 유지 (CLAUDE.md §반드시 지킬 것 2번).
  - 입력 컬럼이 누락되면 그 조건만 *무시* (graceful) — 빈 결과 반환하지 않음.
  - 컴플라이언스: 본 함수는 ranking 변형만, "추천/투자자문/매수" 단어 사용 안 함.
    호출자가 응답 meta 에 `cohort` 채우고 `is_advice: false` 유지 (W1C 표준).

5 코호트 (08 §3.2):
  - conservative : volatility_60d 하위 50% 필터 → Top-N
  - balanced     : v9 점수 그대로 (default)
  - growth       : score + ret_lag_60d × 10 정렬 (모멘텀 가중)
  - dividend     : dividend_yield > 2% 필터 + score 정렬
  - value        : PER<15 AND PBR<1.5 필터 + score 정렬

본 모듈은 *순수 함수* — 단위 테스트 가능. DB·HTTP 의존 0.
"""

from __future__ import annotations

from statistics import median
from typing import Iterable, Optional


VALID_COHORTS = frozenset({"conservative", "balanced", "growth", "dividend", "value"})


def normalize_cohort(cohort: Optional[str]) -> Optional[str]:
    """입력값 정규화. 알 수 없는 코호트는 None (balanced 와 동치) 반환."""
    if not cohort:
        return None
    c = str(cohort).strip().lower()
    if c == "" or c == "balanced":
        return None
    return c if c in VALID_COHORTS else None


def rerank_for_cohort(
    rows: list[dict],
    cohort: Optional[str],
    *,
    top_k: int = 20,
) -> list[dict]:
    """
    cohort 별 reranking 후 top_k 잘라 반환.

    Parameters
    ----------
    rows : 추천 응답 행. 각 dict 에 score 필수, cohort 별 추가 컬럼이 있으면 활용.
    cohort : None / "balanced" / "conservative" / "growth" / "dividend" / "value"
    top_k : 0 이면 전체, 양수면 그 수만큼 잘라 반환.
    """
    c = normalize_cohort(cohort)
    if c is None:
        return _take(rows, top_k)

    if c == "conservative":
        rows = _filter_low_volatility(rows)
    elif c == "dividend":
        rows = [r for r in rows if _safe_float(r.get("dividend_yield"), default=0.0) > 0.02]
    elif c == "value":
        rows = [
            r for r in rows
            if _safe_float(r.get("per"), default=float("inf")) < 15.0
            and _safe_float(r.get("pbr"), default=float("inf")) < 1.5
        ]
    elif c == "growth":
        # 점수 + ret_lag_60d × 10 가중. row 자체는 변경하지 않음 (정렬 키만).
        rows = sorted(
            rows,
            key=lambda r: (
                _safe_float(r.get("score"), default=0.0)
                + _safe_float(r.get("ret_lag_60d"), default=0.0) * 10.0
            ),
            reverse=True,
        )

    return _take(rows, top_k)


# ── 내부 헬퍼 ────────────────────────────────────────────────────────────────

def _take(rows: list[dict], top_k: int) -> list[dict]:
    if top_k <= 0:
        return list(rows)
    return list(rows[:top_k])


def _safe_float(v, default: float) -> float:
    """None·NaN·문자열 등 비정상 입력은 default 로 안전 변환."""
    if v is None:
        return default
    try:
        f = float(v)
        # NaN 체크 — `f != f` 트릭.
        if f != f:
            return default
        return f
    except (TypeError, ValueError):
        return default


def _filter_low_volatility(rows: list[dict]) -> list[dict]:
    """volatility_60d 가 *어떤 행에든* 있으면 하위 50% 필터. 전부 없으면 미필터."""
    vols = [_safe_float(r.get("volatility_60d"), default=float("nan")) for r in rows]
    valid = [v for v in vols if v == v]   # NaN 제거
    if not valid:
        return rows
    cutoff = median(valid)
    return [
        r for r in rows
        if _safe_float(r.get("volatility_60d"), default=float("inf")) <= cutoff
    ]
