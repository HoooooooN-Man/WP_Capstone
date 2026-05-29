"""
파일 위치: Back/db/scheduler/webnews_worker.py

server.py 기동 시 APScheduler에 등록 → 매일 09:30 KST 자동 실행.
analyzer.py 는 Back/Redis/crawling/ 에 있으므로 .env의 ANALYZER_PATH 로 경로를 받거나
ANALYZER_PATH 미설정 시 상대경로로 추론.

저장 키 (TTL 48h):
  webnews:{date}:sentiment:{category}   → JSON (카테고리별 감성 결과)
  webnews:{date}:sentiment:updated_at   → 완료 시각 문자열
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("webnews_worker")

# ── 설정 ──────────────────────────────────────────────────────────────────────
REDIS_CONF: dict = {
    "host":                   os.getenv("REDIS_HOST"),
    "port":                   int(os.getenv("WEBNEWS_REDIS_PORT", 6380)),
    "password":               os.getenv("WEBNEWS_REDIS_PASSWORD"),
    "decode_responses":       True,
    "socket_timeout":         int(os.getenv("REDIS_SOCKET_TIMEOUT", 60)),
    "socket_connect_timeout": int(os.getenv("REDIS_CONNECT_TIMEOUT", 10)),
    "retry_on_timeout":       True,
}

TOP_N         = int(os.getenv("WEBNEWS_TOP_N_DEFAULT", 10))
SENTIMENT_TTL = 60 * 60 * 48   # 48시간
KST           = timezone(timedelta(hours=9))
CATEGORIES    = ["korea", "world", "business", "science_tech", "policy_finance", "industry_ai"]

# ── analyzer.py 경로 설정 ─────────────────────────────────────────────────────
# .env 에 ANALYZER_PATH=C:/Users/.../Back/Redis/crawling 형태로 지정하거나
# 미지정 시 server.py 기준 ../../../Redis/crawling 으로 추론
_ANALYZER_DIR = os.getenv(
    "ANALYZER_PATH",
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "Redis", "crawling")
    ),
)

# ── in-process 중복 실행 방지 ─────────────────────────────────────────────────
_last_run_date: str | None = None


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────
def _get_rd() -> redis.Redis:
    return redis.Redis(**REDIS_CONF)

def _today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")

def _load_analyzer():
    """SentimentAnalyzer를 동적으로 import (싱글턴이므로 최초 1회만 느림)"""
    if _ANALYZER_DIR not in sys.path:
        sys.path.insert(0, _ANALYZER_DIR)
    from analyzer import SentimentAnalyzer  # noqa: PLC0415
    return SentimentAnalyzer()

def _scan_categories(rd: redis.Redis, date: str) -> list[str]:
    found: list[str] = []
    for key in rd.scan_iter(match=f"webnews:{date}:rank:*"):
        cat = key.split(":")[-1].strip()
        if cat and cat not in found:
            found.append(cat)
    return found or CATEGORIES


# ── 카테고리 분석 ─────────────────────────────────────────────────────────────
def _analyze_category(rd: redis.Redis, analyzer, date: str, category: str) -> dict:
    ranked = rd.zrevrange(f"webnews:{date}:rank:{category}", 0, TOP_N - 1, withscores=True)

    items: list[dict] = []
    for idx, (item_id, rank_score) in enumerate(ranked, start=1):
        h = rd.hgetall(f"webnews:{date}:item:{item_id}")
        if not h:
            continue

        title     = h.get("title", "")
        sentiment = analyzer.analyze(title) if title else None

        items.append({
            "rank":            idx,
            "item_id":         item_id,
            "title":           title,
            "publisher":       h.get("publisher", ""),
            "category_id":     h.get("category_id", category),
            "category_label":  h.get("category_label", ""),
            "score":           float(h.get("score", 0) or 0),
            "rank_score":      float(rank_score),
            "seen_count":      int(h.get("seen_count", 0) or 0),
            "best_rank":       int(h.get("best_rank", 0) or 0),
            "latest_rank":     int(h.get("latest_rank", 0) or 0),
            "published_at":    h.get("published_at", ""),
            "collected_at":    h.get("collected_at", ""),
            "google_news_url": h.get("google_news_url", ""),
            "sentiment":       sentiment,
        })

    scored     = [it for it in items if it["sentiment"]]
    avg_score  = (
        round(sum(it["sentiment"]["score"] for it in scored) / len(scored), 4)
        if scored else None
    )
    label_counts = {"positive": 0, "neutral": 0, "negative": 0}
    for it in scored:
        label_counts[it["sentiment"]["label"]] += 1

    return {
        "category_id":         category,
        "item_count":          len(items),
        "avg_sentiment_score": avg_score,
        "label_counts":        label_counts,
        "items":               items,
    }


# ── Redis 저장 ────────────────────────────────────────────────────────────────
def _save(rd: redis.Redis, date: str, results: list[dict]) -> None:
    pipe = rd.pipeline()
    for r in results:
        pipe.set(
            f"webnews:{date}:sentiment:{r['category_id']}",
            json.dumps(r, ensure_ascii=False),
            ex=SENTIMENT_TTL,
        )
    updated_at = datetime.now(KST).strftime("%Y-%m-%dT%H:%M:%S%z")
    pipe.set(f"webnews:{date}:sentiment:updated_at", updated_at, ex=SENTIMENT_TTL)
    pipe.execute()
    logger.info(f"[SAVE] {len(results)}개 카테고리 저장 완료 ({updated_at})")


# ── 메인 진입점 ───────────────────────────────────────────────────────────────
def run_analysis(force: bool = False) -> None:
    """
    APScheduler 가 매일 09:30 에 호출.
    force=True 이면 이미 실행된 날도 재분석.
    """
    global _last_run_date

    date = _today()
    logger.info(f"[WORKER] 분석 시작 ({date})")

    # 1. 당일 in-process 중복 방지
    if not force and _last_run_date == date:
        logger.info(f"[SKIP] 오늘({date}) 이미 실행됨")
        return

    rd = _get_rd()
    try:
        rd.ping()
    except Exception as e:
        logger.error(f"[WORKER] Redis 연결 실패: {e}")
        return

    # 2. Redis에 당일 결과가 이미 있으면 스킵
    if not force and rd.exists(f"webnews:{date}:sentiment:updated_at"):
        logger.info(f"[SKIP] 오늘({date}) 결과가 Redis에 이미 존재")
        _last_run_date = date
        return

    # 3. FinBERT 로딩 (싱글턴 → 최초 1회만 느림)
    logger.info(f"[WORKER] FinBERT 로딩 중... (경로: {_ANALYZER_DIR})")
    try:
        analyzer = _load_analyzer()
    except Exception as e:
        logger.error(f"[WORKER] analyzer 로딩 실패: {e}")
        return
    logger.info(f"[WORKER] 모델 로딩 완료 (device: {analyzer.device})")

    # 4. 카테고리별 분석
    categories = _scan_categories(rd, date)
    logger.info(f"[WORKER] 카테고리: {categories}")

    results: list[dict] = []
    for cat in categories:
        t0 = time.time()
        try:
            result = _analyze_category(rd, analyzer, date, cat)
        except Exception as e:
            logger.error(f"[WORKER] [{cat}] 분석 실패: {e}")
            continue
        elapsed = round(time.time() - t0, 1)
        logger.info(
            f"  [{cat}] {result['item_count']}개 | "
            f"avg={result['avg_sentiment_score']} | {elapsed}s"
        )
        results.append(result)

    # 5. 저장
    if results:
        _save(rd, date, results)

    _last_run_date = date
    logger.info("[WORKER] 완료")
