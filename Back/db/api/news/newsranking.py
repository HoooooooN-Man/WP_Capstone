"""
뉴스 감성분석 API 라우터
경로: db/api/news/newsranking.py
DB:   NEWS_DUCKDB_PATH (기본 db/db/news_data.duckdb)

엔드포인트:
  GET /api/v1/news/feed              - 뉴스 피드 (NewsView 호환)
  GET /api/v1/news/detail/{news_id}  - 뉴스 단건 상세 (id-based)
  GET /api/v1/news/rankings          - 날짜별 뉴스 랭킹 (news_rankings JOIN news_normalized)
  GET /api/v1/news/rankings/dates    - 랭킹 데이터가 있는 날짜 목록
  GET /api/v1/news/rankings/{news_id} - 특정 뉴스 상세 (감성 점수 포함)

dbapi.js (baseURL=http://localhost:8000) 가 본 라우터를 호출.
"""

from fastapi import APIRouter, HTTPException, Query
from pathlib import Path
from typing import Optional
import duckdb
import os

router = APIRouter(prefix="/api/v1/news", tags=["news"])

# 뉴스 전용 DuckDB. internal_router.py 가 쓰기, 본 라우터가 읽기.
# 환경변수 NEWS_DUCKDB_PATH 로 통일 (.env.example 참조).
_HERE = Path(__file__).resolve()
_DB_PKG = _HERE.parent.parent.parent          # Back/db/
_DEFAULT_NEWS_DB = _DB_PKG / "db" / "news_data.duckdb"

DB_PATH = os.getenv("NEWS_DUCKDB_PATH", str(_DEFAULT_NEWS_DB))


def get_conn():
    """읽기 전용 DuckDB 연결 반환. 파일이 없으면 빈 파일을 만들지 않고 503 처리."""
    if not Path(DB_PATH).exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"뉴스 DB 가 아직 생성되지 않았습니다 ({DB_PATH}). "
                "Go 파이프라인 + /internal/ingest 가 한 번 이상 실행돼야 합니다."
            ),
        )
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


# ---------------------------------------------------------------------------
# 뉴스 피드 (NewsView 호환)
# ---------------------------------------------------------------------------
@router.get("/feed", summary="뉴스 피드 (감성 라벨 + origin_url 포함)")
def get_news_feed(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sentiment: Optional[str] = Query(None, description="positive | neutral | negative"),
    ticker: Optional[str] = Query(None, description="종목 코드/회사명 LIKE"),
):
    """
    `news_normalized` 테이블에서 최신순 뉴스 피드 반환.
    응답 형식: ``{"total": int, "items": [...]}`` (NewsView.vue 호환).
    """
    try:
        conn = get_conn()

        where = ["1=1"]
        params: list = []

        if sentiment:
            where.append("sentiment_label = ?")
            params.append(sentiment)

        if ticker:
            where.append("(query_text LIKE ? OR title LIKE ?)")
            t = f"%{ticker}%"
            params.extend([t, t])

        where_sql = " AND ".join(where)

        total = conn.execute(
            f"SELECT COUNT(*) FROM news_normalized WHERE {where_sql}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT news_id, provider, title, source_name, origin_url, image_url,
                   CAST(published_at AS VARCHAR) AS published_at,
                   sentiment_label,
                   CAST(sentiment_score AS DOUBLE) AS sentiment_score,
                   CAST(pos_prob AS DOUBLE)        AS pos_prob,
                   CAST(neg_prob AS DOUBLE)        AS neg_prob,
                   CAST(neu_prob AS DOUBLE)        AS neu_prob
            FROM news_normalized
            WHERE {where_sql}
            ORDER BY published_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()
        conn.close()

        items = []
        for r in rows:
            (
                news_id, provider, title, source_name, origin_url, image_url,
                published_at, sentiment_label,
                sentiment_score, pos_prob, neg_prob, neu_prob,
            ) = r
            items.append({
                "id":              news_id,
                "ticker":          ticker or "",
                "company_name":    source_name or "",
                "title":           title,
                "source":          provider,
                "published_at":    published_at,
                "sentiment":       sentiment_label,
                "sentiment_label": sentiment_label,
                "sentiment_score": float(sentiment_score) if sentiment_score is not None else 0.0,
                "confidence":      float(sentiment_score) if sentiment_score is not None else 0.0,
                "pos_prob":        float(pos_prob) if pos_prob is not None else 0.0,
                "neg_prob":        float(neg_prob) if neg_prob is not None else 0.0,
                "neu_prob":        float(neu_prob) if neu_prob is not None else 0.0,
                "url":             origin_url,
                "image_url":       image_url,
            })

        return {"total": int(total), "items": items}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB 조회 오류: {str(e)}")


# ---------------------------------------------------------------------------
# 뉴스 단건 상세 (NewsDetailModal 호환 별칭)
# ---------------------------------------------------------------------------
@router.get("/detail/{news_id}", summary="뉴스 단건 상세 (id 기반)")
def get_news_detail_by_id(news_id: str):
    """`/api/v1/news/rankings/{news_id}` 와 동일 응답을 반환하는 별칭 라우트."""
    return get_news_detail(news_id)