"""
schemas/meta.py
===============
Tier 1.7 (PRD §1.2) — ML API 응답 메타 봉투.

설계 원칙 (하위 호환):
  - 기존 응답 모델에 *Optional* `meta` 필드를 추가만 한다.
  - 기존 클라이언트 코드(top-level `model_version`, `date`, `total` 등)가 깨지지 않도록
    필드 삭제·이름 변경은 하지 않는다.
  - 라우터는 `attach_meta(payload, request, ...)` 헬퍼로 meta 를 채운다.

응답 예시:
    {
      "date": "2026-05-06",
      "model_version": "v9",
      "total": 20,
      "items": [...],
      "meta": {
        "model_version": "v9",
        "as_of_date":    "2026-05-06",
        "generated_at":  "2026-05-07T10:30:11Z",
        "cache_hit":     true,
        "is_stub":       false,
        "request_id":    "uuid"
      }
    }
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, TypeVar

from fastapi import Request
from pydantic import BaseModel


class ResponseMeta(BaseModel):
    """
    ML API 공통 메타.

    캡스톤 Tier 1.7 의 6 필드 + 차기 사이클 (W1·W2·W3·W3.5·W6) 의 6 신규 필드.
    *모든 신규 필드는 default 보유* — 기존 캐시 키·하위 호환 깨지지 않음.
    """
    # ── 캡스톤 Tier 1.7 ────────────────────────────────────────────────────
    model_version: Optional[str] = None
    as_of_date:    Optional[str] = None     # 응답 데이터의 기준일 (YYYY-MM-DD)
    generated_at:  str                      # 응답 생성 시각 (UTC ISO8601)
    cache_hit:     bool          = False
    is_stub:       bool          = False
    request_id:    Optional[str] = None
    # ── 차기 사이클 표준 (CLAUDE.md §반드시 지킬 것 1번 / 차기_사이클.md §응답 메타) ──
    impression_id:     Optional[str] = None  # W1 — 노출 추적용 UUID. recommendations 류만 부여
    is_advice:         bool          = False  # 컴플라이언스 — 항상 false
    embedding_version: Optional[str] = None  # W3.5 이후 채워짐
    cohort:            Optional[str] = None  # W2 이후 채워짐
    target_label:      Optional[str] = None  # W6 멀티라벨 (기본은 "y_abs_20d"), W6 전엔 None
    diversify:         Optional[str] = None  # W3 — "embedding"/"correlation"/"sector"/"none"


class WithMeta(BaseModel):
    """meta 필드를 갖는 응답 모델의 베이스. 기존 모델은 필요 시 이 클래스를 상속하거나
    Optional[ResponseMeta] 를 직접 추가하면 된다."""
    meta: Optional[ResponseMeta] = None


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

T = TypeVar("T", bound=BaseModel)


def make_meta(
    request: Request,
    *,
    model_version: Optional[str] = None,
    as_of_date:    Optional[str] = None,
    cache_hit:     bool          = False,
    is_stub:       bool          = False,
    # 차기 사이클 옵션 — 호출자가 명시하지 않으면 기존 동작.
    is_impression:     bool          = False,        # True 면 impression_id UUID 자동 부여
    embedding_version: Optional[str] = None,
    cohort:            Optional[str] = None,
    target_label:      Optional[str] = None,
    diversify:         Optional[str] = None,
) -> ResponseMeta:
    """미들웨어가 채워둔 request_id 를 끌어와 메타를 만든다.

    `is_impression=True` 시 노출 추적용 `impression_id` (UUID4) 를 자동 부여.
    프론트는 이 ID 를 :8000 events 라우터에 그대로 전달해 적재 (W1B fire-and-forget).
    """
    rid = getattr(request.state, "request_id", None)
    imp_id = str(uuid.uuid4()) if is_impression else None
    return ResponseMeta(
        model_version=model_version,
        as_of_date=as_of_date,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        cache_hit=cache_hit,
        is_stub=is_stub,
        request_id=rid,
        impression_id=imp_id,
        is_advice=False,
        embedding_version=embedding_version,
        cohort=cohort,
        target_label=target_label,
        diversify=diversify,
    )


def attach_meta(
    payload: T,
    request: Request,
    *,
    model_version: Optional[str] = None,
    as_of_date:    Optional[str] = None,
    cache_hit:     bool          = False,
    is_stub:       bool          = False,
    is_impression:     bool          = False,
    embedding_version: Optional[str] = None,
    cohort:            Optional[str] = None,
    target_label:      Optional[str] = None,
    diversify:         Optional[str] = None,
) -> T:
    """응답 모델 인스턴스에 meta 를 부착해 그대로 반환."""
    payload.meta = make_meta(
        request,
        model_version=model_version,
        as_of_date=as_of_date,
        cache_hit=cache_hit,
        is_stub=is_stub,
        is_impression=is_impression,
        embedding_version=embedding_version,
        cohort=cohort,
        target_label=target_label,
        diversify=diversify,
    )
    return payload
