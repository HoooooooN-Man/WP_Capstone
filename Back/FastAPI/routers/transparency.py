"""
routers/transparency.py
=======================
Tier 1.5 (차별화 §2.2) — 박제된 holdout 결과 read-only 노출.

PRD §3.5.3 의 정직성 원칙:
  - holdout 결과는 박제되며 본 라우터는 그것을 *읽기 전용* 으로만 노출한다.
  - 본 라우터의 응답 헤더에 X-Holdout-Sealed: true 를 부착해 클라이언트가
    "박제됨" 표시를 할 수 있게 한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from ..services.holdout_archive import (
    get_full_holdout_payload,
    get_holdout_metrics_summary,
    get_model_card_markdown,
)
from ..schemas.meta import attach_meta
from pydantic import BaseModel
from typing import Optional


router = APIRouter(prefix="/transparency", tags=["transparency"])


class HoldoutSummary(BaseModel):
    available:   bool
    ece:         Optional[float] = None
    brier:       Optional[float] = None
    sealed_at:   Optional[str]   = None
    message:     Optional[str]   = None


class ModelCardResponse(BaseModel):
    available: bool
    markdown:  Optional[str] = None
    message:   Optional[str] = None


@router.get(
    "/holdout/summary",
    response_model=HoldoutSummary,
    summary="박제된 holdout ECE·Brier·sealed_at 요약",
)
def holdout_summary(request: Request, response: Response):
    s = get_holdout_metrics_summary()
    response.headers["X-Holdout-Sealed"] = "true" if s.get("ece_holdout") is not None else "false"
    return HoldoutSummary(
        available=s.get("ece_holdout") is not None,
        ece=s.get("ece_holdout"),
        brier=s.get("brier_holdout"),
        sealed_at=s.get("holdout_sealed_at"),
        message=None if s.get("ece_holdout") is not None else "박제된 holdout 결과가 없습니다.",
    )


@router.get(
    "/holdout",
    summary="박제된 holdout 전체 결과 (read-only)",
)
def holdout_full(request: Request, response: Response):
    """
    `_archive/holdout_2026_q1_q2/` 의 전체 박제 페이로드를 반환한다.
    - report:      Sharpe, MDD, alpha, DSR, PSR
    - calibration: ECE, Brier, reliability bins, per-slice ECE
    - ablation:    단일 LGBM vs 메타 스태킹 비교 (Tier 1B 4.2)
    """
    payload = get_full_holdout_payload()
    response.headers["X-Holdout-Sealed"] = "true" if payload.get("available") else "false"
    return payload


@router.get(
    "/model-card",
    response_model=ModelCardResponse,
    summary="박제된 Model Card 마크다운 (Tier 1.5)",
)
def model_card(request: Request, response: Response):
    """
    Mitchell et al. (2018) 표준의 v9 Model Card 마크다운 원문을 반환.
    프론트가 markdown-it 등으로 렌더해 `/transparency` 페이지에 표시.
    """
    md = get_model_card_markdown()
    response.headers["X-Holdout-Sealed"] = "true" if md is not None else "false"
    return ModelCardResponse(
        available=md is not None,
        markdown=md,
        message=None if md is not None else "Model Card 가 아직 박제되지 않았습니다.",
    )
