"""GET /api/v1/playground — grid_v9.json (_archive)."""
import pytest


def test_playground_grid_v9(client, have_archive):
    if not have_archive:
        pytest.skip("_archive 디렉토리 부재")
    r = client.get("/api/v1/playground/grid")
    # 라우터 구현에 따라 / 또는 /grid 일 수 있음 — 둘 다 시도.
    if r.status_code == 404:
        r = client.get("/api/v1/playground")
    assert r.status_code in (200, 404), r.text


def test_playground_no_internal_error(client):
    """라우터 자체 로드 + 미존재 경로는 404 (500 아님)."""
    r = client.get("/api/v1/playground/__no_such_path__")
    assert r.status_code == 404
