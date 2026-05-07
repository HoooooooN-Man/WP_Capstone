"""
Back/db/tests/conftest.py
=========================
PostgreSQL 통합 테스트용 fixture (W1B Step 1).

운영 DB 와 분리된 *테스트 전용 DB* (`wp_capstone_test`) 에 init_db.sql 을 한 세션에
한 번 적용한다. PostgreSQL 서버가 부재하면 모든 PG 의존 테스트는 skip — CI 보호.

기본 URL: postgresql://postgres:postgres@localhost:5432/wp_capstone_test
오버라이드: PG_TEST_DATABASE_URL 환경변수.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest


_DB_ROOT = Path(__file__).resolve().parents[1]   # Back/db/
_BACK_ROOT = _DB_ROOT.parent                     # Back/

# pytest 가 self-inserted 한 Back/ 항목을 제거 (db 패키지 충돌 회피, test_watchlist 패턴).
sys.path[:] = [p for p in sys.path if Path(p).resolve() != _BACK_ROOT]
if str(_DB_ROOT) not in sys.path:
    sys.path.insert(0, str(_DB_ROOT))


PG_TEST_URL = os.getenv(
    "PG_TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/wp_capstone_test",
)


def _pg_available() -> bool:
    """PG 서버 + psycopg2 가용성 확인. 2초 timeout."""
    try:
        import psycopg2  # noqa: F401
        from sqlalchemy import create_engine
        eng = create_engine(
            PG_TEST_URL,
            isolation_level="AUTOCOMMIT",
            connect_args={"connect_timeout": 2},
        )
        with eng.connect():
            return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def pg_engine():
    """세션 단위 PG 엔진. 부재 시 skip."""
    if not _pg_available():
        pytest.skip("PostgreSQL test DB unreachable — set PG_TEST_DATABASE_URL")
    from sqlalchemy import create_engine
    return create_engine(PG_TEST_URL, future=True)


@pytest.fixture(scope="session", autouse=False)
def _apply_init_sql(pg_engine):
    """매 세션 시작 시 init_db.sql 을 fresh 적용. PG 의존 테스트가 자동 트리거."""
    sql_path = _DB_ROOT / "init_db.sql"
    if not sql_path.exists():
        pytest.skip("init_db.sql not found")

    with pg_engine.begin() as conn:
        # 의존 순서 무관하게 CASCADE 로 일괄 DROP.
        conn.exec_driver_sql("""
            DROP TABLE IF EXISTS impression_outcomes        CASCADE;
            DROP TABLE IF EXISTS recommendation_clicks      CASCADE;
            DROP TABLE IF EXISTS recommendation_impressions CASCADE;
            DROP TABLE IF EXISTS events_v1_meta             CASCADE;
            DROP TABLE IF EXISTS board_likes                CASCADE;
            DROP TABLE IF EXISTS board_comments             CASCADE;
            DROP TABLE IF EXISTS board_posts                CASCADE;
            DROP TABLE IF EXISTS notifications              CASCADE;
            DROP TABLE IF EXISTS user_watchlist             CASCADE;
            DROP TABLE IF EXISTS users                      CASCADE;
        """)
        sql_text = sql_path.read_text(encoding="utf-8")
        conn.exec_driver_sql(sql_text)


@pytest.fixture
def db_session(pg_engine, _apply_init_sql):
    """함수 단위 세션 — 종료 시 ROLLBACK 으로 격리."""
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=pg_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def sample_user(db_session):
    """기본 user 1명 — impression FK 테스트용."""
    from db.models import User

    nick = "evt_user_" + uuid.uuid4().hex[:8]
    user = User(
        email=f"{nick}@example.com",
        hashed_password="dummy",
        nickname=nick,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    yield user
    # 일부 테스트가 user 를 직접 delete 하므로 존재 여부 확인 후 정리.
    if db_session.query(User).filter_by(user_id=user.user_id).first() is not None:
        db_session.delete(user)
        db_session.commit()
