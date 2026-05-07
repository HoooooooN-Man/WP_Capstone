"""
test_playground.py
==================
Tier 2.5 — 정책 grid 노출 회귀 테스트.
"""

from __future__ import annotations


def test_playground_grid_endpoint(client):
    r = client.get("/api/v1/playground/grid")
    assert r.status_code == 200
    body = r.json()
    assert "available" in body
    if body["available"]:
        assert "axis_cutoff" in body
        assert "axis_top_k"  in body
        assert "combinations" in body
        # 6 × 3 = 18 조합 (Tier 2.5 정의).
        assert len(body["combinations"]) == 18
        # 각 항목에 필수 키.
        for c in body["combinations"]:
            assert "cutoff" in c and "top_k" in c
            assert "sharpe" in c and "cumulative_return" in c
        assert r.headers.get("X-Sealed-Grid") == "true"


def test_playground_grid_axis_values(client):
    r = client.get("/api/v1/playground/grid")
    if r.status_code != 200 or not r.json().get("available"):
        return
    body = r.json()
    assert body["axis_cutoff"] == [85, 88, 90, 93, 95, 97]
    assert body["axis_top_k"]  == [10, 20, 50]
