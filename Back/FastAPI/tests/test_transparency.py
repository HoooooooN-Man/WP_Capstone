"""
test_transparency.py
====================
Tier 1.5 (차별화 §2.2) — holdout 박제 read-only 노출 회귀 테스트.
"""

from __future__ import annotations


def test_holdout_summary_endpoint_exists(client):
    r = client.get("/api/v1/transparency/holdout/summary")
    assert r.status_code == 200
    body = r.json()
    assert "available" in body
    if body["available"]:
        assert isinstance(body.get("ece"), (int, float))
        assert isinstance(body.get("brier"), (int, float))
        assert "sealed_at" in body and isinstance(body["sealed_at"], str)
        assert r.headers.get("X-Holdout-Sealed") == "true"
    else:
        assert r.headers.get("X-Holdout-Sealed") == "false"


def test_holdout_full_endpoint_exists(client):
    r = client.get("/api/v1/transparency/holdout")
    assert r.status_code == 200
    body = r.json()
    assert "available" in body
    if body["available"]:
        assert "report" in body
        assert "calibration" in body
        # 핵심 박제 키들이 있어야 한다.
        report = body["report"]
        assert "strategy" in report
        assert "alpha_vs_kospi" in report
        s = report["strategy"]
        assert "sharpe_ratio" in s
        assert "psr_threshold_0" in s
        assert "dsr_n1" in s


def test_health_metrics_includes_holdout_calibration(client):
    r = client.get("/health/metrics?window_days=7")
    assert r.status_code == 200
    body = r.json()
    if body.get("status") == "ok" and body.get("summary"):
        summary = body["summary"]
        # ECE/Brier 키는 항상 노출 (값이 None 일 수도 있음).
        assert "ece_holdout" in summary
        assert "brier_holdout" in summary
        assert "holdout_sealed_at" in summary


def test_holdout_full_includes_ablation(client):
    """Tier 1B 4.2 — ablation 결과가 박제되어 있으면 holdout 응답에 포함."""
    r = client.get("/api/v1/transparency/holdout")
    assert r.status_code == 200
    body = r.json()
    if body.get("available"):
        assert "ablation" in body
        if body["ablation"] is not None:
            ab = body["ablation"]
            assert "candidates" in ab
            assert "ensemble_vs_lgbm" in ab
            # 5개 후보 (lgbm/xgb/cat/meta/simple_mean).
            assert len(ab["candidates"]) >= 4


def test_model_card_endpoint(client):
    """Tier 1.5 — Model Card 마크다운 노출."""
    r = client.get("/api/v1/transparency/model-card")
    assert r.status_code == 200
    body = r.json()
    assert "available" in body
    if body["available"]:
        assert isinstance(body["markdown"], str)
        # Mitchell et al. 표준 섹션 헤더 몇 개가 본문에 있어야 한다.
        md = body["markdown"]
        assert "Model Card" in md
        assert "한계" in md or "Limitations" in md
        assert "데이터 분할" in md or "Data Splits" in md
        assert r.headers.get("X-Holdout-Sealed") == "true"
