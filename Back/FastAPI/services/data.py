"""
services/data.py
================
DuckDB 쿼리 레이어 + Redis 캐시 래퍼.

- 모든 public 함수는 model_version 파라미터를 받음.
- "latest" 전달 시 scores 테이블에서 가장 최근 inserted_at 의 버전을 자동 선택.
- Redis 캐시 TTL은 config.REDIS_CACHE_TTL (기본 60초).
  Redis 연결 실패 시 캐시 없이 DuckDB 직접 조회로 graceful fallback.
"""

from __future__ import annotations

import json
import hashlib
from typing import Any

import duckdb
import pandas as pd

try:
    import redis as _redis_lib
    _REDIS_OK = True
except ImportError:
    _REDIS_OK = False

from ..core.config import DUCKDB_PATH, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_CACHE_TTL

# ── Redis 연결 (싱글턴, 실패 허용) ───────────────────────────────────────────

_redis_client: Any = None

def _get_redis():
    global _redis_client
    if not _REDIS_OK:
        return None
    if _redis_client is None:
        try:
            _redis_client = _redis_lib.Redis(
                host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                decode_responses=True, socket_connect_timeout=1,
            )
            _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


def _cache_key(fn_name: str, **kwargs) -> str:
    raw = json.dumps({"fn": fn_name, **kwargs}, sort_keys=True, default=str)
    return "ml_api:" + hashlib.md5(raw.encode()).hexdigest()


def _cached(fn_name: str, fetch_fn, ttl: int = REDIS_CACHE_TTL, **kwargs):
    """Redis 캐시 래퍼. 직렬화는 JSON."""
    r = _get_redis()
    key = _cache_key(fn_name, **kwargs)
    if r:
        try:
            hit = r.get(key)
            if hit:
                return json.loads(hit)
        except Exception:
            pass

    result = fetch_fn()

    if r:
        try:
            r.setex(key, ttl, json.dumps(result, default=str))
        except Exception:
            pass
    return result


# ── DuckDB 헬퍼 ───────────────────────────────────────────────────────────────

def _con() -> duckdb.DuckDBPyConnection:
    """읽기 전용 DuckDB 연결 (요청마다 새로 열고 닫음 — DuckDB read_only 동시성 안전)."""
    return duckdb.connect(str(DUCKDB_PATH), read_only=True)


def _resolve_version(model_version: str) -> str:
    """'latest' → 실제 버전 문자열 변환."""
    if model_version != "latest":
        return model_version
    con = _con()
    row = con.execute(
        "SELECT model_version FROM scores ORDER BY inserted_at DESC LIMIT 1"
    ).fetchone()
    con.close()
    if row is None:
        raise RuntimeError("scores 테이블이 비어 있습니다. precompute_scores.py 를 먼저 실행하세요.")
    return row[0]


# ── Public API ────────────────────────────────────────────────────────────────

def get_available_dates(model_version: str = "latest") -> list[str]:
    """scores 테이블에 있는 날짜 목록(오름차순)."""
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()
        rows = con.execute(
            "SELECT DISTINCT CAST(date AS VARCHAR) FROM scores WHERE model_version=? ORDER BY 1",
            [ver],
        ).fetchall()
        con.close()
        return [r[0] for r in rows]

    return _cached("available_dates", fetch, model_version=ver)


def get_available_versions() -> list[str]:
    """적재된 model_version 목록."""
    def fetch():
        con = _con()
        rows = con.execute(
            "SELECT DISTINCT model_version FROM scores ORDER BY inserted_at"
        ).fetchall()
        con.close()
        return [r[0] for r in rows]
    return _cached("available_versions", fetch, ttl=300)


def get_recommendations(
    date: str | None = None,
    model_version: str = "latest",
    sector: str | None = None,
    top_k: int = 20,
    min_score: float = 0.0,
) -> list[dict]:
    """
    날짜별 종목 추천 목록 (score 내림차순).

    - date=None → 가장 최신 날짜
    - top_k=0   → 전체 반환
    """
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()

        # 날짜 결정
        _date = date
        if _date is None:
            row = con.execute(
                "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version=?", [ver]
            ).fetchone()
            _date = row[0] if row else None

        if _date is None:
            con.close()
            return []

        conditions = ["model_version = ?", "CAST(date AS VARCHAR) = ?", "score >= ?"]
        params: list = [ver, _date, min_score]

        if sector:
            conditions.append("sector = ?")
            params.append(sector)

        limit_clause = f"LIMIT {int(top_k)}" if top_k > 0 else ""

        sql = f"""
            SELECT
                CAST(date AS VARCHAR)   AS date,
                ticker,
                name,
                sector,
                mid_sector,
                close,
                ROUND(prob_lgbm, 6)     AS prob_lgbm,
                ROUND(prob_xgb,  6)     AS prob_xgb,
                ROUND(prob_cat,  6)     AS prob_cat,
                ROUND(prob_ensemble, 6)         AS prob_ensemble,
                ROUND(CAST(score AS DOUBLE), 1) AS score,
                tier,
                rank_in_date,
                total_in_date,
                model_version
            FROM scores
            WHERE {' AND '.join(conditions)}
            ORDER BY score DESC
            {limit_clause}
        """
        rows = con.execute(sql, params).fetchdf()
        con.close()
        return rows.to_dict(orient="records")

    return _cached(
        "recommendations", fetch,
        date=date, model_version=ver,
        sector=sector, top_k=top_k, min_score=min_score,
    )


def get_stock_history(
    ticker: str,
    model_version: str = "latest",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """특정 종목의 날짜별 스코어 이력."""
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()
        conditions = ["model_version = ?", "ticker = ?"]
        params: list = [ver, ticker.zfill(6)]

        if start_date:
            conditions.append("CAST(date AS VARCHAR) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("CAST(date AS VARCHAR) <= ?")
            params.append(end_date)

        sql = f"""
            SELECT
                CAST(date AS VARCHAR) AS date,
                ticker,
                name,
                sector,
                close,
                ROUND(prob_ensemble, 6)         AS prob_ensemble,
                ROUND(CAST(score AS DOUBLE), 1) AS score,
                tier,
                rank_in_date,
                total_in_date,
                model_version
            FROM scores
            WHERE {' AND '.join(conditions)}
            ORDER BY date
        """
        rows = con.execute(sql, params).fetchdf()
        con.close()
        return rows.to_dict(orient="records")

    return _cached(
        "stock_history", fetch,
        ticker=ticker, model_version=ver,
        start_date=start_date, end_date=end_date,
    )


def get_sector_summary(
    date: str | None = None,
    model_version: str = "latest",
) -> list[dict]:
    """섹터별 평균 점수 요약 (특정 날짜 기준)."""
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()

        _date = date
        if _date is None:
            row = con.execute(
                "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version=?", [ver]
            ).fetchone()
            _date = row[0] if row else None

        if _date is None:
            con.close()
            return []

        sql = """
            SELECT
                COALESCE(sector, '미분류') AS sector,
                COUNT(*)                   AS stock_count,
                ROUND(AVG(score), 1)       AS avg_score,
                ROUND(MAX(score), 1)       AS max_score,
                ROUND(MIN(score), 1)       AS min_score,
                SUM(CASE WHEN tier='A' THEN 1 ELSE 0 END) AS tier_a_count,
                CAST(date AS VARCHAR)      AS date,
                model_version
            FROM scores
            WHERE model_version = ? AND CAST(date AS VARCHAR) = ?
            GROUP BY sector, date, model_version
            ORDER BY avg_score DESC
        """
        rows = con.execute(sql, [ver, _date]).fetchdf()
        con.close()
        return rows.to_dict(orient="records")

    return _cached("sector_summary", fetch, date=date, model_version=ver)


def get_backtest_monthly_returns(version: str = "v7_v8") -> list[dict]:
    """v7·v8 백테스트 월별 수익률 (CSV 파일에서 읽음)."""
    from ..core.config import WF_MONTHLY_RETURNS_CSV, V7_COMPARISON_CSV
    import os

    def fetch():
        results: list[dict] = []

        if os.path.exists(WF_MONTHLY_RETURNS_CSV):
            df = pd.read_csv(WF_MONTHLY_RETURNS_CSV)
            df["source"] = "v8_walk_forward"
            results.extend(df.to_dict(orient="records"))

        if os.path.exists(V7_COMPARISON_CSV):
            df = pd.read_csv(V7_COMPARISON_CSV)
            results.append({"source": "comparison_summary", "data": df.to_dict(orient="records")})

        return results

    return _cached("backtest_monthly", fetch, ttl=600, version=version)


def get_backtest_summary() -> dict:
    """v7·v8 백테스트 성과 요약."""
    from ..core.config import WF_PERFORMANCE_TXT, V7_COMPARISON_CSV
    import os

    def fetch():
        out: dict = {}

        if os.path.exists(WF_PERFORMANCE_TXT):
            with open(WF_PERFORMANCE_TXT, encoding="utf-8") as f:
                out["v8_walk_forward"] = f.read()

        if os.path.exists(V7_COMPARISON_CSV):
            df = pd.read_csv(V7_COMPARISON_CSV)
            out["comparison"] = df.to_dict(orient="records")

        return out

    return _cached("backtest_summary", fetch, ttl=600)
