"""
JSON 리포트 — 슬라이스 × 메트릭 매트릭스를 dict 로.
CI 통합·외부 분석 도구가 본 JSON 을 직접 소비할 수 있도록 평탄한 구조.
"""

from __future__ import annotations

from datetime import datetime, timezone


def build_json(
    *,
    model_version: str,
    overall: dict,
    slices: list[dict],
) -> dict:
    """
    overall: 전 데이터의 메트릭 dict (compute_metric_bundle().to_dict()).
    slices : 각 슬라이스 dict 목록. 각 dict 는 {dimension, key, metrics} 구조.
    """
    return {
        "schema_version": "1.0",
        "generated_at":   datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_version":  model_version,
        "overall":        overall,
        "slices":         slices,
    }
