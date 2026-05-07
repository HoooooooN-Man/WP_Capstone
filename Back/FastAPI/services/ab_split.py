"""
services/ab_split.py
====================
W7B Step 1 — model_version A/B 분배.

목적:
  추천 라우터에서 사용자가 model_version 을 명시하지 않으면 (model_version="latest"),
  user_id (또는 session_id) 의 결정적 hash 로 variant 를 결정.

설계 원칙:
  - **결정적**: 같은 user_id → 항상 같은 variant. 캐시·디버깅 일관성.
  - **균등 분배**: SHA-1(user_id) → 정수 0~99 → 누적 cutoff 비교.
  - **명시 우선**: model_version != "latest" 이면 hash 우회, 그대로 반환.
  - **인프라 모드 default**: 환경변수 미설정 시 "v9:100" — 분배 비활성, 기존 동작 유지.
  - **anonymous fallback**: user_id·session_id 둘 다 없으면 첫 번째 variant.

env var 형식:
  AB_SPLIT="v9:50,v11a_prime:50"           # 50/50
  AB_SPLIT="v9:90,v11a_prime:10"           # canary 10%
  AB_SPLIT="latest:100"  (default)         # 분배 OFF — 기존 동작 (svc 가 latest 결정)

라이브 트래픽 0 인 차기 사이클에서는 인프라만 깔고 default 유지. 차차기 사이클
사용자 진입 시 env var 만 변경하면 즉시 활성화.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Optional

DEFAULT_SPLIT = "latest:100"
ENV_VAR = "AB_SPLIT"


@dataclass(frozen=True)
class SplitResult:
    variant:    str           # 결정된 model_version
    bucket:     int           # 0~99 hash bucket (디버깅·로깅용)
    via:        str           # "override" | "hash" | "fallback"
    split_used: tuple[tuple[str, int], ...]   # 적용된 분배 (variant, weight)


def parse_split(spec: str) -> tuple[tuple[str, int], ...]:
    """
    "v9:50,v11a_prime:50" → (("v9", 50), ("v11a_prime", 50)).
    합 100 강제 (틀리면 ValueError). 빈 spec → DEFAULT_SPLIT.
    """
    spec = (spec or "").strip() or DEFAULT_SPLIT
    pairs: list[tuple[str, int]] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(f"AB_SPLIT 형식 오류 — 'variant:weight' 필요: {chunk!r}")
        name, w = chunk.split(":", 1)
        name = name.strip()
        if not name:
            raise ValueError(f"AB_SPLIT variant 이름 비어있음: {chunk!r}")
        try:
            weight = int(w.strip())
        except ValueError as e:
            raise ValueError(f"AB_SPLIT weight 정수 아님: {chunk!r}") from e
        if weight < 0:
            raise ValueError(f"AB_SPLIT weight 음수: {chunk!r}")
        pairs.append((name, weight))
    total = sum(w for _, w in pairs)
    if total != 100:
        raise ValueError(f"AB_SPLIT weight 합 100 아님: {total}")
    return tuple(pairs)


def hash_bucket(key: str) -> int:
    """key 를 0~99 정수 bucket 으로. SHA-1 결정적."""
    h = hashlib.sha1(key.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") % 100


def _pick_by_bucket(bucket: int, split: tuple[tuple[str, int], ...]) -> str:
    cum = 0
    for name, weight in split:
        cum += weight
        if bucket < cum:
            return name
    return split[-1][0]   # 안전망 — 합 100 검증돼서 도달 안 함


def resolve_variant(
    *,
    user_id:    Optional[int | str] = None,
    session_id: Optional[str]       = None,
    override:   str                  = "latest",
    split_spec: Optional[str]        = None,
) -> SplitResult:
    """
    model_version 결정.
    - override != "latest" → 명시값 그대로 (override-via).
    - 아니면 user_id (있으면) 또는 session_id 기반 hash split.
    - 둘 다 없으면 첫 번째 variant (fallback).
    """
    if override and override != "latest":
        return SplitResult(variant=override, bucket=-1, via="override",
                           split_used=())

    spec = split_spec if split_spec is not None else os.getenv(ENV_VAR, DEFAULT_SPLIT)
    split = parse_split(spec)

    key = None
    if user_id is not None and str(user_id) != "":
        key = f"u:{user_id}"
    elif session_id:
        key = f"s:{session_id}"

    if key is None:
        return SplitResult(variant=split[0][0], bucket=-1, via="fallback",
                           split_used=split)

    bucket = hash_bucket(key)
    variant = _pick_by_bucket(bucket, split)
    return SplitResult(variant=variant, bucket=bucket, via="hash", split_used=split)
