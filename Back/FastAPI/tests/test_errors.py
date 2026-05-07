"""
test_errors.py
==============
Tier 1.7 (PRD §1.3) — 통합 에러 응답 스키마 회귀 테스트.

검증 대상:
  - 모든 4xx/5xx 응답이 {code, message, request_id} 스키마를 따른다.
  - 모든 응답에 X-Request-ID 헤더가 부착된다.
  - 클라이언트가 X-Request-ID 를 보내면 그대로 echo 된다.
  - 기존 `raise HTTPException(detail=...)` 도 새 스키마로 자동 감싸진다.
  - AppError 가 의도한 code/status 로 노출된다.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, status

from Back.FastAPI.core.errors import AppError, ErrorCode


# ── 응답 스키마 자체 ─────────────────────────────────────────────────────────

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _assert_error_shape(body, expected_code: str | None = None):
    assert set(body.keys()) >= {"code", "message", "request_id"}, body
    assert isinstance(body["code"], str)
    assert isinstance(body["message"], str)
    assert UUID_RE.match(body["request_id"]), body["request_id"]
    if expected_code is not None:
        assert body["code"] == expected_code, body


def test_404_returns_unified_schema(client):
    r = client.get("/api/v1/nonexistent-endpoint")
    assert r.status_code == 404
    _assert_error_shape(r.json(), expected_code=ErrorCode.NOT_FOUND)
    assert r.headers.get("X-Request-ID")


def test_request_id_header_present_on_success(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert UUID_RE.match(r.headers.get("X-Request-ID", "")), r.headers


def test_request_id_echoed_when_provided(client):
    rid = "11111111-2222-3333-4444-555555555555"
    r = client.get("/health", headers={"X-Request-ID": rid})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == rid


def test_validation_error_returns_unified_schema(client):
    # top_k 의 ge=0/le=500 제약을 위반.
    r = client.get("/api/v1/stocks/recommendations?top_k=999")
    assert r.status_code == 422
    _assert_error_shape(r.json(), expected_code=ErrorCode.VALIDATION_FAILED)


# ── AppError 통합 ───────────────────────────────────────────────────────────
#
# 라우터 변경 없이 AppError 동작을 확인하기 위해, 테스트 전용 엔드포인트를
# 앱에 임시 등록한다 (test session 동안만).

def test_app_error_propagates_code_and_status(app, client):
    test_router = APIRouter()

    @test_router.get("/__test__/app-error")
    def _raise_app_error():
        raise AppError(
            ErrorCode.STOCK_NOT_FOUND,
            "삼성전자(005930) 점수 데이터를 찾지 못했습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    app.include_router(test_router)
    try:
        r = client.get("/__test__/app-error")
        assert r.status_code == 404
        body = r.json()
        _assert_error_shape(body, expected_code=ErrorCode.STOCK_NOT_FOUND)
        assert "삼성전자" in body["message"]
    finally:
        # 다른 테스트에 누수되지 않도록 라우트 제거.
        app.router.routes = [
            r for r in app.router.routes
            if getattr(r, "path", None) != "/__test__/app-error"
        ]
