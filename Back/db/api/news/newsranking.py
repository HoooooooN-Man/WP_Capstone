"""
뉴스 감성분석 API 라우터
경로: db/api/news/news.py
DB: db/db/stock_analysis.duckdb

포함 엔드포인트:
  GET /api/v1/news/rankings          - 날짜별 뉴스 랭킹 목록 (news_rankings JOIN news_normalized)
  GET /api/v1/news/rankings/dates    - 랭킹 데이터가 있는 날짜 목록
  GET /api/v1/news/rankings/{news_id} - 특정 뉴스 상세 (감성 점수 포함)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import duckdb
import os

router = APIRouter(prefix="/api/v1/news", tags=["news"])

# DuckDB 파일 경로 (server.py 기준 상대경로)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "db", "stock_analysis.duckdb")


def get_conn():
    """읽기 전용 DuckDB 연결 반환"""
    return duckdb.connect(DB_PATH, read_only=True)


# ---------------------------------------------------------------------------
# 날짜 목록
# ---------------------------------------------------------------------------
@router.get("/rankings/dates")
def get_ranking_dates():
    """랭킹 데이터가 존재하는 날짜 목록 (최신순)"""
    try:
        conn = get_conn()
        rows = conn.execute(
            """
            SELECT DISTINCT display_date
            FROM news_rankings
            ORDER BY display_date DESC
            """
        ).fetchall()
        conn.close()

        dates = [row[0] for row in rows]
        return {
            "dates": dates,
            "latest": dates[0] if dates else None,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB 조회 오류: {str(e)}")


# ---------------------------------------------------------------------------
# 랭킹 목록
# ---------------------------------------------------------------------------
@router.get("/rankings")
def get_news_rankings(
    display_date: Optional[str] = Query(None, description="조회 날짜 (YYYY-MM-DD). 미입력 시 최신 날짜"),
    category_id: Optional[str] = Query(None, description="카테고리 필터"),
    limit: int = Query(20, ge=1, le=100, description="최대 반환 수"),
):
    """
    뉴스 랭킹 목록 조회.
    news_rankings와 news_normalized를 JOIN하여 감성 점수까지 반환합니다.

    sentiment_label: positive / negative / neutral
    sentiment_score: FinBERT 확신도 (0.0 ~ 1.0)
    """
    try:
        conn = get_conn()

        # 날짜 미입력 시 최신 날짜 자동 선택
        if not display_date:
            row = conn.execute(
                "SELECT MAX(display_date) FROM news_rankings"
            ).fetchone()
            if not row or row[0] is None:
                conn.close()
                raise HTTPException(status_code=503, detail="랭킹 데이터가 없습니다.")
            display_date = row[0]

        params = [display_date]
        category_filter = ""
        if category_id:
            category_filter = "AND r.category_id = ?"
            params.append(category_id)

        params.append(limit)

        query = f"""
            SELECT
                r.rank,
                r.score             AS ranking_score,
                r.category_id,
                r.display_date,
                n.news_id,
                n.title,
                n.provider,
                n.source_name,
                n.published_at,
                n.image_url,
                n.google_url,
                n.origin_url,
                n.sentiment_label,
                n.sentiment_score,
                n.pos_prob,
                n.neg_prob,
                n.neu_prob
            FROM news_rankings r
            JOIN news_normalized n ON r.news_id = n.news_id
            WHERE r.display_date = ?
            {category_filter}
            ORDER BY r.rank ASC
            LIMIT ?
        """

        rows = conn.execute(query, params).fetchall()
        conn.close()

        columns = [
            "rank", "ranking_score", "category_id", "display_date",
            "news_id", "title", "provider", "source_name", "published_at",
            "image_url", "google_url", "origin_url",
            "sentiment_label", "sentiment_score",
            "pos_prob", "neg_prob", "neu_prob",
        ]

        items = []
        for row in rows:
            item = dict(zip(columns, row))
            # published_at을 문자열로 변환 (직렬화 안전)
            if item.get("published_at") and not isinstance(item["published_at"], str):
                item["published_at"] = str(item["published_at"])
            if item.get("display_date") and not isinstance(item["display_date"], str):
                item["display_date"] = str(item["display_date"])
            items.append(item)

        return {
            "display_date": str(display_date),
            "total": len(items),
            "items": items,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB 조회 오류: {str(e)}")


# ---------------------------------------------------------------------------
# 뉴스 상세
# ---------------------------------------------------------------------------
@router.get("/rankings/{news_id}")
def get_news_detail(news_id: str):
    """특정 뉴스 상세 조회 (감성 확률 전체 포함)"""
    try:
        conn = get_conn()
        row = conn.execute(
            """
            SELECT
                n.news_id,
                n.title,
                n.provider,
                n.source_name,
                n.query_text,
                n.published_at,
                n.fetched_at,
                n.google_url,
                n.origin_url,
                n.image_url,
                n.sentiment_label,
                n.sentiment_score,
                n.pos_prob,
                n.neg_prob,
                n.neu_prob
            FROM news_normalized n
            WHERE n.news_id = ?
            """,
            [news_id],
        ).fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="해당 뉴스를 찾을 수 없습니다.")

        columns = [
            "news_id", "title", "provider", "source_name", "query_text",
            "published_at", "fetched_at", "google_url", "origin_url", "image_url",
            "sentiment_label", "sentiment_score", "pos_prob", "neg_prob", "neu_prob",
        ]
        item = dict(zip(columns, row))
        for key in ("published_at", "fetched_at"):
            if item.get(key) and not isinstance(item[key], str):
                item[key] = str(item[key])
        return item

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB 조회 오류: {str(e)}")