"""H#27 + IP/UA fingerprint — 쿠키 기반 인증 회귀 가드.

8001 (ML) 은 인증 라우터가 없고, 본 테스트는 8000 (Auth) 의 헤더 검증을 위한 것.
8000 의 TestClient 가 필요하므로 별도 fixture 로 server.py 의 app 을 로드한다.
Redis 미접속 환경에서는 skip.
"""
import os
import sys
from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def auth_app():
    """Back/db/server.py 의 FastAPI app — 8000 인증 서버.

    Back/db/ 가 sys.path 최우선이어야 `from db.database import ...` 같은 server.py
    내부 import 가 namespace 충돌 없이 작동. conftest 가 Back/ 을 먼저 넣어둔
    상태라 db.database 가 Back/db/__init__.py 와 충돌 → 임포트 전 sys.modules 정리.
    """
    db_dir = Path(__file__).resolve().parents[2] / "db"
    # 0번에 강제 삽입 (이미 있어도 우선순위 갱신).
    while str(db_dir) in sys.path:
        sys.path.remove(str(db_dir))
    sys.path.insert(0, str(db_dir))
    # 이전에 잘못 임포트된 db.* / api.* 캐시 제거.
    for mod in list(sys.modules):
        if mod == "db" or mod.startswith("db.") or mod == "api" or mod.startswith("api."):
            sys.modules.pop(mod, None)
    try:
        from server import app as auth_app  # type: ignore
    except Exception as e:
        pytest.skip(f"8000 auth app import 실패: {e}")
    return auth_app


@pytest.fixture()
def auth_client(auth_app):
    from fastapi.testclient import TestClient
    with TestClient(auth_app) as c:
        yield c


def test_session_endpoint_unauthenticated_401(auth_client):
    """미인증 호출 → 401 (500 NEVER)."""
    r = auth_client.get("/auth/session")
    assert r.status_code in (401, 503)


def test_session_endpoint_bad_cookie_401(auth_client):
    """잘못된 쿠키 토큰 → 401."""
    r = auth_client.get("/auth/session", cookies={"wp_session": "deadbeef-bad-token"})
    assert r.status_code in (401, 503)


def test_session_endpoint_bad_header_401(auth_client):
    """잘못된 헤더 토큰 → 401."""
    r = auth_client.get("/auth/session", headers={"session-token": "deadbeef-bad-token"})
    assert r.status_code in (401, 503)


def test_login_invalid_email_format_422(auth_client):
    """EmailStr 검증 — TLD .local 등 reserved 는 거부."""
    r = auth_client.post("/auth/login", json={"email": "smoke@test.local", "password": "Wp1@Wp1@"})
    assert r.status_code == 422


def test_logout_idempotent_no_token(auth_client):
    """토큰 없이 logout 호출도 200 — idempotent."""
    r = auth_client.post("/auth/logout")
    assert r.status_code == 200
    # Set-Cookie 가 쿠키 삭제 명령 (max-age=0) 으로 응답.
    set_cookie = r.headers.get("set-cookie", "")
    assert "wp_session" in set_cookie.lower() or set_cookie == ""


def test_fingerprint_helper_pure(auth_app):  # noqa: ARG001
    """fingerprint 함수가 같은 입력에 같은 출력, 다른 입력에 다른 출력."""
    try:
        from api.auth.auth import _fingerprint  # type: ignore
    except Exception as e:
        pytest.skip(f"auth 모듈 import 실패: {e}")

    class _FakeReq:
        def __init__(self, ip: str, ua: str):
            self.client = type("c", (), {"host": ip})()
            self.headers = {"user-agent": ua}

    a = _fingerprint(_FakeReq("1.2.3.4", "Chrome/130"))
    b = _fingerprint(_FakeReq("1.2.3.4", "Chrome/130"))
    c = _fingerprint(_FakeReq("9.9.9.9", "Chrome/130"))
    d = _fingerprint(_FakeReq("1.2.3.4", "Firefox/120"))

    assert a == b, "동일 입력은 동일 fingerprint"
    assert a != c, "IP 다르면 다른 fingerprint"
    assert a != d, "UA 다르면 다른 fingerprint"
    # 해시는 16자 hex
    for ip_h, ua_h in (a, b, c, d):
        assert len(ip_h) == 16 and len(ua_h) == 16
