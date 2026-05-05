# back/board/router.py
# WP_Capstone — P-07 커뮤니티 게시판 백엔드 (FastAPI)
# 포트 8001 기준. DB 연결은 .env 환경변수 사용

from __future__ import annotations

import os
from typing import Optional

import asyncpg
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

# Redis 세션 클라이언트 공유 (auth.py 와 동일 인스턴스 사용)
from api.auth.auth import rd

load_dotenv()

router = APIRouter(prefix="/api/v1/board", tags=["board"])

# ─────────────────────────────────────────────
# DB 연결 헬퍼
# ─────────────────────────────────────────────

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "capstone"),
            min_size=2,
            max_size=10,
        )
    return _pool


async def db() -> asyncpg.Connection:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


# ─────────────────────────────────────────────
# 세션 토큰 → author_id 검증 헬퍼
# Redis 의 session:{token} → email 을 조회하고
# PostgreSQL users 테이블에서 user_id 를 얻는다 (auth.py 와 동일한 토큰 체계).
# ─────────────────────────────────────────────

async def _email_from_session(session_token: Optional[str]) -> Optional[str]:
    if not session_token:
        return None
    try:
        return rd.get(f"session:{session_token}")
    except Exception:
        # Redis 연결 실패 시에도 401 처리 (가용성보다 보안 우선)
        return None


async def resolve_author(
    session_token: Optional[str],
    conn: asyncpg.Connection,
) -> Optional[int]:
    """세션 토큰 → user_id. 토큰이 없거나 만료되면 None."""
    email = await _email_from_session(session_token)
    if not email:
        return None
    return await conn.fetchval(
        "SELECT user_id FROM users WHERE email = $1", email
    )


async def require_auth(
    session_token: Optional[str],
    conn: asyncpg.Connection,
) -> int:
    """인증 필수 엔드포인트용. 토큰이 없으면 401, user 미존재면 401."""
    if not session_token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    email = await _email_from_session(session_token)
    if not email:
        raise HTTPException(status_code=401, detail="세션이 만료됐습니다. 다시 로그인해주세요.")
    user_id = await conn.fetchval(
        "SELECT user_id FROM users WHERE email = $1", email
    )
    if not user_id:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return int(user_id)


# ─────────────────────────────────────────────
# Pydantic 모델
# ─────────────────────────────────────────────

class PostCreate(BaseModel):
    ticker: str = Field(..., max_length=20)
    title: str = Field(..., max_length=255)
    content: str


class CommentCreate(BaseModel):
    post_id: int
    content: str


class LikeRequest(BaseModel):
    pass  # author_id는 세션 토큰에서


# ─────────────────────────────────────────────
# 인기 게시글 (전체 통합)
# GET /api/v1/board/popular
# 인기 점수 = likes*3 + comments*2 + views
# ─────────────────────────────────────────────

@router.get("/popular")
async def list_popular_posts(
    limit: int = Query(20, ge=1, le=100, description="가져올 게시글 수"),
    conn: asyncpg.Connection = Depends(db),
):
    rows = await conn.fetch(
        """
        SELECT
            p.id, p.ticker, p.author_id, p.title, p.views, p.likes,
            p.created_at,
            (SELECT COUNT(*) FROM board_comments c WHERE c.post_id = p.id) AS comment_count,
            (p.likes * 3
             + (SELECT COUNT(*) FROM board_comments c WHERE c.post_id = p.id) * 2
             + p.views) AS popularity
        FROM board_posts p
        ORDER BY popularity DESC, p.created_at DESC
        LIMIT $1
        """,
        limit,
    )
    items = [
        {
            "id":            r["id"],
            "ticker":        r["ticker"],
            "author_id":     r["author_id"],
            "title":         r["title"],
            "views":         r["views"],
            "likes":         r["likes"],
            "comment_count": r["comment_count"],
            "popularity":    r["popularity"],
            "created_at":    r["created_at"].isoformat(),
        }
        for r in rows
    ]
    return {"total": len(items), "items": items}


# ─────────────────────────────────────────────
# 게시글 목록 조회
# GET /api/v1/board/posts/{ticker}
# ─────────────────────────────────────────────

@router.get("/posts")
async def list_posts(
    ticker: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session_token: Optional[str] = Header(None, alias="session-token"),
    conn: asyncpg.Connection = Depends(db),
):
    author_id = await resolve_author(session_token, conn)
    offset = (page - 1) * page_size

    if ticker:
        # 1. 특정 티커 조회 시
        total = await conn.fetchval("SELECT COUNT(*) FROM board_posts WHERE ticker = $1", ticker)
        query = """
            SELECT p.id, p.ticker, p.author_id, p.title, p.views, p.likes, p.created_at,
                   (SELECT COUNT(*) FROM board_comments c WHERE c.post_id = p.id) AS comment_count,
                   CASE WHEN $3::int IS NOT NULL
                        THEN EXISTS(SELECT 1 FROM board_likes l WHERE l.post_id = p.id AND l.author_id = $3)
                        ELSE FALSE
                   END AS liked
            FROM board_posts p
            WHERE p.ticker = $1
            ORDER BY p.created_at DESC
            LIMIT $2 OFFSET $4
        """
        rows = await conn.fetch(query, ticker, page_size, author_id, offset)
    else:
        # 2. 전체 티커 조회 시 (ticker 파라미터가 없을 때)
        total = await conn.fetchval("SELECT COUNT(*) FROM board_posts")
        query = """
            SELECT p.id, p.ticker, p.author_id, p.title, p.views, p.likes, p.created_at,
                   (SELECT COUNT(*) FROM board_comments c WHERE c.post_id = p.id) AS comment_count,
                   CASE WHEN $2::int IS NOT NULL
                        THEN EXISTS(SELECT 1 FROM board_likes l WHERE l.post_id = p.id AND l.author_id = $2)
                        ELSE FALSE
                   END AS liked
            FROM board_posts p
            ORDER BY p.created_at DESC
            LIMIT $1 OFFSET $3
        """
        # 여기는 ticker가 없으므로 전달 인자 개수가 달라집니다.
        rows = await conn.fetch(query, page_size, author_id, offset)

    rows = await conn.fetch(
        """
        SELECT
            p.id, p.ticker, p.author_id, p.title, p.views, p.likes,
            p.created_at,
            (SELECT COUNT(*) FROM board_comments c WHERE c.post_id = p.id) AS comment_count,
            CASE WHEN $3::int IS NOT NULL
                 THEN EXISTS(SELECT 1 FROM board_likes l WHERE l.post_id = p.id AND l.author_id = $3)
                 ELSE FALSE
            END AS liked
        FROM board_posts p
        WHERE p.ticker = $1
        ORDER BY p.created_at DESC
        LIMIT $2 OFFSET $4
        """,
        ticker, page_size, author_id, offset,
    )

    items = [
        {
            "id": r["id"],
            "ticker": r["ticker"],
            "author_id": r["author_id"],
            "title": r["title"],
            "views": r["views"],
            "likes": r["likes"],
            "comment_count": r["comment_count"],
            "liked": r["liked"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ─────────────────────────────────────────────
# 게시글 상세 조회 (views +1)
# GET /api/v1/board/posts/detail/{post_id}
# ─────────────────────────────────────────────

@router.get("/posts/detail/{post_id}")
async def get_post(
    post_id: int,
    session_token: Optional[str] = Header(None, alias="session-token"),
    conn: asyncpg.Connection = Depends(db),
):
    author_id = await resolve_author(session_token, conn)

    row = await conn.fetchrow(
        "UPDATE board_posts SET views = views + 1 WHERE id = $1 RETURNING *",
        post_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    comments = await conn.fetch(
        "SELECT * FROM board_comments WHERE post_id = $1 ORDER BY created_at ASC",
        post_id,
    )

    liked = False
    if author_id:
        liked = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM board_likes WHERE post_id=$1 AND author_id=$2)",
            post_id, author_id,
        )

    return {
        "id": row["id"],
        "ticker": row["ticker"],
        "author_id": row["author_id"],
        "title": row["title"],
        "content": row["content"],
        "views": row["views"],
        "likes": row["likes"],
        "liked": liked,
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "comments": [
            {
                "id": c["id"],
                "author_id": c["author_id"],
                "content": c["content"],
                "created_at": c["created_at"].isoformat(),
            }
            for c in comments
        ],
    }


# ─────────────────────────────────────────────
# 게시글 작성
# POST /api/v1/board/posts
# ─────────────────────────────────────────────

@router.post("/posts", status_code=201)
async def create_post(
    body: PostCreate,
    session_token: Optional[str] = Header(None, alias="session-token"),
    conn: asyncpg.Connection = Depends(db),
):
    author_id = await require_auth(session_token, conn)

    row = await conn.fetchrow(
        """
        INSERT INTO board_posts (ticker, author_id, title, content)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        body.ticker, author_id, body.title, body.content,
    )
    return {
        "id": row["id"],
        "ticker": row["ticker"],
        "author_id": row["author_id"],
        "title": row["title"],
        "content": row["content"],
        "views": row["views"],
        "likes": row["likes"],
        "created_at": row["created_at"].isoformat(),
    }


# ─────────────────────────────────────────────
# 게시글 삭제 (작성자 본인만)
# DELETE /api/v1/board/posts/{post_id}
# ─────────────────────────────────────────────

@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    session_token: Optional[str] = Header(None, alias="session-token"),
    conn: asyncpg.Connection = Depends(db),
):
    author_id = await require_auth(session_token, conn)

    row = await conn.fetchrow(
        "SELECT author_id FROM board_posts WHERE id = $1", post_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
    if row["author_id"] != author_id:
        raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

    await conn.execute("DELETE FROM board_posts WHERE id = $1", post_id)
    return {"message": "삭제되었습니다."}


# ─────────────────────────────────────────────
# 댓글 작성
# POST /api/v1/board/comments
# ─────────────────────────────────────────────

@router.post("/comments", status_code=201)
async def create_comment(
    body: CommentCreate,
    session_token: Optional[str] = Header(None, alias="session-token"),
    conn: asyncpg.Connection = Depends(db),
):
    author_id = await require_auth(session_token, conn)

    exists = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM board_posts WHERE id = $1)", body.post_id
    )
    if not exists:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    row = await conn.fetchrow(
        """
        INSERT INTO board_comments (post_id, author_id, content)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        body.post_id, author_id, body.content,
    )
    return {
        "id": row["id"],
        "post_id": row["post_id"],
        "author_id": row["author_id"],
        "content": row["content"],
        "created_at": row["created_at"].isoformat(),
    }


# ─────────────────────────────────────────────
# 좋아요 토글
# POST /api/v1/board/posts/{post_id}/like
# ─────────────────────────────────────────────

@router.post("/posts/{post_id}/like")
async def toggle_like(
    post_id: int,
    session_token: Optional[str] = Header(None, alias="session-token"),
    conn: asyncpg.Connection = Depends(db),
):
    author_id = await require_auth(session_token, conn)

    exists = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM board_posts WHERE id = $1)", post_id
    )
    if not exists:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    already = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM board_likes WHERE post_id=$1 AND author_id=$2)",
        post_id, author_id,
    )

    async with conn.transaction():
        if already:
            await conn.execute(
                "DELETE FROM board_likes WHERE post_id=$1 AND author_id=$2",
                post_id, author_id,
            )
            await conn.execute(
                "UPDATE board_posts SET likes = GREATEST(0, likes - 1) WHERE id = $1",
                post_id,
            )
            liked = False
        else:
            await conn.execute(
                "INSERT INTO board_likes (post_id, author_id) VALUES ($1, $2)",
                post_id, author_id,
            )
            await conn.execute(
                "UPDATE board_posts SET likes = likes + 1 WHERE id = $1",
                post_id,
            )
            liked = True

    likes = await conn.fetchval(
        "SELECT likes FROM board_posts WHERE id = $1", post_id
    )
    return {"liked": liked, "likes": likes}