import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

DB_USER = os.getenv("DB_USER")
DB_PW = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

if not all([DB_USER, DB_PW, DB_HOST, DB_PORT, DB_NAME]):
    raise RuntimeError(
        f"DB env 누락: DB_USER={DB_USER}, DB_HOST={DB_HOST}, DB_PORT={DB_PORT}, DB_NAME={DB_NAME}, "
        f"env_path={ENV_PATH}"
    )

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# 한국어 Windows(CP949) 호스트에서 PostgreSQL 메시지가 CP949 로 인코딩돼 들어와
# psycopg2 의 UTF-8 디코드가 실패하는 문제를 방지. 모든 통신을 UTF-8 로 고정.
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"client_encoding": "utf8"})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """SQLAlchemy 세션 생성 — 핸들러 예외 시 rollback 으로 dirty 세션 누수를 막는다.

    이전엔 예외가 try 블록 밖으로 빠져나가는 경우 commit 전 변경사항이 다음 요청에서
    이 세션을 재사용할 때 (커넥션 풀) 자동 commit 되거나 잠금이 남는 위험.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def _resolve_duckdb_path() -> str:
    """DuckDB 경로를 env → 기본(repo-relative) 순으로 해석.

    이전엔 default 가 `E:\\Capstone Data\\...` 절대경로 — 다른 머신에서 503.
    이제 env 가 비어 있으면 `<repo>/project_data/db/market_data.duckdb` 를 시도,
    그래도 없으면 호출 시점에 RuntimeError 로 명확히 실패 (silent 503 회피).
    """
    env_path = os.getenv("DUCKDB_PATH")
    if env_path:
        return env_path
    # repo root = Back/db/db/database.py → parents[3]
    repo_default = Path(__file__).resolve().parents[3] / "project_data" / "db" / "market_data.duckdb"
    return str(repo_default)


DB_PATH = _resolve_duckdb_path()


def get_duckdb():
    if not Path(DB_PATH).exists():
        raise RuntimeError(
            f"DuckDB 파일 없음: {DB_PATH}. DUCKDB_PATH 환경변수를 .env 에 설정하거나 "
            f"project_data/db/market_data.duckdb 에 파일을 배치하세요."
        )
    conn = duckdb.connect(DB_PATH, read_only=False)
    try:
        yield conn
    finally:
        conn.close()