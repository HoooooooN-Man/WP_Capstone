"""
routers/playground.py
=====================
Tier 2.5 (차별화 §2.4 / 캡스톤 §5.5) — 사용자 정책 슬라이더 grid 노출.

엔드포인트:
  GET /api/v1/playground/grid    → 사전계산된 (cutoff, top_k) grid 반환

설계:
  - playground_grid.py 가 박제한 `_archive/playground/grid_v9.json` 을 그대로 노출.
  - 캐시: lru_cache (파일 변경되면 서버 재시작 필요).
  - 박제 파일이 없으면 graceful 빈 응답.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Response

from ..core.config import CAPSTONE_ROOT


router = APIRouter(prefix="/playground", tags=["playground"])
logger = logging.getLogger(__name__)


def _grid_path() -> Path:
    return Path(CAPSTONE_ROOT).parent / "_archive" / "playground" / "grid_v9.json"


@lru_cache(maxsize=1)
def _load_grid() -> Optional[dict]:
    p = _grid_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("playground grid parse failed: %s", e)
        return None


@router.get(
    "/grid",
    summary="사전계산된 정책 grid (cutoff × top_k)",
)
def playground_grid(request: Request, response: Response):
    """
    Tier 2.5 — 사용자가 슬라이더로 조작할 (cutoff, top_k) 조합의 사전 평가 결과.
    """
    g = _load_grid()
    response.headers["X-Sealed-Grid"] = "true" if g is not None else "false"
    if g is None:
        return {
            "available": False,
            "message":   "Playground grid 가 박제되어 있지 않습니다 (playground_grid.py 실행 필요).",
        }
    return {"available": True, **g}
