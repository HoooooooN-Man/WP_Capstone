"""
services/confidence.py
======================
Tier 1.4 (차별화 §2.1) — 앙상블 모델 간 분산을 신뢰구간으로 변환.

`scores` 테이블의 prob_lgbm / prob_xgb / prob_cat 세 값에서 표본 표준편차를
계산해 응답 시점에 부착한다. DB 스키마는 변경하지 않는다 (캡스톤 범위).

향후(Phase 3.0 분할 시) `services/scores_svc.py` 의 후처리 단계로 흡수.
"""

from __future__ import annotations

import math
import os
from typing import Iterable

# 모델 의견 불일치 임계값. probability 표준편차 기준.
# 0~1 범위 확률에서 σ=0.05 = 평균 ± 5%p 변동 — 의견 분기 시그널.
# 운영 환경에서 분포 보고 재조정 가능하도록 env override 노출.
DISAGREEMENT_THRESHOLD = float(os.getenv("DISAGREEMENT_THRESHOLD", "0.05"))

# B28 fix: 이전엔 prob_std × 100 으로 score_std 매핑 — score 는 백분위 랭킹(0-100)
# 이라 prob_std 와 단위/스케일이 다르다. 실제 *score 단위 분산* 을 추정하려면
# rank space 에서 계산해야 정확하지만, 응답 시점에 전체 universe 가 없으므로
# 다음과 같은 1차 근사 사용:
#   score_std ≈ prob_std × ranking_sensitivity (모델 확률 1%p 변동이 점수 단위로
#               유발하는 변동량). 경험치: 한국 시장 universe ~2300 종목에서 prob 1%p
#               ≈ 6~8 ranking 변동 ≈ score 0.3-0.4 단위. 보수적으로 ×30 사용.
PROB_TO_SCORE_SCALE = float(os.getenv("PROB_TO_SCORE_SCALE", "30.0"))


def _stdev3(a: float, b: float, c: float) -> float:
    """세 값의 표본 표준편차 (n-1 분모)."""
    mean = (a + b + c) / 3.0
    s2 = ((a - mean) ** 2 + (b - mean) ** 2 + (c - mean) ** 2) / 2.0
    return math.sqrt(max(s2, 0.0))


def annotate_confidence(rows: Iterable[dict]) -> list[dict]:
    """
    rows: prob_lgbm/prob_xgb/prob_cat 가 포함된 dict 목록.
    각 dict 에 prob_std, score_std, model_disagreement 를 추가해 반환.
    원본 dict 를 직접 mutate 하므로 caller 가 동일 리스트를 그대로 사용해도 안전.
    """
    out: list[dict] = []
    for r in rows:
        try:
            lgbm = float(r["prob_lgbm"])
            xgb  = float(r["prob_xgb"])
            cat  = float(r["prob_cat"])
        except (KeyError, TypeError, ValueError):
            # 세 확률이 없으면 신뢰구간 계산 불가 — Optional 필드라 None 으로 둠.
            out.append(r)
            continue

        prob_std = _stdev3(lgbm, xgb, cat)
        r["prob_std"] = round(prob_std, 4)
        r["score_std"] = round(prob_std * PROB_TO_SCORE_SCALE, 2)
        r["model_disagreement"] = prob_std > DISAGREEMENT_THRESHOLD
        out.append(r)
    return out
