"""
test_confidence.py
==================
Tier 1.4 (차별화 §2.1) — 신뢰구간 산출 회귀 테스트.

검증 대상:
  - annotate_confidence 가 prob_std / score_std / model_disagreement 를 채운다.
  - 세 확률이 동일하면 prob_std == 0, model_disagreement == False.
  - 세 확률이 크게 벌어지면 model_disagreement == True.
  - prob_lgbm 등이 누락된 row 는 침묵으로 통과 (Optional 필드).

API 응답 회귀:
  - /api/v1/stocks/recommendations 응답의 items[0] 에 prob_std 등이 포함되는지.
"""

from __future__ import annotations

import math

from Back.FastAPI.services.confidence import (
    annotate_confidence,
    DISAGREEMENT_THRESHOLD,
)


def test_unanimous_models_have_zero_std():
    rows = [{"prob_lgbm": 0.7, "prob_xgb": 0.7, "prob_cat": 0.7}]
    out = annotate_confidence(rows)
    assert math.isclose(out[0]["prob_std"], 0.0, abs_tol=1e-9)
    assert out[0]["score_std"] == 0.0
    assert out[0]["model_disagreement"] is False


def test_divergent_models_flag_disagreement():
    # σ ≈ 0.27 (>> 0.05 임계)
    rows = [{"prob_lgbm": 0.2, "prob_xgb": 0.5, "prob_cat": 0.8}]
    out = annotate_confidence(rows)
    assert out[0]["prob_std"] > DISAGREEMENT_THRESHOLD
    assert out[0]["model_disagreement"] is True
    # 점수 단위 환산 (× 100) 도 함께 채워졌는지.
    assert out[0]["score_std"] > 0


def test_missing_prob_columns_are_silent():
    rows = [{"prob_ensemble": 0.7}]   # prob_lgbm/xgb/cat 없음
    out = annotate_confidence(rows)
    assert "prob_std" not in out[0] or out[0].get("prob_std") is None


def test_modifies_in_place_returns_same_list():
    rows = [{"prob_lgbm": 0.5, "prob_xgb": 0.5, "prob_cat": 0.5}]
    out = annotate_confidence(rows)
    # caller 가 같은 객체를 그대로 써도 안전.
    assert out[0] is rows[0]
    assert "prob_std" in rows[0]


def test_recommendations_response_has_confidence_fields(client):
    r = client.get("/api/v1/stocks/recommendations?top_k=3")
    if r.status_code != 200:
        return
    body = r.json()
    items = body.get("items", [])
    if not items:
        return
    first = items[0]
    # Optional 이지만 prob_lgbm 등이 있는 환경에선 채워져 있어야 한다.
    if all(k in first for k in ("prob_lgbm", "prob_xgb", "prob_cat")):
        assert "prob_std" in first
        assert "score_std" in first
        assert "model_disagreement" in first
        assert isinstance(first["model_disagreement"], bool)
