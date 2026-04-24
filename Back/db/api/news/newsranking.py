from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")


# ── /news/feed — 프론트엔드 NewsView 연동용 ──────────────────────────────────

class NewsFeedItem(BaseModel):
    id:          str
    title:       str
    source:      str
    url:         str
    image_url:   Optional[str] = None
    sentiment:   str           # "positive" | "neutral" | "negative"
    confidence:  float
    published_at: datetime
    ticker:      Optional[str] = None

    class Config:
        from_attributes = True


class NewsFeedResponse(BaseModel):
    total:  int
    items:  List[NewsFeedItem]


SENTIMENT_MAP = {
    "positive": "positive",
    "negative": "negative",
    "neutral":  "neutral",
    "pos":      "positive",
    "neg":      "negative",
    "neu":      "neutral",
}


@router.get("/feed", response_model=NewsFeedResponse, summary="뉴스 피드 (감성 분석 포함)")
async def get_news_feed(
    sentiment: Optional[str] = Query(None,  description="긍정/중립/부정 필터"),
    ticker:    Optional[str] = Query(None,  description="티커 필터 (예: 005930)"),
    limit:     int           = Query(20,    ge=1, le=100),
    offset:    int           = Query(0,     ge=0),
    target_date: Optional[date] = Query(None, description="기준 날짜 (기본: 오늘)"),
):
    """
    감성 분석이 포함된 뉴스 피드를 반환합니다.
    NewsView.vue 에서 사용합니다.
    """
    if target_date is None:
        target_date = date.today()

    try:
        with duckdb.connect(DUCKDB_PATH) as duck_conn:
            conditions = ["r.display_date = ?"]
            params: list = [target_date]

            # 감성 필터
            if sentiment:
                mapped = SENTIMENT_MAP.get(sentiment.lower(), sentiment.lower())
                conditions.append("LOWER(n.sentiment_label) = ?")
                params.append(mapped)

            # 티커 필터 (news_normalized 에 ticker 컬럼이 있는 경우)
            try:
                duck_conn.execute("SELECT ticker FROM news_normalized LIMIT 1").fetchone()
                has_ticker_col = True
            except Exception:
                has_ticker_col = False

            if ticker and has_ticker_col:
                conditions.append("n.ticker = ?")
                params.append(ticker.zfill(6))

            where_clause = " AND ".join(conditions)

            # 전체 카운트
            count_sql = f"""
                SELECT COUNT(*)
                FROM news_rankings r
                JOIN news_normalized n ON r.news_id = n.news_id
                WHERE {where_clause}
            """
            total_row = duck_conn.execute(count_sql, params).fetchone()
            total = total_row[0] if total_row else 0

            # 데이터 조회
            data_sql = f"""
                SELECT
                    n.news_id,
                    n.title,
                    n.source_name,
                    n.origin_url,
                    n.image_url,
                    n.sentiment_label,
                    n.sentiment_score,
                    n.published_at
                    {"," + "n.ticker" if has_ticker_col else ""}
                FROM news_rankings r
                JOIN news_normalized n ON r.news_id = n.news_id
                WHERE {where_clause}
                ORDER BY r.rank ASC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            rows = duck_conn.execute(data_sql, params).fetchall()

            items = []
            for row in rows:
                raw_sentiment = (row[5] or "neutral").lower()
                mapped_sentiment = SENTIMENT_MAP.get(raw_sentiment, "neutral")
                item_ticker = row[8] if has_ticker_col and len(row) > 8 else None
                items.append(NewsFeedItem(
                    id=str(row[0]),
                    title=row[1] or "",
                    source=row[2] or "",
                    url=row[3] or "",
                    image_url=row[4],
                    sentiment=mapped_sentiment,
                    confidence=float(row[6]) if row[6] else 0.5,
                    published_at=row[7],
                    ticker=item_ticker,
                ))

            return NewsFeedResponse(total=total, items=items)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")