"""
파일 위치: Back/db/api/news/webnews.py

prefix: /api/webnews

엔드포인트:
  GET  /api/webnews/dates              → Redis에 rank 키가 있는 날짜 목록
  GET  /api/webnews/{date}/daily       → report:daily (LLM 전체 시장 리포트)
  GET  /api/webnews/{date}/summary     → 6개 카테고리 summary + 감성 집계
  GET  /api/webnews/{date}/{category}  → rank + item(hash) + sentiment + report 병합
  POST /api/webnews/analyze            → 수동 분석 트리거 (force 가능)
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import redis
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

load_dotenv()

logger   = logging.getLogger("webnews_router")
router   = APIRouter(prefix="/api/webnews", tags=["webnews"])
KST      = timezone(timedelta(hours=9))

REDIS_CONF: dict = {
    "host":                   os.getenv("REDIS_HOST"),
    "port":                   int(os.getenv("WEBNEWS_REDIS_PORT", 6380)),
    "password":               os.getenv("WEBNEWS_REDIS_PASSWORD"),
    "decode_responses":       True,
    "socket_timeout":         10,
    "socket_connect_timeout": 5,
}
CATEGORIES = ["korea", "world", "business", "science_tech", "policy_finance", "industry_ai"]
TOP_N      = int(os.getenv("WEBNEWS_TOP_N_DEFAULT", 10))


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────
def _rd() -> redis.Redis:
    return redis.Redis(**REDIS_CONF)

def _today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


# ── GET /api/webnews/dates ────────────────────────────────────────────────────
@router.get("/dates")
def get_dates():
    """Redis에 rank 키가 존재하는 날짜 목록 반환."""
    rd = _rd()
    dates: set[str] = set()
    for key in rd.scan_iter(match="webnews:*:rank:*"):
        m = re.match(r"webnews:(\d{4}-\d{2}-\d{2}):", key)
        if m:
            dates.add(m.group(1))

    sorted_dates = sorted(dates, reverse=True)
    return {
        "dates":  sorted_dates,
        "latest": sorted_dates[0] if sorted_dates else None,
    }


# ── GET /api/webnews/{date}/daily ─────────────────────────────────────────────
@router.get("/{date}/daily")
def get_daily_report(date: str):
    """LLM이 생성한 전체 시장 daily report 반환."""
    rd  = _rd()
    raw = rd.get(f"webnews:{date}:report:daily")
    if not raw:
        raise HTTPException(status_code=404, detail=f"{date} daily report 없음")
    return json.loads(raw)


# ── GET /api/webnews/{date}/summary ──────────────────────────────────────────
@router.get("/{date}/summary")
def get_summary(date: str):
    """6개 카테고리 summary + FinBERT 감성 집계 병합 반환."""
    rd     = _rd()
    result = []

    for cat in CATEGORIES:
        raw_summary   = rd.get(f"webnews:{date}:summary:{cat}")
        raw_sentiment = rd.get(f"webnews:{date}:sentiment:{cat}")
        if not raw_summary:
            continue

        data = json.loads(raw_summary)
        if raw_sentiment:
            s = json.loads(raw_sentiment)
            data["sentiment"] = {
                "avg_score":    s.get("avg_sentiment_score"),
                "label_counts": s.get("label_counts"),
            }
        else:
            data["sentiment"] = None
        result.append(data)

    if not result:
        raise HTTPException(status_code=404, detail=f"{date} summary 없음")

    return {
        "date":                 date,
        "sentiment_updated_at": _rd().get(f"webnews:{date}:sentiment:updated_at"),
        "categories":           result,
    }


# ── GET /api/webnews/{date}/{category} ───────────────────────────────────────
@router.get("/{date}/{category}")
def get_category(date: str, category: str):
    """
    rank(zset) + item(hash) + sentiment(캐시) + report(LLM) 병합.
    프론트 NewsDetailModal 카테고리 탭에서 호출.
    감성 분석이 아직 안 됐으면 sentiment 필드가 null 로 내려감.
    """
    rd = _rd()

    # 1. 랭킹 목록
    ranked = rd.zrevrange(f"webnews:{date}:rank:{category}", 0, TOP_N - 1, withscores=True)
    if not ranked:
        raise HTTPException(status_code=404, detail=f"{date}/{category} 랭킹 없음")

    # 2. 감성 캐시 → item_id 기준 맵
    raw_sentiment = rd.get(f"webnews:{date}:sentiment:{category}")
    sentiment_map: dict[str, dict] = {}
    sentiment_summary = None
    if raw_sentiment:
        s_data = json.loads(raw_sentiment)
        for it in s_data.get("items", []):
            sentiment_map[it["item_id"]] = it.get("sentiment")
        sentiment_summary = {
            "avg_score":    s_data.get("avg_sentiment_score"),
            "label_counts": s_data.get("label_counts"),
            "updated_at":   rd.get(f"webnews:{date}:sentiment:updated_at"),
        }

    # 3. item hash 조회 + 감성 병합
    items: list[dict] = []
    for idx, (item_id, rank_score) in enumerate(ranked, start=1):
        h = rd.hgetall(f"webnews:{date}:item:{item_id}")
        if not h:
            continue
        items.append({
            "rank":            idx,
            "item_id":         item_id,
            "title":           h.get("title", ""),
            "publisher":       h.get("publisher", ""),
            "category_id":     h.get("category_id", category),
            "category_label":  h.get("category_label", ""),
            "score":           float(h.get("score", 0) or 0),
            "rank_score":      float(rank_score),
            "seen_count":      int(h.get("seen_count", 0) or 0),
            "best_rank":       int(h.get("best_rank", 0) or 0),
            "latest_rank":     int(h.get("latest_rank", 0) or 0),
            "published_at":    h.get("published_at", ""),
            "google_news_url": h.get("google_news_url", ""),
            "sentiment":       sentiment_map.get(item_id),   # None if 미분석
        })

    # 4. 카테고리 AI report
    raw_report = rd.get(f"webnews:{date}:report:{category}")
    report     = json.loads(raw_report) if raw_report else None

    return {
        "date":             date,
        "category_id":      category,
        "item_count":       len(items),
        "items":            items,
        "sentiment_summary": sentiment_summary,
        "report":           report,
    }


# ── POST /api/webnews/analyze ─────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    date:  Optional[str] = None   # 기본값: 오늘
    force: bool          = False  # True면 기존 결과 무시하고 재실행

@router.post("/analyze")
def trigger_analysis(req: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    수동으로 FinBERT 분석 트리거.
    서버 재시작 없이 즉시 실행하거나 특정 날짜를 재분석할 때 사용.
    백그라운드에서 실행되므로 응답은 즉시 반환.
    """
    from WP_Capstone.Back.db.scheduler.webnews_worker import run_analysis

    def _run():
        try:
            run_analysis(force=req.force)
        except Exception as e:
            logger.error(f"[ANALYZE] 실패: {e}")

    background_tasks.add_task(_run)
    return {
        "status": "started",
        "date":   req.date or datetime.now(KST).strftime("%Y-%m-%d"),
        "force":  req.force,
    }
