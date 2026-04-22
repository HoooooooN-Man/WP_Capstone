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
        # manifest에서 배포 기준 날짜 추출 (기본값 오늘)
        display_date = batch_data.get('display_date') 
        items = batch_data.get('items', [])
        category_id = batch_data.get('category_id', 'general') # 카테고리 ID 확보

        with duckdb.connect(DUCKDB_PATH) as duck_conn:
            for item in items:
                sentiment = item.get('sentiment', {'label': 'neutral', 'score': 0, 'pos': 0, 'neg': 0})
                
                # [이미지 URL 필터링] 문서에 언급된 fonts.googleapis.com 등 예외 처리
                img_url = item.get('image_url')
                if img_url and 'fonts.googleapis.com' in img_url:
                    img_url = None

                # 1. news_normalized 적재 (이미지 및 원문 URL 필드 추가)
                duck_conn.execute("""
                    INSERT OR REPLACE INTO news_normalized (
                        news_id, provider, title, title_norm, title_hash, 
                        query_text, source_name, google_url, origin_url, image_url,
                        published_at, fetched_at, 
                        sentiment_label, sentiment_score, pos_prob, neg_prob, neu_prob, 
                        used_for_ml, source_quality_tier
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['news_id'], item['provider'], item['title'], item.get('title_norm', ''), 
                    item['title_hash'], item.get('query', ''), item['source_name'], 
                    item.get('google_news_url', ''), item.get('origin_url', ''), img_url,
                    item['published_at'], item['fetched_at'], 
                    sentiment['label'], sentiment['score'], sentiment['pos'], sentiment['neg'], sentiment.get('neu', 0),
                    item.get('used_for_ml', True), item.get('source_quality_tier', 'normal')
                ))

                # 2. news_rankings (랭킹) 적재 - 오늘 띄워줄 뉴스 정보
                if display_date and 'rank' in item:
                    duck_conn.execute("""
                        INSERT OR REPLACE INTO news_rankings (display_date, category_id, news_id, rank, score)
                        VALUES (?, ?, ?, ?, ?)
                    """, (display_date, category_id, item['news_id'], item['rank'], item.get('score', 0)))

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
        raise HTTPException(status_code=500, detail=str(e))