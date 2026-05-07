"""
services/news_svc.py
====================
Tier 1B 4.5 — `data.py` 분할 결과물.

뉴스 피드·상세 도메인 (FinBERT 감성 분석 라벨 포함).
함수: get_news_feed, get_news_detail
"""

from __future__ import annotations

import pandas as pd

from ._core import (
    news_con as _news_con,
    cached as _cached,
)


def get_news_feed(
    limit:     int = 20,
    offset:    int = 0,
    sentiment: str | None = None,
    ticker:    str | None = None,
) -> dict:
    """
    `news_normalized` 테이블에서 최신 뉴스 피드 반환.

    - sentiment : 'positive' | 'neutral' | 'negative' (None → 전체)
    - ticker    : 종목코드 LIKE 매칭 (query_text/title 기준 폴백, 매핑 없을 때만)
    - 정렬      : 최신 published_at DESC
    """

    def fetch():
        con = _news_con()
        if con is None:
            # 뉴스 DB 가 아직 생성되지 않았으면 빈 결과 반환 (501 대신 graceful 빈 응답)
            return {"total": 0, "items": []}
        where = ["1=1"]
        params: list = []

        if sentiment:
            where.append("sentiment_label = ?")
            params.append(sentiment)

        if ticker:
            # news_company_map이 비어있어 query_text/title LIKE로 폴백
            where.append("(query_text LIKE ? OR title LIKE ?)")
            t = f"%{ticker}%"
            params.extend([t, t])

        where_sql = " AND ".join(where)

        total = con.execute(
            f"SELECT COUNT(*) FROM news_normalized WHERE {where_sql}", params
        ).fetchone()[0]

        rows = con.execute(
            f"""
            SELECT
                news_id,
                provider,
                title,
                source_name,
                origin_url,
                image_url,
                CAST(published_at AS VARCHAR) AS published_at,
                sentiment_label,
                CAST(sentiment_score AS FLOAT) AS sentiment_score,
                CAST(pos_prob AS FLOAT) AS pos_prob,
                CAST(neg_prob AS FLOAT) AS neg_prob,
                CAST(neu_prob AS FLOAT) AS neu_prob
            FROM news_normalized
            WHERE {where_sql}
            ORDER BY published_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchdf()

        items = []
        for _, r in rows.iterrows():
            items.append({
                "id":              r["news_id"],
                "ticker":          ticker or "",
                "company_name":    r.get("source_name") or "",
                "title":           r["title"],
                "source":          r["provider"],
                "published_at":    r["published_at"],
                "sentiment":       r["sentiment_label"],
                "sentiment_label": r["sentiment_label"],
                "sentiment_score": float(r["sentiment_score"]) if pd.notna(r["sentiment_score"]) else 0.0,
                "confidence":      float(r["sentiment_score"]) if pd.notna(r["sentiment_score"]) else 0.0,
                "pos_prob":        float(r["pos_prob"]) if pd.notna(r["pos_prob"]) else 0.0,
                "neg_prob":        float(r["neg_prob"]) if pd.notna(r["neg_prob"]) else 0.0,
                "neu_prob":        float(r["neu_prob"]) if pd.notna(r["neu_prob"]) else 0.0,
                "url":             r["origin_url"],
                "image_url":       r.get("image_url"),
            })

        return {"total": int(total), "items": items}

    return _cached(
        "news_feed", fetch, ttl=120,
        limit=limit, offset=offset, sentiment=sentiment or "", ticker=ticker or "",
    )


def get_news_detail(news_id: str) -> dict | None:
    """단건 뉴스 조회."""
    con = _news_con()
    if con is None:
        return None
    rows = con.execute(
        """
        SELECT news_id, provider, title, source_name, origin_url, image_url,
               CAST(published_at AS VARCHAR) AS published_at,
               sentiment_label,
               CAST(sentiment_score AS FLOAT) AS sentiment_score,
               CAST(pos_prob AS FLOAT) AS pos_prob,
               CAST(neg_prob AS FLOAT) AS neg_prob,
               CAST(neu_prob AS FLOAT) AS neu_prob
        FROM news_normalized
        WHERE news_id = ?
        LIMIT 1
        """,
        [news_id],
    ).fetchdf()
    if rows.empty:
        return None
    r = rows.iloc[0]
    return {
        "id":              r["news_id"],
        "title":           r["title"],
        "source":          r["provider"],
        "publisher":       r["provider"],
        "origin_url":      r["origin_url"],
        "url":             r["origin_url"],
        "image_url":       r.get("image_url"),
        "published_at":    r["published_at"],
        "sentiment_label": r["sentiment_label"],
        "sentiment_score": float(r["sentiment_score"]) if pd.notna(r["sentiment_score"]) else 0.0,
        "pos_prob":        float(r["pos_prob"]) if pd.notna(r["pos_prob"]) else 0.0,
        "neg_prob":        float(r["neg_prob"]) if pd.notna(r["neg_prob"]) else 0.0,
        "neu_prob":        float(r["neu_prob"]) if pd.notna(r["neu_prob"]) else 0.0,
    }
