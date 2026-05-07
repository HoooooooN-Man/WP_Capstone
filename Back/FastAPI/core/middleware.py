"""
core/middleware.py
==================
공통 미들웨어. PRD v1.2 §1.3 / 캡스톤 Tier 1.7.

`RequestIDMiddleware`
  - 모든 요청에 UUID4 request_id 부여 → request.state.request_id 에 저장.
  - 응답 헤더 X-Request-ID 로 회수 (에러 토스트 디버깅·로그 상관에 사용).
  - 클라이언트가 X-Request-ID 헤더를 보내오면 그대로 사용 (분산 추적용).
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_HEADER_NAME = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get(_HEADER_NAME) or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        # 핸들러가 이미 헤더를 박아놨다면 덮어쓰지 않음.
        response.headers.setdefault(_HEADER_NAME, rid)
        return response
