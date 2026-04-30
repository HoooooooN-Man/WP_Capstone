from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import duckdb
import os
from db.database import get_db
from db.models import UserWatchlist, Notification

router = APIRouter(prefix="/internal", tags=["internal"])

# DuckDB 경로 (환경변수 DUCKDB_PATH 우선, 없으면 통합 DB 기본값)
DUCKDB_PATH = os.getenv(
    "DUCKDB_PATH",
    r"E:\Capstone Data\project_data\db\market_data.duckdb",
)

@router.post("/ingest")
async def ingest_and_notify(batch_data: dict, db_pg: Session = Depends(get_db)):
    try:
        display_date = batch_data.get('display_date') 
        items = batch_data.get('items', [])
        category_id = batch_data.get('category_id', 'general')

        # 1. 연결 유지 (Context Manager 내부에서 트랜잭션 관리)
        with duckdb.connect(DUCKDB_PATH) as duck_conn:
            # 트랜잭션 시작 (성능 최적화)
            duck_conn.execute("BEGIN TRANSACTION")
            
            for item in items:
                # 필드 기본값 처리 (KeyError 방지)
                sentiment = item.get('sentiment', {'label': 'neutral', 'score': 0, 'pos': 0, 'neg': 0})
                img_url = item.get('image_url')
                
                # 이미지 URL 필터링 보강
                if not img_url or any(x in img_url for x in ['fonts.googleapis.com', 'pixel']):
                    img_url = None

                # 1. news_normalized 적재 (필드명은 전달하신 Redis 규격 기준)
                duck_conn.execute("""
                    INSERT OR REPLACE INTO news_normalized (
                        news_id, provider, title, title_hash, 
                        query_text, source_name, google_url, origin_url, image_url,
                        published_at, fetched_at, 
                        sentiment_label, sentiment_score, pos_prob, neg_prob, neu_prob
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get('id'), # Redis/JSON의 'id' 사용
                    item.get('publisher'), # publisher로 매핑
                    item.get('title'),
                    item.get('title_hash', ''), # 해시값 부재 시 빈값
                    item.get('query', ''),
                    item.get('publisher'), # source_name
                    item.get('google_news_url', ''),
                    item.get('origin_url', ''),
                    img_url,
                    item.get('published_at'),
                    item.get('collected_at'), # Redis 규격의 collected_at
                    sentiment['label'], 
                    sentiment['score'], 
                    sentiment['pos'], 
                    sentiment['neg'], 
                    sentiment.get('neu', 0)
                ))

                # 2. news_rankings (랭킹) 적재
                if display_date and 'rank' in item:
                    duck_conn.execute("""
                        INSERT OR REPLACE INTO news_rankings (display_date, category_id, news_id, rank, score)
                        VALUES (?, ?, ?, ?, ?)
                    """, (display_date, category_id, item.get('id'), item['rank'], item.get('score', 0)))

                # 3. news_company_map 적재 (기존 로직)
                for m in item.get('matched', []):
                    ticker = m['ticker']
                    duck_conn.execute("""
                        INSERT OR REPLACE INTO news_company_map VALUES (?, ?, ?, ?, ?)
                    """, (item['news_id'], ticker, m['company_name'], m['match_type'], m['match_score']))

                '''# 4. PostgreSQL 알림 로직 (오늘 기준 새로 나온 긍정/부정 뉴스만)
                # item의 published_at 또는 display_date가 오늘인 경우만 실행
                is_today = str(item['published_at']).startswith(str(display_date))
                if is_today and sentiment['label'] in ['positive', 'negative']:
                    for m in item.get('matched', []): # 매칭된 종목별로 알림 생성
                        ticker = m['ticker']
                        subscribers = db_pg.query(UserWatchlist).filter(UserWatchlist.ticker == ticker).all()
                        for sub in subscribers:
                            new_notif = Notification(
                                user_id=sub.user_id,
                                ticker=ticker,
                                title=item['title'],
                                sentiment_label=sentiment['label']
                            )
                            db_pg.add(new_notif)
                db_pg.commit()'''

        return {"status": "success", "processed_items": len(items)}

    except Exception as e:
        import traceback
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"Database Ingest Error: {str(e)}")