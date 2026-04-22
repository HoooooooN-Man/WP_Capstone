from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import date, datetime
import duckdb
import os

# --- API 응답용 모델 (이 파일에서만 사용) ---
class NewsResponse(BaseModel):
    rank: int
    news_id: str
    title: str
    publisher: str
    origin_url: str
    image_url: Optional[str]
    sentiment_label: str
    sentiment_score: float
    pos_prob: float
    neg_prob: float
    neu_prob: float
    published_at: datetime

    class Config:
        from_attributes = True

# --- 라우터 설정 ---
router = APIRouter(prefix="/news", tags=["news"])

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DUCKDB_PATH = os.path.join(BASE_DIR, "db", "stock_analysis.duckdb")

@router.get("/list", response_model=List[NewsResponse])
async def get_news_list(
    category_id: str, 
    target_date: Optional[date] = None,
    provider: Optional[str] = None,      # 발행처 필터링용
    sort_by: str = "rank"                # "rank"(순위순) 또는 "latest"(최신순)
):
    if target_date is None:
        target_date = date.today()

    try:
        with duckdb.connect(DUCKDB_PATH) as duck_conn:
            # 1. 기본 Join 쿼리 (감성 분석 상세 스코어 포함)
            base_query = """
                SELECT 
                    r.rank, n.news_id, n.title, n.source_name, 
                    n.origin_url, n.image_url, n.sentiment_label,
                    n.sentiment_score, n.pos_prob, n.neg_prob, n.neu_prob,
                    n.published_at
                FROM news_rankings r
                JOIN news_normalized n ON r.news_id = n.news_id
                WHERE r.display_date = ? AND r.category_id = ?
            """
            params = [target_date, category_id]

            # 2. 발행처(Provider) 필터링 추가
            if provider:
                base_query += " AND n.source_name = ?"
                params.append(provider)

            # 3. 정렬 조건 분기
            if sort_by == "latest":
                base_query += " ORDER BY n.published_at DESC"
            else:
                base_query += " ORDER BY r.rank ASC"

            results = duck_conn.execute(base_query, params).fetchall()

            # 4. 결과 매핑 (NewsResponse 모델에 맞춤)
            return [
                NewsResponse(
                    rank=row[0],
                    news_id=row[1],
                    title=row[2],
                    publisher=row[3],
                    origin_url=row[4],
                    image_url=row[5],
                    sentiment_label=row[6],
                    sentiment_score=row[7],
                    pos_prob=row[8],
                    neg_prob=row[9],
                    neu_prob=row[10],
                    published_at=row[11]
                ) for row in results
            ]
            
    except Exception as e:
        # 에러 추적을 위해 로깅 추가 가능
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")