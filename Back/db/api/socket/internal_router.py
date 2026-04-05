from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import duckdb
import os
from db.database import get_db
from db.models import UserWatchlist, Notification

router = APIRouter(prefix="/internal", tags=["internal"])

# 경로 문제 방지를 위해 절대 경로 설정 (현재 파일 위치 기준)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DUCKDB_PATH = os.path.join(BASE_DIR, "db", "stock_analysis.duckdb")

@router.post("/ingest")
async def ingest_and_notify(batch_data: dict, db_pg: Session = Depends(get_db)):
    try:
        # Context Manager 사용으로 자동 Close 보장
        with duckdb.connect(DUCKDB_PATH) as duck_conn:
            items = batch_data.get('items', [])
            for item in items:
                sentiment = item.get('sentiment')
                if not sentiment: 
                    continue

                # 1. news_normalized 적재 (총 17개 컬럼)
                duck_conn.execute("""
                    INSERT OR REPLACE INTO news_normalized (
                        news_id, provider, title, title_norm, title_hash, 
                        query_text, source_name, google_url, published_at, fetched_at, 
                        sentiment_label, sentiment_score, pos_prob, neg_prob, neu_prob, 
                        used_for_ml, source_quality_tier
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['news_id'],                  # 1
                    item['provider'],                 # 2
                    item['title'],                    # 3
                    item.get('title_norm', ''),       # 4
                    item['title_hash'],               # 5
                    item.get('query', ''),            # 6
                    item['source_name'],              # 7
                    item.get('google_url', ''),       # 8
                    item['published_at'],             # 9
                    item['fetched_at'],               # 10
                    sentiment['label'],               # 11
                    sentiment['score'],               # 12
                    sentiment['pos'],                 # 13
                    sentiment['neg'],                 # 14
                    sentiment.get('neu', 0),          # 15
                    item.get('used_for_ml', True),    # 16
                    item.get('source_quality_tier', 'normal') # 17
                ))

                # 2. news_company_map 적재
                for m in item.get('matched', []):
                    ticker = m['ticker']
                    duck_conn.execute("""
                        INSERT OR REPLACE INTO news_company_map VALUES (?, ?, ?, ?, ?)
                    """, (item['news_id'], ticker, m['company_name'], m['match_type'], m['match_score']))

                '''# 3. PostgreSQL 알림 로직 (긍정/부정 뉴스인 경우만)
                    if sentiment['label'] in ['positive', 'negative']:
                        subscribers = db_pg.query(UserWatchlist).filter(UserWatchlist.ticker == ticker).all()
                        for sub in subscribers:
                            new_notif = Notification(
                                user_id=sub.user_id,
                                ticker=ticker,
                                title=item['title'],
                                sentiment_label=sentiment['label']
                            )
                            db_pg.add(new_notif)

        # 모든 작업 완료 후 PostgreSQL 커밋
        db_pg.commit()'''
        return {"status": "success", "processed_items": len(items)}

    except Exception as e:
        #db_pg.rollback()
        import traceback
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=str(e))