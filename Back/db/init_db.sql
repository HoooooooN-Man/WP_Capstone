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

-- 2) user_watchlist — 사용자 관심 종목 (포트폴리오)
CREATE TABLE IF NOT EXISTS user_watchlist (
    id          SERIAL          PRIMARY KEY,
    user_id     INTEGER         REFERENCES users(user_id) ON DELETE CASCADE,
    ticker      VARCHAR(20)     NOT NULL,
    created_at  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, ticker)
);
CREATE INDEX IF NOT EXISTS idx_watch_user   ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watch_ticker ON user_watchlist(ticker);

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
