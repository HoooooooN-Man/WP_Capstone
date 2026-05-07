import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

from api.auth.auth import router as auth_router
from api.socket.internal_router import router as internal_router
from api.news.newsranking import router as news_router
from api.board.board import router as board_router
from api.users.users import router as users_router
from api.users.watchlist import router as watchlist_router
from api.users.cohort    import router as cohort_router
from api.events.events import router as events_router

load_dotenv()


# Tier 1B 4.4 (PRD §1.7): brute-force·스팸 방지 rate limiter.
# 클라이언트 IP 기준. 운영 환경에서는 X-Forwarded-For 등 신뢰 헤더 정책을 별도 결정.
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


def _parse_origins(env_value: str | None) -> list[str]:
    if not env_value:
        return []
    return [o.strip() for o in env_value.split(",") if o.strip()]


_DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
ALLOWED_ORIGINS = _parse_origins(os.getenv("CORS_ALLOW_ORIGINS")) or _DEFAULT_DEV_ORIGINS

app = FastAPI(title="Stock Analysis System")

# Rate limiter 등록 — slowapi 는 app.state.limiter 를 통해 데코레이터와 연결.
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """rate limit 초과 시 통일 에러 스키마로 응답 (PRD §1.3 호환)."""
    return JSONResponse(
        status_code=429,
        content={
            "code":       "RATE_LIMITED",
            "message":    f"요청이 너무 많습니다. 잠시 후 다시 시도해 주세요. (limit: {exc.detail})",
            "request_id": request.headers.get("X-Request-ID", ""),
        },
        headers={"Retry-After": "60"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(internal_router)
app.include_router(news_router)
app.include_router(board_router)
app.include_router(users_router)
app.include_router(watchlist_router)  # Tier 1.6 — /users/me/watchlist CRUD
app.include_router(cohort_router)     # W2C — /users/me/cohort GET·PUT
app.include_router(events_router)     # W1B — /events impressions·clicks·outcomes


@app.get("/")
def root():
    return {"message": "Server is running"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
