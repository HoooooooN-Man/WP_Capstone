"""
services/holdout_archive.py
===========================
Tier 1.1 / 1B 4.1 — 박제된 holdout 결과를 read-only 로 API 에 노출.

박제 디렉터리 (`_archive/holdout_2026_q1_q2/`) 의 JSON 을 그대로 읽어 응답한다.
서버는 박제 파일을 *수정하지 않는다* (filesystem read-only).

핸들링:
  - 박제 파일이 없으면 None 반환 (transparency 페이지가 "데이터 미박제" 표시).
  - 파싱 실패 시 None 반환 + 로그.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _archive_dir() -> Path:
    """capstone_root 의 _archive/holdout_2026_q1_q2/ 를 반환."""
    # config.py 의 CAPSTONE_ROOT 는 project_data 를 가리킴 → 그 부모가 캡스톤 루트.
    from ..core.config import CAPSTONE_ROOT
    explicit = os.getenv("HOLDOUT_ARCHIVE_DIR")
    if explicit:
        return Path(explicit)
    return Path(CAPSTONE_ROOT).parent / "_archive" / "holdout_2026_q1_q2"


@lru_cache(maxsize=1)
def _load_report() -> Optional[dict]:
    path = _archive_dir() / "holdout_v9_report.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("holdout report parse failed: %s", e)
        return None


@lru_cache(maxsize=1)
def _load_calibration() -> Optional[dict]:
    path = _archive_dir() / "calibration_v9.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("holdout calibration parse failed: %s", e)
        return None


def get_holdout_metrics_summary() -> dict:
    """`/health/metrics` summary 에 합칠 ECE·Brier·sealed_at."""
    calib = _load_calibration()
    report = _load_report()
    if not calib or not calib.get("overall"):
        return {"ece_holdout": None, "brier_holdout": None, "holdout_sealed_at": None}
    overall = calib["overall"]
    sealed = calib.get("sealed_at") or (report.get("sealed_at") if report else None)
    return {
        "ece_holdout":       overall.get("ece"),
        "brier_holdout":     overall.get("brier"),
        "holdout_sealed_at": sealed,
    }


@lru_cache(maxsize=1)
def _load_ablation() -> Optional[dict]:
    path = _archive_dir() / "ablation_v9.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("holdout ablation parse failed: %s", e)
        return None


@lru_cache(maxsize=1)
def _load_model_card() -> Optional[str]:
    path = _archive_dir() / "model_card_v9.md"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("model card read failed: %s", e)
        return None


def get_full_holdout_payload() -> dict:
    """`/transparency/holdout` 응답 — 박제 결과 전체 (read-only)."""
    report   = _load_report()
    calib    = _load_calibration()
    ablation = _load_ablation()
    if report is None and calib is None and ablation is None:
        return {
            "available": False,
            "message":   "Holdout 결과가 아직 박제되지 않았습니다.",
        }
    return {
        "available":   True,
        "report":      report,
        "calibration": calib,
        "ablation":    ablation,
        "archive_dir": str(_archive_dir()),
    }


def get_model_card_markdown() -> Optional[str]:
    """`/transparency/model-card` 응답용 — 박제된 Model Card 마크다운."""
    return _load_model_card()
