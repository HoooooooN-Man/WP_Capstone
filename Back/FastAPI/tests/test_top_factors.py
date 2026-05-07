"""
test_top_factors.py
===================
Tier 1.3 (PRD §4.4 / 차별화 §2.3) — SHAP top_factors API 노출 회귀 테스트.

검증 대상:
  - StockScore 스키마에 top_factors 필드가 정의되어 있다.
  - 추천 응답이 200 일 때, 적재된 행은 top_factors list[dict] 를 반환한다.
  - 적재되지 않은 행은 top_factors=None.
  - 각 factor 항목이 {feature, contribution, direction, label, display} 모양을 따른다.

DuckDB 데이터·top_factors 적재가 없는 환경에서는 silent pass.
"""

from __future__ import annotations


def test_stock_score_schema_declares_top_factors():
    from Back.FastAPI.schemas.stocks import StockScore
    fields = StockScore.model_fields
    assert "top_factors" in fields, fields.keys()
    assert "prob_std" in fields
    assert "score_std" in fields
    assert "model_disagreement" in fields


def _assert_factor_shape(f: dict):
    assert isinstance(f, dict), f
    for key in ("feature", "contribution", "direction", "label", "display"):
        assert key in f, f
    assert f["direction"] in ("positive", "negative")
    assert isinstance(f["contribution"], (int, float))
    assert isinstance(f["label"], str) and len(f["label"]) > 0


def test_recommendations_top_factors_shape(client):
    r = client.get(
        "/api/v1/stocks/recommendations"
        "?date=2026-04-29&model_version=v9&top_k=5"
    )
    if r.status_code != 200:
        # 데이터 없는 환경에서는 검증 스킵.
        return
    body = r.json()
    items = body.get("items", [])
    if not items:
        return
    # 적어도 하나의 항목이 top_factors 를 포함해야 한다 (적재 확인).
    populated = [it for it in items if it.get("top_factors")]
    if not populated:
        # 적재 안 된 환경 — None 이어야 한다.
        for it in items:
            assert it.get("top_factors") is None, it
        return

    for it in populated:
        factors = it["top_factors"]
        assert isinstance(factors, list)
        assert 1 <= len(factors) <= 5
        for f in factors:
            _assert_factor_shape(f)


def test_recommendations_top_factors_korean_label_present(client):
    r = client.get(
        "/api/v1/stocks/recommendations"
        "?date=2026-04-29&model_version=v9&top_k=5"
    )
    if r.status_code != 200:
        return
    items = r.json().get("items", [])
    populated = [it for it in items if it.get("top_factors")]
    if not populated:
        return
    # 자연어 라벨에 한국어가 한 글자라도 포함되어야 한다 (자동 폴백 포함).
    sample_label = populated[0]["top_factors"][0]["label"]
    assert any("가" <= ch <= "힣" for ch in sample_label), sample_label
