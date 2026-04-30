"""
routers/board.py
================
종목 토론방 API (SQLite OLTP 레이어).

[이중 DB 아키텍처]
  DuckDB  → OLAP (ML 스코어 · 가격 · 재무 분석)   — services/data.py
  SQLite  → OLTP (게시글 · 댓글 · 좋아요 트랜잭션) — services/board_db.py

엔드포인트 7개
  GET  /board/posts/{ticker}              게시글 목록 (페이지네이션)
  POST /board/posts                       게시글 작성
  GET  /board/posts/detail/{post_id}      게시글 상세 (조회수 +1)
  DEL  /board/posts/{post_id}             게시글 삭제 (본인 검증)
  POST /board/comments                    댓글 작성
  GET  /board/comments/{post_id}          댓글 목록
  POST /board/posts/{post_id}/like        좋아요 토글
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..services import board_db as svc
from ..schemas.board import (
    PostCreate, PostSummary, PostDetail,
    PostListResponse, DeleteResponse,
    CommentCreate, CommentItem, CommentListResponse,
    LikeResponse,
)

router = APIRouter(prefix="/board", tags=["board"])


# ── 인기 게시글 (전체 종목 통합) ──────────────────────────────────────────────

@router.get(
    "/popular",
    summary="전체 인기 게시글 (좋아요·댓글·조회수 종합 정렬)",
)
def list_popular_posts(
    limit: int = Query(20, ge=1, le=100, description="가져올 게시글 수"),
):
    """
    종목 구분 없이 **전체 게시글 중 인기순** Top N을 반환합니다.

    인기 점수 = `likes×3 + comments×2 + views`
    """
    items = svc.db_list_popular_posts(limit=limit)
    return {"total": len(items), "items": items}


# ── 게시글 목록 ────────────────────────────────────────────────────────────────

@router.get(
    "/posts/{ticker}",
    response_model=PostListResponse,
    summary="종목 게시글 목록 조회 (페이지네이션)",
)
def list_posts(
    ticker:    str,
    page:      int = Query(1,  ge=1,  description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 게시글 수"),
):
    """
    특정 종목의 게시글 목록을 **최신순**으로 반환합니다.

    - 제목·작성자·조회수·좋아요 수·**댓글 수** 포함
    - `page` / `page_size` 파라미터로 페이지네이션
    """
    items_raw, total = svc.db_list_posts(
        ticker=ticker.upper(), page=page, page_size=page_size
    )
    items = [PostSummary(**r) for r in items_raw]
    return PostListResponse(
        ticker=ticker.upper(),
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


# ── 게시글 작성 ────────────────────────────────────────────────────────────────

@router.post(
    "/posts",
    response_model=PostDetail,
    status_code=201,
    summary="게시글 작성",
)
def create_post(body: PostCreate):
    """
    새 게시글을 작성합니다.

    - `ticker`: 종목 코드 (예: `005930`)
    - `author_id`: 작성자 식별자 (추후 JWT 토큰에서 추출로 교체 예정)
    """
    row = svc.db_create_post(
        ticker=body.ticker.upper(),
        author_id=body.author_id,
        title=body.title,
        content=body.content,
    )
    row.setdefault("comment_count", 0)
    return PostDetail(**row)


# ── 게시글 상세 조회 ───────────────────────────────────────────────────────────

@router.get(
    "/posts/detail/{post_id}",
    response_model=PostDetail,
    summary="게시글 상세 조회 (조회수 +1)",
)
def get_post(post_id: int):
    """
    게시글 본문을 포함한 상세 정보를 반환합니다.
    호출할 때마다 **조회수(views)가 1 증가**합니다.
    """
    row = svc.db_get_post(post_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"post_id={post_id} 가 존재하지 않습니다.")
    return PostDetail(**row)


# ── 게시글 삭제 ────────────────────────────────────────────────────────────────

@router.delete(
    "/posts/{post_id}",
    response_model=DeleteResponse,
    summary="게시글 삭제 (본인 검증)",
)
def delete_post(
    post_id:   int,
    author_id: str = Query(..., description="삭제 요청자 ID (본인 확인용)"),
):
    """
    게시글을 삭제합니다. **본인(author_id)이 작성한 글만** 삭제 가능합니다.
    삭제 시 연결된 댓글 · 좋아요도 CASCADE 삭제됩니다.

    - 403: 작성자 불일치
    - 404: 게시글 없음
    """
    try:
        deleted = svc.db_delete_post(post_id=post_id, author_id=author_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not deleted:
        raise HTTPException(status_code=404, detail=f"post_id={post_id} 가 존재하지 않습니다.")

    return DeleteResponse(post_id=post_id, deleted=True)


# ── 댓글 작성 ─────────────────────────────────────────────────────────────────

@router.post(
    "/comments",
    response_model=CommentItem,
    status_code=201,
    summary="댓글 작성",
)
def create_comment(body: CommentCreate):
    """
    특정 게시글에 댓글을 작성합니다.

    - `post_id`: 대상 게시글 ID
    - `author_id`: 작성자 식별자
    """
    try:
        row = svc.db_create_comment(
            post_id=body.post_id,
            author_id=body.author_id,
            content=body.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return CommentItem(**row)


# ── 댓글 목록 ─────────────────────────────────────────────────────────────────

@router.get(
    "/comments/{post_id}",
    response_model=CommentListResponse,
    summary="댓글 목록 조회",
)
def list_comments(post_id: int):
    """
    해당 게시글의 댓글을 **작성 순서대로** 반환합니다.
    """
    items_raw = svc.db_list_comments(post_id)
    items = [CommentItem(**r) for r in items_raw]
    return CommentListResponse(post_id=post_id, total=len(items), items=items)


# ── 좋아요 토글 ────────────────────────────────────────────────────────────────

@router.post(
    "/posts/{post_id}/like",
    response_model=LikeResponse,
    summary="좋아요 토글 (누르면 +1, 다시 누르면 -1)",
)
def toggle_like(
    post_id:   int,
    author_id: str = Query(..., description="좋아요 요청자 ID"),
):
    """
    게시글 좋아요를 **토글**합니다.

    | 상태 | 결과 |
    |------|------|
    | 아직 좋아요 안 함 | +1, `liked=true` 반환 |
    | 이미 좋아요 함    | -1, `liked=false` 반환 |

    동일 사용자의 중복 좋아요는 DB 레벨(PRIMARY KEY)에서 차단됩니다.
    """
    try:
        result = svc.db_toggle_like(post_id=post_id, author_id=author_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return LikeResponse(
        post_id=post_id,
        author_id=author_id,
        liked=result["liked"],
        likes=result["likes"],
    )
