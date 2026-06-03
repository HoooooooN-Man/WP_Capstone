-- DuckDB schema proposal for the separate DuckDB owner.
-- This file is documentation-first: it is not wired into the Go runtime yet.

CREATE TABLE IF NOT EXISTS universe_kospi200 (
    as_of_date DATE,
    ticker VARCHAR,
    company_name_ko VARCHAR,
    company_name_en VARCHAR,
    aliases_json JSON,
    sector VARCHAR,
    is_active BOOLEAN,
    PRIMARY KEY (as_of_date, ticker)
);

CREATE TABLE IF NOT EXISTS raw_news (
    news_id VARCHAR PRIMARY KEY,
    provider VARCHAR NOT NULL,
    query_text VARCHAR,
    title VARCHAR NOT NULL,
    source_name VARCHAR,
    google_url VARCHAR,
    article_url VARCHAR,
    snippet VARCHAR,
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload_json JSON
);

CREATE TABLE IF NOT EXISTS news_normalized (
    news_id VARCHAR PRIMARY KEY,
    provider VARCHAR NOT NULL,
    query_text VARCHAR,
    title VARCHAR NOT NULL,
    title_norm VARCHAR NOT NULL,
    title_hash VARCHAR NOT NULL,
    source_name VARCHAR,
    google_url VARCHAR,
    article_url VARCHAR,
    snippet VARCHAR,
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL,
    sentiment_label VARCHAR,
    sentiment_score DOUBLE,
    used_for_ml BOOLEAN DEFAULT FALSE,
    used_for_digest BOOLEAN DEFAULT FALSE,
    extra_json JSON
);

CREATE TABLE IF NOT EXISTS news_company_map (
    news_id VARCHAR NOT NULL,
    ticker VARCHAR NOT NULL,
    company_name VARCHAR NOT NULL,
    match_type VARCHAR,
    match_score DOUBLE,
    PRIMARY KEY (news_id, ticker)
);

CREATE TABLE IF NOT EXISTS news_features_daily (
    trade_date DATE NOT NULL,
    ticker VARCHAR NOT NULL,
    news_count_1d INTEGER,
    pos_count_1d INTEGER,
    neg_count_1d INTEGER,
    neu_count_1d INTEGER,
    avg_sentiment_1d DOUBLE,
    weighted_sentiment_1d DOUBLE,
    after_close_news_count INTEGER,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (trade_date, ticker)
);

CREATE TABLE IF NOT EXISTS news_digest (
    digest_id VARCHAR PRIMARY KEY,
    digest_type VARCHAR NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    topic VARCHAR,
    summary_text VARCHAR NOT NULL,
    items_json JSON NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

-- Suggested ingestion pattern for the DuckDB owner:
-- 1) writer service flushes normalized micro-batches to JSON or Parquet spool files
-- 2) DuckDB owner loads files in bulk
-- 3) MERGE INTO / ON CONFLICT equivalent logic is applied around news_id and (title_hash, source_name, published_at)
