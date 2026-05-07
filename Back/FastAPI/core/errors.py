"""
core/errors.py
==============
통합 에러 응답 스키마 + 글로벌 예외 핸들러.

PRD v1.2 §1.3 / 캡스톤 Tier 1.7.

응답 형식:
    {
      "code":       "STOCK_NOT_FOUND",
      "message":    "사용자에게 표시할 메시지",
      "request_id": "uuid"
    }

라우터는 다음 두 가지 방식 중 하나로 에러를 발생시킨다:
  1) `raise AppError("STOCK_NOT_FOUND", "...", status_code=404)` — 권장.
  2) 기존 `raise HTTPException(status_code=..., detail="...")` — 글로벌 핸들러가
     자동으로 `code="HTTP_<status>"` 로 감싼다 (점진 마이그레이션 안전망).
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    """모든 4xx/5xx 응답이 따르는 스키마."""
    code:       str
    message:    str
    request_id: str


class AppError(Exception):
    """애플리케이션 정의 예외 — 글로벌 핸들러가 ErrorResponse 로 변환한다."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


# ── 자주 쓰일 코드 상수 (필요 시 라우터에서 import) ─────────────────────────────

class ErrorCode:
    # 4xx
    BAD_REQUEST            = "BAD_REQUEST"
    VALIDATION_FAILED      = "VALIDATION_FAILED"
    UNAUTHORIZED           = "UNAUTHORIZED"
    FORBIDDEN              = "FORBIDDEN"
    NOT_FOUND              = "NOT_FOUND"
    STOCK_NOT_FOUND        = "STOCK_NOT_FOUND"
    DATE_NOT_AVAILABLE     = "DATE_NOT_AVAILABLE"
    MODEL_NOT_AVAILABLE    = "MODEL_NOT_AVAILABLE"
    RATE_LIMITED           = "RATE_LIMITED"
    # 5xx
    INTERNAL_ERROR         = "INTERNAL_ERROR"
    DATA_UNAVAILABLE       = "DATA_UNAVAILABLE"   # DuckDB 미초기화 등 일시적 503
    UPSTREAM_ERROR         = "UPSTREAM_ERROR"


def _request_id(request: Request) -> str:
    """RequestIDMiddleware 가 채워둔 id 를 꺼내거나, 없으면 새로 생성."""
    rid: Optional[str] = getattr(request.state, "request_id", None)
    return rid or str(uuid.uuid4())


def _json_error(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    rid = _request_id(request)
    body = ErrorResponse(code=code, message=message, request_id=rid).model_dump()
    return JSONResponse(
        status_code=status_code,
        content=body,
        headers={"X-Request-ID": rid},
    )


# ── 핸들러 본체 ────────────────────────────────────────────────────────────────

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _json_error(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    기존 `raise HTTPException(detail=...)` 코드를 새 스키마로 자동 감싼다.
    detail 이 dict 면 그 안의 code 를 우선 채택, 아니면 status code 기반 기본 코드.
    """
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        code = str(detail["code"])
        message = str(detail["message"])
    else:
        code = _default_code_for_status(exc.status_code)
        message = str(detail) if detail is not None else ""
    return _json_error(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # pydantic 검증 실패는 한 줄 요약만 사용자에게 노출하고, 상세는 로그로.
    errors = exc.errors()
    summary = errors[0].get("msg", "Validation failed") if errors else "Validation failed"
    logger.info("validation_failed", extra={"errors": errors})
    return _json_error(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code=ErrorCode.VALIDATION_FAILED,
        message=summary,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 마지막 보루. 사용자에게는 코드만, 로그에는 트레이스백.
    logger.exception("unhandled_exception", extra={"path": str(request.url)})
    return _json_error(
        request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code=ErrorCode.INTERNAL_ERROR,
        message="서버 내부 오류가 발생했습니다.",
    )


def _default_code_for_status(status_code: int) -> str:
    if status_code == 400: return ErrorCode.BAD_REQUEST
    if status_code == 401: return ErrorCode.UNAUTHORIZED
    if status_code == 403: return ErrorCode.FORBIDDEN
    if status_code == 404: return ErrorCode.NOT_FOUND
    if status_code == 422: return ErrorCode.VALIDATION_FAILED
    if status_code == 429: return ErrorCode.RATE_LIMITED
    if status_code == 503: return ErrorCode.DATA_UNAVAILABLE
    return f"HTTP_{status_code}"


def register_exception_handlers(app: FastAPI) -> None:
    """main.py 에서 한 번 호출."""
    app.add_exception_handler(AppError,                  app_error_handler)
    app.add_exception_handler(StarletteHTTPException,    http_exception_handler)
    app.add_exception_handler(RequestValidationError,    validation_exception_handler)
    app.add_exception_handler(Exception,                 unhandled_exception_handler)
