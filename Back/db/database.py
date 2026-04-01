import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent
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

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DB_PATH = "server/stock_analysis.duckdb"

def get_duckdb():
    conn = duckdb.connect(DB_PATH, read_only=False)
    try:
        yield conn
    finally:
        conn.close()