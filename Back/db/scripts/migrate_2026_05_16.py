"""
migrate_2026_05_16.py
=====================
PostgreSQL schema migration — audit B 영역 3건을 단일 트랜잭션으로 적용.

  M#36: user_holdings.avg_price  INTEGER → NUMERIC(20,4)
        - 외국 종목 USD 소수점 대응 + int 머지 잘림 누적 방지.
        - quantity 는 그대로 INTEGER 유지 (자기 회사 종목은 정수).
  M#37: user_notes.tags 콤마조인 → 정규화 테이블 user_note_tags
        - 콤마 포함 태그 lossy, 200자 silent truncate 모두 해소.
        - 기존 row=0 이라 데이터 이관은 안전한 백업 SELECT 만.
  L#54: user_holdings hard-delete → soft delete + user_holdings_history
        - deleted_at TIMESTAMP NULL 컬럼.
        - user_holdings_history (action, snapshot JSONB, changed_at) audit trail.
        - app 측 핸들러도 함께 갱신.

idempotent — 이미 적용된 단계는 자동 스킵 (IF NOT EXISTS / column check).
--dry-run 모드는 트랜잭션을 ROLLBACK 으로 종료.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# .env 로드 + DB engine
BACK_DB_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACK_DB_DIR))
try:
    from dotenv import load_dotenv
    load_dotenv(BACK_DB_DIR / ".env")
except ImportError:
    pass

from db.database import engine  # noqa: E402
from sqlalchemy import text     # noqa: E402


def log(msg: str) -> None:
    print(msg, flush=True)


def column_type(con, table: str, column: str) -> str | None:
    row = con.execute(text("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = :t AND column_name = :c
    """), {"t": table, "c": column}).fetchone()
    return row[0] if row else None


def column_exists(con, table: str, column: str) -> bool:
    return column_type(con, table, column) is not None


def table_exists(con, table: str) -> bool:
    row = con.execute(text("""
        SELECT 1 FROM information_schema.tables WHERE table_name = :t
    """), {"t": table}).fetchone()
    return row is not None


# ── M#36: user_holdings.avg_price INTEGER → NUMERIC(20,4) ────────────────────

def migrate_avg_price(con) -> None:
    log("[M#36] user_holdings.avg_price → NUMERIC(20,4)")
    t = column_type(con, "user_holdings", "avg_price")
    if t is None:
        log("       ✗ user_holdings.avg_price column not found — skip")
        return
    if t == "numeric":
        log("       ✓ already NUMERIC — skip")
        return
    if t != "integer":
        log(f"       ⚠ unexpected current type: {t} — skip (manual review)")
        return
    log("       INTEGER → NUMERIC(20,4) ...")
    con.execute(text("""
        ALTER TABLE user_holdings
        ALTER COLUMN avg_price TYPE NUMERIC(20,4)
        USING avg_price::NUMERIC(20,4)
    """))
    log("       ✓ ALTER COLUMN applied")


# ── M#37: user_note_tags 정규화 + 콤마조인 컬럼 제거 ──────────────────────────

def migrate_notes_tags(con) -> None:
    log("[M#37] user_note_tags 정규화")
    if not table_exists(con, "user_note_tags"):
        log("       CREATE TABLE user_note_tags ...")
        con.execute(text("""
            CREATE TABLE user_note_tags (
                id        SERIAL PRIMARY KEY,
                note_id   INTEGER NOT NULL REFERENCES user_notes(id) ON DELETE CASCADE,
                tag_text  VARCHAR(30) NOT NULL,
                ordering  SMALLINT NOT NULL DEFAULT 0,
                UNIQUE (note_id, tag_text)
            )
        """))
        con.execute(text("CREATE INDEX idx_note_tags_note ON user_note_tags(note_id)"))
        con.execute(text("CREATE INDEX idx_note_tags_text ON user_note_tags(tag_text)"))
        log("       ✓ user_note_tags table created (with unique + 2 indexes)")
    else:
        log("       ✓ user_note_tags already exists — skip CREATE")

    # 기존 user_notes.tags (콤마조인) → user_note_tags 로 이관.
    if column_exists(con, "user_notes", "tags"):
        n = con.execute(text(
            "SELECT COUNT(*) FROM user_notes WHERE tags IS NOT NULL AND tags <> ''"
        )).scalar() or 0
        log(f"       legacy tags column 보유 행 = {n}")
        if n > 0:
            log("       legacy tags 이관 (regexp_split_to_table)")
            # 콤마/공백 분리, 트림, 빈 값 제거, 30자 절단, ordering = 원본 순서.
            con.execute(text("""
                INSERT INTO user_note_tags (note_id, tag_text, ordering)
                SELECT n.id,
                       SUBSTRING(TRIM(t.tag) FROM 1 FOR 30) AS tag_text,
                       t.ordering
                FROM user_notes n,
                     LATERAL unnest(string_to_array(n.tags, ',')) WITH ORDINALITY AS t(tag, ordering)
                WHERE n.tags IS NOT NULL
                  AND n.tags <> ''
                  AND TRIM(t.tag) <> ''
                ON CONFLICT (note_id, tag_text) DO NOTHING
            """))
            moved = con.execute(text("SELECT COUNT(*) FROM user_note_tags")).scalar() or 0
            log(f"       ✓ 이관 후 user_note_tags rows = {moved}")
        # 컬럼은 안전을 위해 즉시 DROP 하지 않고 RENAME 으로 박제 (legacy_tags).
        # 다음 마이그레이션에서 검증 후 DROP 가능.
        log("       RENAME tags → legacy_tags (안전 백업, 다음 사이클에서 DROP)")
        con.execute(text("ALTER TABLE user_notes RENAME COLUMN tags TO legacy_tags"))
    else:
        # 이미 RENAME / DROP 된 상태
        log("       ✓ user_notes.tags 컬럼 부재 (이미 마이그레이션 완료) — skip")


# ── L#54: user_holdings soft delete + audit history ───────────────────────────

def migrate_holdings_audit(con) -> None:
    log("[L#54] user_holdings soft delete + history")
    if not column_exists(con, "user_holdings", "deleted_at"):
        log("       ADD COLUMN deleted_at TIMESTAMP NULL")
        con.execute(text("ALTER TABLE user_holdings ADD COLUMN deleted_at TIMESTAMP NULL"))
        con.execute(text("CREATE INDEX idx_holding_deleted_at ON user_holdings(deleted_at) WHERE deleted_at IS NULL"))
        log("       ✓ deleted_at + partial index")
    else:
        log("       ✓ deleted_at 이미 존재 — skip")

    if not table_exists(con, "user_holdings_history"):
        log("       CREATE TABLE user_holdings_history")
        con.execute(text("""
            CREATE TABLE user_holdings_history (
                id          BIGSERIAL PRIMARY KEY,
                holding_id  INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                action      VARCHAR(20) NOT NULL,
                snapshot    JSONB NOT NULL,
                changed_at  TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        con.execute(text("CREATE INDEX idx_hold_hist_holding ON user_holdings_history(holding_id)"))
        con.execute(text("CREATE INDEX idx_hold_hist_user    ON user_holdings_history(user_id, changed_at DESC)"))
        log("       ✓ user_holdings_history + indexes")
    else:
        log("       ✓ user_holdings_history 이미 존재 — skip")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="트랜잭션 ROLLBACK")
    args = p.parse_args()
    log(f"engine: {engine.url}  mode={'DRY' if args.dry_run else 'WRITE'}")

    # 단일 트랜잭션 — 한 단계 실패 시 전체 롤백.
    with engine.connect() as con:
        trans = con.begin()
        try:
            migrate_avg_price(con)
            migrate_notes_tags(con)
            migrate_holdings_audit(con)
            if args.dry_run:
                trans.rollback()
                log("[DRY] ROLLBACK")
            else:
                trans.commit()
                log("[OK] COMMIT")
        except Exception as e:
            trans.rollback()
            log(f"[FAIL] rollback: {e}")
            raise


if __name__ == "__main__":
    main()
