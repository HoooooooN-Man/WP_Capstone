from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import duckdb
import os
from pathlib import Path
from db.database import get_db
from db.models import UserWatchlist, Notification

router = APIRouter(prefix="/internal", tags=["internal"])

# ─────────────────────────────────────────────────────────────────────────────
# 뉴스 적재 전용 DuckDB.
#
# 중요: ML 서버(8001)가 market_data.duckdb 를 read-only 로 잡고 있어
# 같은 파일에 쓰기를 시도하면 DuckDB lock 충돌이 발생한다.
# 따라서 적재 대상은 NEWS_DUCKDB_PATH (기본: news_data.duckdb) 로 분리한다.
# 같은 경로를 newsranking.py 가 read-only 로 조회한다.
# ─────────────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve()
_DB_PKG = _HERE.parent.parent.parent          # Back/db/
_DEFAULT_NEWS_DB = _DB_PKG / "db" / "news_data.duckdb"

NEWS_DUCKDB_PATH = os.getenv("NEWS_DUCKDB_PATH", str(_DEFAULT_NEWS_DB))

@router.post("/ingest")
async def ingest_and_notify(batch_data: dict, db_pg: Session = Depends(get_db)):
    try:
        display_date = batch_data.get('display_date')
        # 중요: 워커는 'categories'라는 키 안에 'items'를 넣어서 보냅니다.
        categories = batch_data.get('categories', [])
        
        # 만약 categories가 없고 루트에 items가 있는 경우를 대비한 방어 로직
        if not categories and 'items' in batch_data:
            categories = [{"category_id": "general", "items": batch_data['items']}]

        total_processed = 0
        
        # 디버깅 로그: 실제 어디에 저장되는지 출력
        print(f"[*] Target DB Path: {os.path.abspath(NEWS_DUCKDB_PATH)}")
        print(f"[*] Received Categories: {len(categories)}")

        # 디렉토리 자동 생성 (최초 적재 시 파일이 없을 수 있음)
        Path(NEWS_DUCKDB_PATH).parent.mkdir(parents=True, exist_ok=True)

        with duckdb.connect(NEWS_DUCKDB_PATH) as duck_conn:
            # 스키마 보장 (newsranking.py 와 동일한 테이블 사용)
            duck_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS news_normalized (
                    news_id          VARCHAR PRIMARY KEY,
                    provider         VARCHAR,
                    title            VARCHAR,
                    title_hash       VARCHAR,
                    query_text       VARCHAR,
                    source_name      VARCHAR,
                    google_url       VARCHAR,
                    origin_url       VARCHAR,
                    image_url        VARCHAR,
                    published_at     VARCHAR,
                    fetched_at       VARCHAR,
                    sentiment_label  VARCHAR,
                    sentiment_score  DOUBLE,
                    pos_prob         DOUBLE,
                    neg_prob         DOUBLE,
                    neu_prob         DOUBLE
                )
                """
            )
            duck_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS news_rankings (
                    display_date  VARCHAR,
                    category_id   VARCHAR,
                    news_id       VARCHAR,
                    rank          INTEGER,
                    score         DOUBLE,
                    PRIMARY KEY (display_date, category_id, news_id)
                )
                """
            )
            duck_conn.execute("BEGIN TRANSACTION")
            
            for cat_group in categories:
                cat_id = cat_group.get('category_id', 'general')
                items = cat_group.get('items', [])
                
                print(f"[*] Category '{cat_id}': Processing {len(items)} items")

                for item in items:
                    # 필드 매핑 및 기본값 처리
                    sentiment = item.get('sentiment', {'label': 'neutral', 'score': 0, 'pos': 0, 'neg': 0})
                    # Redis 워커 필드명(id)과 DB 필드명 매핑 주의
                    news_id = item.get('id') or item.get('news_id') 
                    
                    # 1. news_normalized 적재
                    duck_conn.execute("""
                        INSERT OR REPLACE INTO news_normalized (
                            news_id, provider, title, title_hash, 
                            query_text, source_name, google_url, origin_url, image_url,
                            published_at, fetched_at, 
                            sentiment_label, sentiment_score, pos_prob, neg_prob, neu_prob
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        news_id,
                        item.get('publisher'),
                        item.get('title'),
                        item.get('title_hash', ''),
                        item.get('query', ''),
                        item.get('publisher'),
                        item.get('google_news_url', ''),
                        item.get('origin_url', ''),
                        item.get('image_url'),
                        item.get('published_at'),
                        item.get('collected_at'),
                        sentiment.get('label'),
                        sentiment.get('score'),
                        sentiment.get('pos'),
                        sentiment.get('neg'),
                        sentiment.get('neu', 0)
                    ))

                    # 2. news_rankings 적재
                    if display_date and 'rank' in item:
                        duck_conn.execute("""
                            INSERT OR REPLACE INTO news_rankings (display_date, category_id, news_id, rank, score)
                            VALUES (?, ?, ?, ?, ?)
                        """, (display_date, cat_id, news_id, item['rank'], item.get('rank_score', 0)))

                    total_processed += 1
            
            duck_conn.execute("COMMIT")
            
        print(f"[OK] Total {total_processed} items successfully committed to DuckDB.")
        return {"status": "success", "processed_items": total_processed}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database Ingest Error: {str(e)}")