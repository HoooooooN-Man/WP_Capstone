-- ─────────────────────────────────────────────────────────────────────────
-- wp_capstone — PostgreSQL 초기 스키마
-- 회원가입 / 로그인 / 게시판 / 포트폴리오(관심종목) / 알림
-- ─────────────────────────────────────────────────────────────────────────

-- 1) users — 회원
CREATE TABLE IF NOT EXISTS users (
    user_id           SERIAL          PRIMARY KEY,
    email             VARCHAR(255)    NOT NULL UNIQUE,
    hashed_password   VARCHAR(255)    NOT NULL,
    nickname          VARCHAR(50)     NOT NULL UNIQUE,
    is_active         BOOLEAN         DEFAULT TRUE,
    is_verified       BOOLEAN         DEFAULT FALSE,
    created_at        TIMESTAMPTZ     DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_nickname ON users(nickname);

-- W2 — cohort 컬럼. NULL 허용 (미선택 = balanced 와 동치).
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS cohort VARCHAR(20);

-- 2) user_watchlist — 사용자 관심 종목 (포트폴리오)
CREATE TABLE IF NOT EXISTS user_watchlist (
    id          SERIAL          PRIMARY KEY,
    user_id     INTEGER         REFERENCES users(user_id) ON DELETE CASCADE,
    ticker      VARCHAR(20)     NOT NULL,
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    -- P0-3 (PRD §8.1) — 관심종목 그룹 분류. UNIQUE 제약은 (user, ticker, group) 조합으로 변경.
    group_name  VARCHAR(50)     NOT NULL DEFAULT 'default'
);

-- 기존 환경 마이그레이션 — UNIQUE(user, ticker) 가 있다면 제거하고 group 포함 제약으로 교체.
ALTER TABLE user_watchlist
    ADD COLUMN IF NOT EXISTS group_name VARCHAR(50) NOT NULL DEFAULT 'default';
ALTER TABLE user_watchlist DROP CONSTRAINT IF EXISTS user_watchlist_user_id_ticker_key;
ALTER TABLE user_watchlist DROP CONSTRAINT IF EXISTS uq_watch_user_ticker;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_watch_user_ticker_group'
    ) THEN
        ALTER TABLE user_watchlist
            ADD CONSTRAINT uq_watch_user_ticker_group UNIQUE (user_id, ticker, group_name);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_watch_user   ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watch_ticker ON user_watchlist(ticker);
CREATE INDEX IF NOT EXISTS idx_watch_group  ON user_watchlist(user_id, group_name);

-- 2-1) user_holdings — 사용자 보유 종목 (PRD §3.6 신규)
CREATE TABLE IF NOT EXISTS user_holdings (
    id          SERIAL          PRIMARY KEY,
    user_id     INTEGER         REFERENCES users(user_id) ON DELETE CASCADE NOT NULL,
    ticker      VARCHAR(20)     NOT NULL,
    quantity    INTEGER         NOT NULL DEFAULT 0,
    avg_price   INTEGER         NOT NULL DEFAULT 0,
    bought_at   DATE,
    memo        VARCHAR(200),
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_holding_user   ON user_holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holding_ticker ON user_holdings(ticker);

-- 3) notifications — 사용자 알림 (긍정/부정 뉴스 트리거)
CREATE TABLE IF NOT EXISTS notifications (
    id              SERIAL          PRIMARY KEY,
    user_id         INTEGER         REFERENCES users(user_id) ON DELETE CASCADE,
    ticker          VARCHAR(20)     NOT NULL,
    title           TEXT            NOT NULL,
    sentiment_label VARCHAR(20),
    is_read         BOOLEAN         DEFAULT FALSE,
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_notif_user_unread
    ON notifications(user_id, is_read);

-- 4) board_posts — 게시글
CREATE TABLE IF NOT EXISTS board_posts (
    id          SERIAL          PRIMARY KEY,
    ticker      VARCHAR(20)     NOT NULL,
    author_id   INTEGER         NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title       VARCHAR(255)    NOT NULL,
    content     TEXT            NOT NULL,
    views       INTEGER         NOT NULL DEFAULT 0,
    likes       INTEGER         NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_posts_ticker_created
    ON board_posts(ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_author
    ON board_posts(author_id);

-- 5) board_comments — 댓글
CREATE TABLE IF NOT EXISTS board_comments (
    id          SERIAL          PRIMARY KEY,
    post_id     INTEGER         NOT NULL REFERENCES board_posts(id) ON DELETE CASCADE,
    author_id   INTEGER         NOT NULL REFERENCES users(user_id)  ON DELETE CASCADE,
    content     TEXT            NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_comments_post
    ON board_comments(post_id, created_at);

-- 6) board_likes — 좋아요 (중복 방지: post_id+author_id UNIQUE)
CREATE TABLE IF NOT EXISTS board_likes (
    id          SERIAL          PRIMARY KEY,
    post_id     INTEGER         NOT NULL REFERENCES board_posts(id) ON DELETE CASCADE,
    author_id   INTEGER         NOT NULL REFERENCES users(user_id)  ON DELETE CASCADE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (post_id, author_id)
);
CREATE INDEX IF NOT EXISTS idx_likes_post   ON board_likes(post_id);
CREATE INDEX IF NOT EXISTS idx_likes_author ON board_likes(author_id);

-- ─────────────────────────────────────────────────────────────────────────
-- 트리거: board_posts.updated_at 자동 갱신
-- ─────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_posts_updated_at ON board_posts;
CREATE TRIGGER trg_posts_updated_at
    BEFORE UPDATE ON board_posts
    FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ─────────────────────────────────────────────────────────────────────────
-- W1 events_v1 — 노출·클릭·사후 수익률 로깅 인프라
-- 출처: 08_recommendation_logic_improvements.md §5.2 + W1A_명세.md
-- 결정 박제: user_id INTEGER (기존 users PK 일관), session_id 비로그인용,
--           embedding_version W3.5 대비, impression_outcomes cron이 채움
-- ─────────────────────────────────────────────────────────────────────────

-- gen_random_uuid() 안전망. PG13+ 기본, PG12 이하에서도 본 extension 으로 사용 가능
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 7) recommendation_impressions — 추천 노출 시점·내용
CREATE TABLE IF NOT EXISTS recommendation_impressions (
    impression_id      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            INTEGER         REFERENCES users(user_id) ON DELETE SET NULL,
    session_id         VARCHAR(64),                      -- 비로그인 식별자 (W7)
    cohort             VARCHAR(20),                      -- W2 이후 채워짐
    shown_tickers      JSONB           NOT NULL,         -- [{ticker, rank, score, tier}, ...]
    model_version      VARCHAR(20)     NOT NULL,
    embedding_version  VARCHAR(20),                      -- W3.5 이후
    shown_at           TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    page_context       VARCHAR(50)
);
CREATE INDEX IF NOT EXISTS idx_impressions_user_at
    ON recommendation_impressions(user_id, shown_at DESC);
CREATE INDEX IF NOT EXISTS idx_impressions_session_at
    ON recommendation_impressions(session_id, shown_at DESC);
CREATE INDEX IF NOT EXISTS idx_impressions_at
    ON recommendation_impressions(shown_at);

-- 8) recommendation_clicks — 사용자 클릭·체류
CREATE TABLE IF NOT EXISTS recommendation_clicks (
    click_id        UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    impression_id   UUID            NOT NULL
                                    REFERENCES recommendation_impressions(impression_id)
                                    ON DELETE CASCADE,
    ticker          VARCHAR(10)     NOT NULL,
    rank_clicked    INTEGER         NOT NULL,
    dwell_ms        INTEGER,                            -- 이탈 시 PATCH 로 채움 (W1B)
    followup_action VARCHAR(30),                        -- 'watchlist_add' 등 자유 enum
    clicked_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_clicks_impression
    ON recommendation_clicks(impression_id);
CREATE INDEX IF NOT EXISTS idx_clicks_at
    ON recommendation_clicks(clicked_at);

-- 9) impression_outcomes — 사후 N일 수익률 (cron 적재, W1D)
CREATE TABLE IF NOT EXISTS impression_outcomes (
    impression_id        UUID        NOT NULL
                                     REFERENCES recommendation_impressions(impression_id)
                                     ON DELETE CASCADE,
    outcome_horizon_days INTEGER     NOT NULL,           -- 5 / 20 / 60
    ticker_returns       JSONB       NOT NULL,           -- {ticker: return_pct}
    computed_at          TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (impression_id, outcome_horizon_days)
);
CREATE INDEX IF NOT EXISTS idx_outcomes_horizon_at
    ON impression_outcomes(outcome_horizon_days, computed_at);

-- 10) events_v1_meta — 스키마 버전 박제 (단순 1행 테이블)
CREATE TABLE IF NOT EXISTS events_v1_meta (
    schema_version  VARCHAR(20)   PRIMARY KEY,
    applied_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes           TEXT
);

INSERT INTO events_v1_meta (schema_version, notes)
VALUES (
    'v1',
    'Initial schema for W1 logging. impressions + clicks + outcomes. '
    'Includes nullable embedding_version (for W3.5) and session_id (for W7 anonymous A/B).'
)
ON CONFLICT (schema_version) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────
-- W3.5D ticker_embeddings — 종목 임베딩 적재
-- 출처: 차기_사이클.md §W3.5
-- 정책: PK=ticker (한 시점에 한 버전만 활성). 새 버전 학습 시 UPSERT 로 덮어씀.
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ticker_embeddings (
    ticker             VARCHAR(10)   PRIMARY KEY,
    embedding_version  VARCHAR(20)   NOT NULL,         -- 'emb_v1', 'emb_v2', ...
    vector             REAL[]        NOT NULL,         -- 64차원 (proj head 출력)
    computed_at        TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_window_start  DATE,
    data_window_end    DATE
);
CREATE INDEX IF NOT EXISTS idx_ticker_embeddings_version
    ON ticker_embeddings(embedding_version);

