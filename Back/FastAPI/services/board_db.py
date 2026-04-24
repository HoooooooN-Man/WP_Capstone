"""
services/board_db.py
====================
종목 토론방 SQLite 레이어.

[이중 DB 아키텍처 설계 근거]
- DuckDB  : OLAP 특화 → ML 스코어 · 가격 · 재무 분석 (컬럼 스토리지, 벡터 실행)
- SQLite  : OLTP 특화 → 게시글 · 댓글 · 좋아요 (행 단위 트랜잭션, WAL 모드로 동시 읽기)

SQLite WAL(Write-Ahead Logging) 모드를 사용해
다수의 읽기 요청이 단일 쓰기 트랜잭션을 블로킹하지 않도록 설계.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator

from ..core.config import BOARD_DB_PATH

# ── 연결 풀 (thread-local) ────────────────────────────────────────────────────
_local = threading.local()

DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 게시글
CREATE TABLE IF NOT EXISTS posts (
    post_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker     TEXT    NOT NULL,
    author_id  TEXT    NOT NULL,
    title      TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    views      INTEGER NOT NULL DEFAULT 0,
    likes      INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_posts_ticker ON posts(ticker, created_at DESC);

-- 댓글
CREATE TABLE IF NOT EXISTS comments (
    comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id    INTEGER NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    author_id  TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);

-- 좋아요 (중복 방지 + 토글용)
CREATE TABLE IF NOT EXISTS post_likes (
    post_id   INTEGER NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    author_id TEXT    NOT NULL,
    PRIMARY KEY (post_id, author_id)
);
"""


def init_board_db() -> None:
    """앱 시작 시 한 번 호출 — DB 파일·테이블·인덱스 생성."""
    BOARD_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(BOARD_DB_PATH))
    con.executescript(DDL)
    con.commit()
    con.close()


def _get_con() -> sqlite3.Connection:
    """Thread-local SQLite 연결 반환 (check_same_thread=False + row_factory)."""
    if not hasattr(_local, "con") or _local.con is None:
        _local.con = sqlite3.connect(
            str(BOARD_DB_PATH),
            check_same_thread=False,
        )
        _local.con.row_factory = sqlite3.Row
        _local.con.execute("PRAGMA journal_mode=WAL")
        _local.con.execute("PRAGMA foreign_keys=ON")
    return _local.con


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """요청 범위 DB 컨텍스트 — 예외 시 자동 rollback, 정상 시 commit."""
    con = _get_con()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise


# ── Posts ─────────────────────────────────────────────────────────────────────

def db_list_posts(
    ticker: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """종목 게시글 목록 + 전체 건수 (페이지네이션)."""
    offset = (page - 1) * page_size
    with get_db() as con:
        total = con.execute(
            "SELECT COUNT(*) FROM posts WHERE ticker = ?", (ticker,)
        ).fetchone()[0]

        rows = con.execute(
            """
            SELECT
                p.post_id, p.ticker, p.author_id, p.title,
                p.views, p.likes, p.created_at,
                (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count
            FROM posts p
            WHERE p.ticker = ?
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (ticker, page_size, offset),
        ).fetchall()

    return [dict(r) for r in rows], total


def db_create_post(
    ticker: str,
    author_id: str,
    title: str,
    content: str,
) -> dict:
    """게시글 생성 → 생성된 레코드 반환."""
    with get_db() as con:
        cur = con.execute(
            """
            INSERT INTO posts (ticker, author_id, title, content)
            VALUES (?, ?, ?, ?)
            """,
            (ticker, author_id, title, content),
        )
        post_id = cur.lastrowid
        row = con.execute(
            "SELECT * FROM posts WHERE post_id = ?", (post_id,)
        ).fetchone()
    return dict(row)


def db_get_post(post_id: int) -> dict | None:
    """게시글 상세 조회 + 조회수 +1."""
    with get_db() as con:
        con.execute(
            "UPDATE posts SET views = views + 1 WHERE post_id = ?", (post_id,)
        )
        row = con.execute(
            """
            SELECT
                p.*,
                (SELECT COUNT(*) FROM comments c WHERE c.post_id = p.post_id) AS comment_count
            FROM posts p
            WHERE p.post_id = ?
            """,
            (post_id,),
        ).fetchone()
    return dict(row) if row else None


def db_delete_post(post_id: int, author_id: str) -> bool:
    """본인 글만 삭제 가능. 삭제 성공 여부 반환."""
    with get_db() as con:
        # 소유자 확인
        row = con.execute(
            "SELECT author_id FROM posts WHERE post_id = ?", (post_id,)
        ).fetchone()
        if row is None:
            return False
        if row["author_id"] != author_id:
            raise PermissionError("본인 게시글만 삭제할 수 있습니다.")
        con.execute("DELETE FROM posts WHERE post_id = ?", (post_id,))
    return True


# ── Comments ──────────────────────────────────────────────────────────────────

def db_create_comment(
    post_id: int,
    author_id: str,
    content: str,
) -> dict:
    """댓글 작성 → 생성된 레코드 반환."""
    with get_db() as con:
        # 게시글 존재 확인
        if not con.execute(
            "SELECT 1 FROM posts WHERE post_id = ?", (post_id,)
        ).fetchone():
            raise ValueError(f"post_id={post_id} 가 존재하지 않습니다.")
        cur = con.execute(
            "INSERT INTO comments (post_id, author_id, content) VALUES (?, ?, ?)",
            (post_id, author_id, content),
        )
        row = con.execute(
            "SELECT * FROM comments WHERE comment_id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


def db_list_comments(post_id: int) -> list[dict]:
    """게시글의 댓글 목록 (오래된 순)."""
    with get_db() as con:
        rows = con.execute(
            "SELECT * FROM comments WHERE post_id = ? ORDER BY created_at ASC",
            (post_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Likes ─────────────────────────────────────────────────────────────────────

def db_toggle_like(post_id: int, author_id: str) -> dict:
    """
    좋아요 토글.
    - 처음 누르면 post_likes 에 삽입 + posts.likes +1
    - 다시 누르면 post_likes 에서 삭제 + posts.likes -1
    반환: {"liked": bool, "likes": int}
    """
    with get_db() as con:
        # 게시글 존재 확인
        if not con.execute(
            "SELECT 1 FROM posts WHERE post_id = ?", (post_id,)
        ).fetchone():
            raise ValueError(f"post_id={post_id} 가 존재하지 않습니다.")

        existing = con.execute(
            "SELECT 1 FROM post_likes WHERE post_id=? AND author_id=?",
            (post_id, author_id),
        ).fetchone()

        if existing:
            # 좋아요 취소
            con.execute(
                "DELETE FROM post_likes WHERE post_id=? AND author_id=?",
                (post_id, author_id),
            )
            con.execute(
                "UPDATE posts SET likes = MAX(0, likes - 1) WHERE post_id=?",
                (post_id,),
            )
            liked = False
        else:
            # 좋아요 추가
            con.execute(
                "INSERT INTO post_likes (post_id, author_id) VALUES (?, ?)",
                (post_id, author_id),
            )
            con.execute(
                "UPDATE posts SET likes = likes + 1 WHERE post_id=?",
                (post_id,),
            )
            liked = True

        likes = con.execute(
            "SELECT likes FROM posts WHERE post_id=?", (post_id,)
        ).fetchone()[0]

    return {"liked": liked, "likes": likes}
