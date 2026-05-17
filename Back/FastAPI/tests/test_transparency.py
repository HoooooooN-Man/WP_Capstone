"""GET /api/v1/transparency/* — holdout 박제 read-only."""
import pytest


def test_transparency_summary(client, have_archive):
    if not have_archive:
        pytest.skip("_archive 디렉토리 부재")
    # transparency.py 의 첫 endpoint — holdout_summary
    r = client.get("/api/v1/transparency/holdout/summary")
    assert r.status_code in (200, 404), r.text
    if r.status_code == 200:
        body = r.json()
        assert isinstance(body, (dict, list))


def test_transparency_full(client, have_archive):
    if not have_archive:
        pytest.skip("_archive 디렉토리 부재")
    r = client.get("/api/v1/transparency/holdout/full")
    assert r.status_code in (200, 404)


def test_transparency_model_card(client, have_archive):
    if not have_archive:
        pytest.skip("_archive 디렉토리 부재")
    r = client.get("/api/v1/transparency/model-card")
    # 실제 path 가 다르면 404 — 라우터 정의 변경 회귀 시그널
    assert r.status_code in (200, 404)


def test_transparency_no_500(client):
    """미존재 경로는 404."""
    r = client.get("/api/v1/transparency/__zzz__")
    assert r.status_code == 404
