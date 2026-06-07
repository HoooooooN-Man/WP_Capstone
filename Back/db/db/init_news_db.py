# -*- coding: utf-8 -*-
"""news_data.duckdb 빈 스키마 생성 — Go webnews 파이프라인이 실행되지 않은
환경에서 /api/v1/news/* endpoint 503 회피용. 데모 / 개발 환경 한정."""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from pathlib import Path
import duckdb

DB = Path(__file__).parent / 'news_data.duckdb'
print(f'대상: {DB}')

con = duckdb.connect(str(DB))

# news_normalized — 뉴스 본문/감성
con.execute("""
CREATE TABLE IF NOT EXISTS news_normalized (
    news_id          VARCHAR PRIMARY KEY,
    title            VARCHAR,
    provider         VARCHAR,
    source_name      VARCHAR,
    query_text       VARCHAR,
    published_at     TIMESTAMP,
    fetched_at       TIMESTAMP,
    google_url       VARCHAR,
    origin_url       VARCHAR,
    image_url        VARCHAR,
    sentiment_label  VARCHAR,
    sentiment_score  REAL,
    pos_prob         REAL,
    neg_prob         REAL,
    neu_prob         REAL,
    category         VARCHAR,
    body_text        TEXT,
    summary          TEXT
)
""")

# news_rankings — 날짜별 랭킹 (news_id JOIN)
con.execute("""
CREATE TABLE IF NOT EXISTS news_rankings (
    display_date     DATE,
    news_id          VARCHAR,
    rank             INTEGER,
    ranking_score    REAL,
    category_id      VARCHAR,
    PRIMARY KEY (display_date, news_id)
)
""")

# webnews 일일 배치용 (webnews.py가 사용할 가능성)
con.execute("""
CREATE TABLE IF NOT EXISTS webnews_items (
    item_id          VARCHAR PRIMARY KEY,
    display_date     DATE,
    category         VARCHAR,
    title            VARCHAR,
    provider         VARCHAR,
    published_at     TIMESTAMP,
    summary          TEXT,
    body_text        TEXT,
    sentiment_label  VARCHAR,
    sentiment_score  REAL
)
""")

tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name").fetchall()
print(f'생성된 테이블: {[t[0] for t in tables]}')

# 헬스체크용 더미 1행 (display_date NULL 회피)
con.execute("""
INSERT OR IGNORE INTO news_rankings VALUES (CURRENT_DATE, '__placeholder__', 0, 0.0, 'general')
""")
con.execute("""
INSERT OR IGNORE INTO news_normalized VALUES ('__placeholder__','placeholder','placeholder','placeholder','',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, '', '', '', 'neutral', 0.0, 0.33, 0.33, 0.34, 'general', '', '')
""")

con.close()
print(f'OK · {DB.stat().st_size/1024:.1f} KB')
