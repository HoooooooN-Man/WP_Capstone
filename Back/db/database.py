import duckdb
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
# PostgreSQL 설정
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PW = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# DuckDB 설정 (read_only 옵션 고려)
DB_PATH = 'server/stock_analysis.duckdb'

def get_duckdb():
    # 분석용으로만 쓴다면 read_only=True를 주는 것이 동시성 관리면에서 안전합니다.
    # 만약 서버에서 DuckDB에 데이터를 계속 써야 한다면 read_only=False(기본값)로 두세요.
    conn = duckdb.connect(DB_PATH, read_only=False) 
    try:
        yield conn
    finally:
        conn.close()