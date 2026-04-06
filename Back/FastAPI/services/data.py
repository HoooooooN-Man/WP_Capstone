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
import threading
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
import time as _time

_redis_client: Any = None
_redis_last_fail: float = 0.0
_REDIS_RETRY_INTERVAL = 30.0  # 실패 후 30초간 재시도 안 함


def _get_redis():
    global _redis_client, _redis_last_fail
    if not _REDIS_OK:
        return None
    # 이미 연결됨
    if _redis_client is not None:
        return _redis_client
    # 최근에 실패한 경우 재시도 억제
    if _time.time() - _redis_last_fail < _REDIS_RETRY_INTERVAL:
        return None
    try:
        _redis_client = _redis_lib.Redis(
            host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        _redis_client.ping()
    except Exception:
        _redis_client = None
        _redis_last_fail = _time.time()
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

_duckdb_con: duckdb.DuckDBPyConnection | None = None
_duckdb_lock = threading.Lock()


def init_duckdb() -> None:
    """앱 시작 시(lifespan) 한 번만 호출 — 파일 열기 + 워밍업 쿼리로 첫 요청 지연 제거."""
    global _duckdb_con
    with _duckdb_lock:
        if _duckdb_con is None:
            _duckdb_con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    # 전체 컬럼을 샘플 조회하여 OS 파일 캐시 확보 (컬럼 스토리지 워밍업)
    con = _duckdb_con
    con.execute("SELECT * FROM finance  LIMIT 500").fetchdf()
    con.execute("SELECT * FROM scores   LIMIT 500").fetchdf()
    con.execute("SELECT * FROM prices   LIMIT 500").fetchdf()


def _con() -> duckdb.DuckDBPyConnection:
    """읽기 전용 DuckDB 싱글턴 연결.
    init_duckdb() 이후 항상 동일한 연결 객체를 반환.
    동시 read는 DuckDB read_only에서 안전하다.
    """
    global _duckdb_con
    if _duckdb_con is None:
        with _duckdb_lock:
            if _duckdb_con is None:
                _duckdb_con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    return _duckdb_con


def _resolve_version(model_version: str) -> str:
    """'latest' → 실제 버전 문자열 변환."""
    if model_version != "latest":
        return model_version
    con = _con()
    row = con.execute(
        "SELECT model_version FROM scores ORDER BY inserted_at DESC LIMIT 1"
    ).fetchone()
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
        return [r[0] for r in rows]

    return _cached("available_dates", fetch, model_version=ver)


def get_available_versions() -> list[str]:
    """적재된 model_version 목록."""
    def fetch():
        con = _con()
        rows = con.execute(
            "SELECT DISTINCT model_version FROM scores ORDER BY inserted_at"
        ).fetchall()
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
        return rows.to_dict(orient="records")

    return _cached("sector_summary", fetch, date=date, model_version=ver)


def search_stocks(
    q: str,
    model_version: str = "latest",
    limit: int = 20,
) -> list[dict]:
    """티커·회사명 키워드 검색 — 최신 날짜 ML 점수 포함."""
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()
        keyword = f"%{q}%"
        sql = """
            SELECT
                s.ticker,
                s.name,
                s.sector,
                s.mid_sector,
                ROUND(CAST(s.score AS DOUBLE), 1) AS score,
                s.tier,
                s.model_version,
                CAST(s.date AS VARCHAR) AS latest_date
            FROM scores s
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date
                FROM scores
                WHERE model_version = ?
                GROUP BY ticker
            ) latest ON s.ticker = latest.ticker AND s.date = latest.max_date
            WHERE s.model_version = ?
              AND (s.ticker ILIKE ? OR s.name ILIKE ?)
            ORDER BY s.score DESC
            LIMIT ?
        """
        rows = con.execute(sql, [ver, ver, keyword, keyword, limit]).fetchdf()
        return rows.to_dict(orient="records")

    return _cached("search", fetch, ttl=120, q=q, model_version=ver, limit=limit)


def get_chart(ticker: str, period: str = "1y") -> dict | None:
    """OHLCV + 이동평균 데이터. period: 1m|3m|6m|1y|3y|all"""
    from datetime import date as _date, timedelta
    PERIOD_DAYS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "3y": 1095, "all": 0}
    days = PERIOD_DAYS.get(period, 365)

    def fetch():
        con = _con()
        t = ticker.zfill(6)

        # 이름 조회 (scores 테이블에서)
        name_row = con.execute(
            "SELECT name FROM scores WHERE ticker=? LIMIT 1", [t]
        ).fetchone()
        name = name_row[0] if name_row else None

        # prices.date 는 VARCHAR 'YYYY-MM-DD' — 최신 날짜 기준 N일 전부터 조회
        if days > 0:
            # 데이터 최신 날짜를 먼저 구해 상대적으로 절단
            max_row = con.execute(
                "SELECT MAX(date) FROM prices WHERE ticker=?", [t]
            ).fetchone()
            if max_row and max_row[0]:
                from datetime import datetime
                max_date = datetime.strptime(str(max_row[0]), "%Y-%m-%d").date()
                cutoff = (max_date - timedelta(days=days)).strftime("%Y-%m-%d")
            else:
                cutoff = (_date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
            date_cond = f"AND date >= '{cutoff}'"
        else:
            date_cond = ""

        sql = f"""
            SELECT
                date,
                open, high, low, close, volume, amount, market_cap,
                ma5, ma20, ma60, ma120
            FROM prices
            WHERE ticker = ? {date_cond}
            ORDER BY date ASC
        """
        rows = con.execute(sql, [t]).fetchdf()

        if rows.empty:
            return None

        return {
            "ticker": t,
            "name":   name,
            "items":  rows.to_dict(orient="records"),
        }

    return _cached("chart", fetch, ttl=300, ticker=ticker, period=period)


def get_finance(ticker: str, limit: int = 20) -> tuple[list[dict], str | None]:
    """분기별 재무 이력 (최신순 N개)."""
    def fetch():
        con = _con()
        t = ticker.zfill(6)
        sql = """
            SELECT
                year, quarter, base_date, market_cap,
                per, pbr, eps, bps, dps, dividend_yield,
                op_margin, net_margin, roe, debt_ratio, current_ratio,
                revenue, op_profit, net_profit,
                equity, total_debt, current_assets, current_liab,
                rev_growth_yoy, rev_growth_qoq, op_growth_yoy, op_growth_qoq,
                finance_score, name
            FROM finance
            WHERE ticker = ?
            ORDER BY year DESC, quarter DESC
            LIMIT ?
        """
        rows = con.execute(sql, [t, limit]).fetchdf()
        if rows.empty:
            return [], None
        name = rows["name"].iloc[0] if "name" in rows.columns else None
        data_rows = rows.drop(columns=["name"]).to_dict(orient="records")
        return data_rows, name

    result = _cached("finance", fetch, ttl=600, ticker=ticker, limit=limit)
    if isinstance(result, list):
        return result, None
    return result


def get_finance_latest(ticker: str) -> dict | None:
    """가장 최근 분기 재무 요약."""
    def fetch():
        con = _con()
        t = ticker.zfill(6)
        sql = """
            SELECT
                ticker, name, year, quarter, base_date,
                per, pbr, eps, roe, debt_ratio, op_margin,
                rev_growth_yoy, finance_score
            FROM finance
            WHERE ticker = ?
            ORDER BY year DESC, quarter DESC
            LIMIT 1
        """
        row = con.execute(sql, [t]).fetchdf()
        if row.empty:
            return None
        return row.to_dict(orient="records")[0]

    return _cached("finance_latest", fetch, ttl=600, ticker=ticker)


def screen_stocks(
    model_version: str = "latest",
    min_score: float = 0.0,
    tier: str | None = None,
    sector: str | None = None,
    max_per: float | None = None,
    max_pbr: float | None = None,
    min_roe: float | None = None,
    max_debt_ratio: float | None = None,
    min_op_margin: float | None = None,
    min_rev_growth: float | None = None,
    min_finance_score: float | None = None,
    sort_by: str = "composite_score",
    limit: int = 50,
) -> list[dict]:
    """ML 점수 + 재무 조건 복합 스크리너."""
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()

        # 최신 날짜 결정
        latest_date_row = con.execute(
            "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version=?", [ver]
        ).fetchone()
        latest_date = latest_date_row[0] if latest_date_row else None

        if latest_date is None:
            return []

        # 최신 재무 분기 서브쿼리
        finance_sub = """
            SELECT
                f.ticker, f.name AS finance_name,
                f.per, f.pbr, f.roe, f.debt_ratio, f.op_margin,
                f.rev_growth_yoy, f.finance_score
            FROM finance f
            INNER JOIN (
                SELECT ticker, MAX(year*10+quarter) AS max_yq
                FROM finance GROUP BY ticker
            ) lf ON f.ticker = lf.ticker AND (f.year*10+f.quarter) = lf.max_yq
        """

        ml_conditions = ["s.model_version = ?", "CAST(s.date AS VARCHAR) = ?", "s.score >= ?"]
        params: list = [ver, latest_date, min_score]

        if tier:
            ml_conditions.append("s.tier = ?")
            params.append(tier.upper())
        if sector:
            ml_conditions.append("s.sector ILIKE ?")
            params.append(f"%{sector}%")

        finance_conditions = []
        if max_per is not None:
            finance_conditions.append(f"fi.per <= {float(max_per)}")
        if max_pbr is not None:
            finance_conditions.append(f"fi.pbr <= {float(max_pbr)}")
        if min_roe is not None:
            finance_conditions.append(f"fi.roe >= {float(min_roe)}")
        if max_debt_ratio is not None:
            finance_conditions.append(f"fi.debt_ratio <= {float(max_debt_ratio)}")
        if min_op_margin is not None:
            finance_conditions.append(f"fi.op_margin >= {float(min_op_margin)}")
        if min_rev_growth is not None:
            finance_conditions.append(f"fi.rev_growth_yoy >= {float(min_rev_growth)}")
        if min_finance_score is not None:
            finance_conditions.append(f"fi.finance_score >= {float(min_finance_score)}")

        finance_where = ""
        if finance_conditions:
            finance_where = "AND " + " AND ".join(finance_conditions)

        ALLOWED_SORT = {"composite_score", "score", "finance_score", "roe", "per", "pbr", "rev_growth_yoy"}
        sort_col = sort_by if sort_by in ALLOWED_SORT else "composite_score"

        sql = f"""
            SELECT
                s.ticker,
                COALESCE(s.name, fi.finance_name)   AS name,
                s.sector,
                ROUND(CAST(s.score AS DOUBLE), 1)   AS score,
                s.tier,
                CAST(s.date AS VARCHAR)              AS latest_date,
                fi.per, fi.pbr, fi.roe, fi.debt_ratio,
                fi.op_margin, fi.rev_growth_yoy,
                ROUND(fi.finance_score, 1)           AS finance_score,
                ROUND(
                    CAST(s.score AS DOUBLE) * 0.6
                    + COALESCE(fi.finance_score, 50.0) * 0.4,
                1)                                   AS composite_score
            FROM scores s
            LEFT JOIN ({finance_sub}) fi ON s.ticker = fi.ticker
            WHERE {' AND '.join(ml_conditions)} {finance_where}
            ORDER BY {sort_col} DESC NULLS LAST
            LIMIT {int(limit)}
        """
        rows = con.execute(sql, params).fetchdf()
        return rows.to_dict(orient="records")

    return _cached(
        "screener", fetch, ttl=120,
        model_version=ver, min_score=min_score, tier=tier, sector=sector,
        max_per=max_per, max_pbr=max_pbr, min_roe=min_roe,
        max_debt_ratio=max_debt_ratio, min_op_margin=min_op_margin,
        min_rev_growth=min_rev_growth, min_finance_score=min_finance_score,
        sort_by=sort_by, limit=limit,
    )


def compare_stocks(
    tickers: list[str],
    model_version: str = "latest",
    period_days: int = 365,
) -> list[dict]:
    """여러 종목 ML 점수 이력 + 최신 재무 비교."""
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()
        results = []

        from datetime import datetime as _dt, timedelta as _timedelta

        # scores 테이블의 최신 날짜 기준으로 period 계산
        max_date_row = con.execute(
            "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version=?", [ver]
        ).fetchone()
        max_date_str = max_date_row[0] if max_date_row and max_date_row[0] else None

        for t in tickers:
            # ML 점수 이력 — scores.date 기준 period 적용
            if period_days > 0 and max_date_str:
                max_date = _dt.strptime(max_date_str, "%Y-%m-%d").date()
                cutoff = (max_date - _timedelta(days=period_days)).strftime("%Y-%m-%d")
                date_cond = f"AND CAST(date AS VARCHAR) >= '{cutoff}'"
            else:
                date_cond = ""

            hist_sql = f"""
                SELECT
                    CAST(date AS VARCHAR) AS date,
                    ROUND(CAST(score AS DOUBLE), 1) AS score,
                    tier, name, sector
                FROM scores
                WHERE ticker = ? AND model_version = ? {date_cond}
                ORDER BY date ASC
            """
            hist = con.execute(hist_sql, [t, ver]).fetchdf()

            name   = hist["name"].iloc[-1]   if not hist.empty and "name"   in hist.columns else None
            sector = hist["sector"].iloc[-1] if not hist.empty and "sector" in hist.columns else None
            latest_score = float(hist["score"].iloc[-1]) if not hist.empty else None
            latest_tier  = str(hist["tier"].iloc[-1])    if not hist.empty else None
            score_history = (
                hist[["date", "score"]].to_dict(orient="records") if not hist.empty else []
            )

            # 최신 재무
            fin_sql = """
                SELECT per, pbr, roe, debt_ratio, op_margin,
                       rev_growth_yoy, finance_score, year, quarter
                FROM finance
                WHERE ticker = ?
                ORDER BY year DESC, quarter DESC
                LIMIT 1
            """
            fin = con.execute(fin_sql, [t]).fetchdf()
            finance = fin.to_dict(orient="records")[0] if not fin.empty else None

            results.append({
                "ticker":        t,
                "name":          name,
                "sector":        sector,
                "latest_score":  latest_score,
                "tier":          latest_tier,
                "score_history": score_history,
                "finance":       finance,
            })

        return results

    return _cached(
        "compare", fetch, ttl=120,
        tickers=",".join(sorted(tickers)), model_version=ver, period_days=period_days,
    )


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
