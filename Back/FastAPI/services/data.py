"""
services/data.py
================
DuckDB 쿼리 레이어 (도메인 함수 + 호환 re-export).

분할 전 1200+ 라인 단일 파일이었으나, 공유 인프라 (Redis/DuckDB/캐시/버전 해석) 는
`services/_core.py` 로 분리됨. 이 모듈은 도메인 함수 본체를 보유하고,
기존 라우터의 `from ..services import data as svc` 임포트 패턴을 유지하기 위해
`_core` 의 헬퍼를 동일 이름으로 노출한다.

향후 추가 분할 후보 (TODO):
  - scores_svc.py  : get_recommendations, get_stock_history, get_sector_summary,
                     search_stocks, screen_stocks, compare_stocks,
                     get_market_regime, get_kospi200_portfolio
  - charts_svc.py  : get_chart, get_stock_price, get_rising_stocks
  - finance_svc.py : get_finance, get_finance_latest
  - backtest_svc.py: get_backtest_*, run_custom_backtest
  - news_svc.py    : get_news_feed, get_news_detail
  - metrics_svc.py : get_model_metrics
"""

from __future__ import annotations

import pandas as pd

from ..core.config import DUCKDB_PATH, NEWS_DUCKDB_PATH, REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_CACHE_TTL
from ._core import (
    init_duckdb,
    con as _con,
    news_con as _news_con,
    cached as _cached,
    cache_key as _cache_key,
    get_redis as _get_redis,
    resolve_version as _resolve_version,
    get_available_dates,
    get_available_versions,
)

# 하위 호환을 위해 ASCII alias 도 노출 (외부 코드가 _con 등을 직접 import 했을 가능성).
__all__ = [
    "init_duckdb",
    "_con",
    "_news_con",
    "_cached",
    "_cache_key",
    "_get_redis",
    "_resolve_version",
    "get_available_dates",
    "get_available_versions",
]


def _norm_optional_str(val: str | None) -> str | None:
    """쿼리·캐시 키용: 빈 문자열과 공백만 있는 값은 None 으로 통일."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


# ── Public API (도메인 함수) ────────────────────────────────────────────────

def _get_kospi_regime(con, ref_date: str, ma_window: int = 20) -> int:
    """
    ref_date 기준 KOSPI 20일 MA 레짐 계산.
    prices 테이블의 삼성전자(005930) 종가를 KOSPI 프록시로 사용.
    Returns: 1=상승(정상), 0=하락(방어)
    """
    try:
        ref_int = int(ref_date.replace("-", ""))
        rows = con.execute(
            """
            SELECT date, close
            FROM prices
            WHERE ticker = '005930' AND date <= ?
            ORDER BY date DESC
            LIMIT ?
            """,
            [ref_int, ma_window * 2],
        ).fetchdf()
        if rows.empty or len(rows) < 5:
            return 1
        rows = rows.sort_values("date")
        ma = rows["close"].rolling(min(ma_window, len(rows)), min_periods=3).mean().iloc[-1]
        last = float(rows["close"].iloc[-1])
        return 1 if last >= ma else 0
    except Exception:
        return 1


def get_recommendations(
    date: str | None = None,
    model_version: str = "latest",
    sector: str | None = None,
    top_k: int = 20,
    min_score: float = 0.0,
    strategy: str = "base",
) -> list[dict]:
    """
    날짜별 종목 추천 목록 (score 내림차순).

    - date=None   → 가장 최신 날짜
    - top_k=0     → 전체 반환
    - strategy    → "base"(기본) | "s3"(v9 S3: prob Top-150 + 레짐 신호 포함)
    """
    date_key = _norm_optional_str(date)
    sector_key = _norm_optional_str(sector)
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()

        # 날짜 결정 — None 또는 빈 문자열이면 최신 날짜 사용
        _date = date_key
        if _date is None:
            row = con.execute(
                "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version=?", [ver]
            ).fetchone()
            _date = row[0] if row else None

        if _date is None:
            return []

        conditions = ["model_version = ?", "CAST(date AS VARCHAR) = ?", "score >= ?"]
        params: list = [ver, _date, min_score]

        if sector_key:
            conditions.append("sector = ?")
            params.append(sector_key)

        # S3 전략: prob 상위 기준, top_k를 150으로 고정
        _top_k = 150 if strategy == "s3" else top_k
        limit_clause = f"LIMIT {int(_top_k)}" if _top_k > 0 else ""

        sql = f"""
            SELECT
                CAST(s.date AS VARCHAR)            AS date,
                s.ticker,
                COALESCE(s.name, st.name)          AS name,
                COALESCE(s.sector, st.wics_large_name) AS sector,
                s.mid_sector,
                s.close,
                ROUND(s.prob_lgbm, 6)              AS prob_lgbm,
                ROUND(s.prob_xgb,  6)              AS prob_xgb,
                ROUND(s.prob_cat,  6)              AS prob_cat,
                ROUND(s.prob_ensemble, 6)          AS prob_ensemble,
                ROUND(CAST(s.score AS DOUBLE), 1)  AS score,
                s.tier,
                s.rank_in_date,
                s.total_in_date,
                s.model_version
            FROM scores s
            LEFT JOIN stocks st ON s.ticker = st.ticker
            WHERE {' AND '.join(conditions)}
            ORDER BY s.score DESC
            {limit_clause}
        """
        rows = con.execute(sql, params).fetchdf()
        result = rows.to_dict(orient="records")

        # S3 전략: 레짐 신호를 각 종목에 메타데이터로 부착
        if strategy == "s3":
            regime = _get_kospi_regime(con, _date)
            for r in result:
                r["regime"] = regime
                r["regime_label"] = "상승" if regime == 1 else "하락(방어)"
                # 하락 구간 경고: 실제 포지션 축소는 클라이언트 측에서 처리
                r["position_scale"] = 1.0 if regime == 1 else 0.5

        return result

    return _cached(
        "recommendations", fetch,
        date=date_key, model_version=ver,
        sector=sector_key, top_k=top_k, min_score=min_score, strategy=strategy,
    )


def get_stock_history(
    ticker: str,
    model_version: str = "latest",
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """특정 종목의 날짜별 스코어 이력."""
    ver = _resolve_version(model_version)
    t_hist = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        conditions = ["s.model_version = ?", "s.ticker = ?"]
        params: list = [ver, t_hist]

        if start_date:
            conditions.append("CAST(s.date AS VARCHAR) >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("CAST(s.date AS VARCHAR) <= ?")
            params.append(end_date)

        sql = f"""
            SELECT
                CAST(s.date AS VARCHAR)                AS date,
                s.ticker,
                COALESCE(s.name, st.name)              AS name,
                COALESCE(s.sector, st.wics_large_name) AS sector,
                s.close,
                ROUND(s.prob_ensemble, 6)              AS prob_ensemble,
                ROUND(CAST(s.score AS DOUBLE), 1)      AS score,
                s.tier,
                s.rank_in_date,
                s.total_in_date,
                s.model_version
            FROM scores s
            LEFT JOIN stocks st ON s.ticker = st.ticker
            WHERE {' AND '.join(conditions)}
            ORDER BY s.date
        """
        rows = con.execute(sql, params).fetchdf()
        return rows.to_dict(orient="records")

    return _cached(
        "stock_history", fetch,
        ticker=t_hist, model_version=ver,
        start_date=start_date, end_date=end_date,
    )


def get_sector_summary(
    date: str | None = None,
    model_version: str = "latest",
) -> list[dict]:
    """섹터별 평균 점수 요약 (특정 날짜 기준)."""
    date_key = _norm_optional_str(date)
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()

        _date = date_key
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

    return _cached("sector_summary", fetch, date=date_key, model_version=ver)


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
    """OHLCV + 이동평균(Python rolling). period: 1m|3m|6m|1y|3y|all

    - prices.date 는 BIGINT YYYYMMDD 형식
    - ma5/20/60/120 컬럼이 DB에 없어 Python 측에서 close 기준 SMA를 산출
    """
    from datetime import date as _date, timedelta, datetime as _dt
    PERIOD_DAYS = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "3y": 1095, "all": 0}
    days = PERIOD_DAYS.get(period, 365)

    def fetch():
        con = _con()
        t = t_chart

        name_row = con.execute(
            "SELECT name FROM stocks WHERE ticker=? LIMIT 1", [t]
        ).fetchone()
        if not name_row or not name_row[0]:
            name_row = con.execute("SELECT name FROM scores WHERE ticker=? LIMIT 1", [t]).fetchone()
        name = name_row[0] if name_row else None

        # 최신 날짜 기준으로 cutoff(YYYYMMDD) 계산
        if days > 0:
            max_row = con.execute(
                "SELECT MAX(date) FROM prices WHERE ticker=?", [t]
            ).fetchone()
            if max_row and max_row[0]:
                max_date = _dt.strptime(str(int(max_row[0])), "%Y%m%d").date()
            else:
                max_date = _date.today()
            cutoff_int = int((max_date - timedelta(days=days)).strftime("%Y%m%d"))
            date_cond = "AND date >= ?"
            params = [t, cutoff_int]
        else:
            date_cond = ""
            params = [t]

        sql = f"""
            SELECT
                date,
                open, high, low, close, volume, amount, market_cap
            FROM prices
            WHERE ticker = ? {date_cond}
            ORDER BY date ASC
        """
        rows = con.execute(sql, params).fetchdf()
        if rows.empty:
            return None

        # 이동평균 계산
        for w in (5, 20, 60, 120):
            rows[f"ma{w}"] = rows["close"].rolling(window=w, min_periods=1).mean().round(2)

        # date(BIGINT YYYYMMDD) → 'YYYY-MM-DD' 문자열 변환
        rows["date"] = rows["date"].apply(lambda d: f"{int(d)//10000:04d}-{(int(d)//100)%100:02d}-{int(d)%100:02d}")

        return {
            "ticker": t,
            "name":   name,
            "items":  rows.to_dict(orient="records"),
        }

    t_chart = str(ticker or "").strip().zfill(6)
    return _cached("chart", fetch, ttl=300, ticker=t_chart, period=period)


def get_finance(ticker: str, limit: int = 20) -> tuple[list[dict], str | None]:
    """분기별 재무 이력 (최신순 N개).

    Redis 에 (rows, name) 튜플을 JSON 직렬화하면 역직렬화 시 list 가 되어
    클라이언트에 잘못 전달될 수 있으므로 dict 로만 캐시한다.
    """
    tkey = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        t = tkey
        sql = """
            SELECT
                f.year, f.quarter, f.base_date, f.market_cap,
                f.per, f.pbr, f.eps, f.bps, f.dps, f.dividend_yield,
                f.op_margin, f.net_margin, f.roe, f.debt_ratio, f.current_ratio,
                f.revenue, f.op_profit, f.net_profit,
                f.equity, f.total_debt, f.current_assets, f.current_liab,
                f.rev_growth_yoy, f.rev_growth_qoq, f.op_growth_yoy, f.op_growth_qoq,
                f.finance_score,
                COALESCE(f.name, st.name) AS name
            FROM finance f
            LEFT JOIN stocks st ON f.ticker = st.ticker
            WHERE f.ticker = ?
            ORDER BY f.year DESC, f.quarter DESC
            LIMIT ?
        """
        rows = con.execute(sql, [t, limit]).fetchdf()
        if rows.empty:
            return {"rows": [], "name": None}
        name_val = rows["name"].iloc[0] if "name" in rows.columns else None
        # base_date: float(YYYYMMDD.0) → 'YYYYMMDD' 문자열 (스키마 호환)
        if "base_date" in rows.columns:
            rows["base_date"] = rows["base_date"].apply(
                lambda v: str(int(v)) if pd.notna(v) else None
            )
        data_rows = rows.drop(columns=["name"]).to_dict(orient="records")
        return {"rows": data_rows, "name": name_val}

    result = _cached("finance_v2", fetch, ttl=600, ticker=tkey, limit=int(limit))
    if not isinstance(result, dict):
        return [], None
    return result.get("rows") or [], result.get("name")


def get_finance_latest(ticker: str) -> dict | None:
    """가장 최근 분기 재무 요약."""
    tkey = str(ticker or "").strip().zfill(6)

    def fetch():
        con = _con()
        t = tkey
        sql = """
            SELECT
                f.ticker,
                COALESCE(f.name, st.name) AS name,
                f.year, f.quarter, f.base_date,
                f.per, f.pbr, f.eps, f.roe, f.debt_ratio, f.op_margin,
                f.rev_growth_yoy, f.finance_score
            FROM finance f
            LEFT JOIN stocks st ON f.ticker = st.ticker
            WHERE f.ticker = ?
            ORDER BY f.year DESC, f.quarter DESC
            LIMIT 1
        """
        row = con.execute(sql, [t]).fetchdf()
        if row.empty:
            return None
        if "base_date" in row.columns:
            row["base_date"] = row["base_date"].apply(
                lambda v: str(int(v)) if pd.notna(v) else None
            )
        return row.to_dict(orient="records")[0]

    return _cached("finance_latest", fetch, ttl=600, ticker=tkey)


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


def get_stock_price(ticker: str) -> dict | None:
    """종목 최신 현재가 (prices 테이블 마지막 행)."""
    def fetch():
        con = _con()
        t = ticker.zfill(6)
        row = con.execute(
            """
            SELECT ticker, date, open, high, low, close, volume
            FROM prices
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 1
            """,
            [t],
        ).fetchone()
        if row is None:
            return None
        # 종목명을 scores 에서 조회
        name_row = con.execute(
            "SELECT name FROM scores WHERE ticker=? LIMIT 1", [t]
        ).fetchone()
        return {
            "ticker":        row[0],
            "date":          str(row[1]),
            "open":          float(row[2]) if row[2] else None,
            "high":          float(row[3]) if row[3] else None,
            "low":           float(row[4]) if row[4] else None,
            "close":         float(row[5]) if row[5] else None,
            "current_price": float(row[5]) if row[5] else None,
            "volume":        int(row[6])   if row[6] else None,
            "name":          name_row[0]   if name_row else None,
        }

    return _cached("stock_price", fetch, ttl=60, ticker=ticker)


def get_rising_stocks(
    model_version: str = "latest",
    limit: int = 20,
) -> dict:
    """최신 날짜 기준 전일 대비 ML 점수 급상승 종목."""
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()
        # 최신 2개 날짜 조회
        dates_row = con.execute(
            """
            SELECT DISTINCT CAST(date AS VARCHAR)
            FROM scores
            WHERE model_version = ?
            ORDER BY 1 DESC
            LIMIT 2
            """,
            [ver],
        ).fetchall()

        if len(dates_row) < 2:
            # 날짜가 1개뿐이면 오늘 데이터만 반환 (score_change = 0)
            today = dates_row[0][0] if dates_row else None
            if not today:
                return {"date": "", "model_version": ver, "total": 0, "items": []}
            rows = con.execute(
                """
                SELECT ticker, name, sector,
                       ROUND(CAST(score AS DOUBLE),1) AS score,
                       ROUND(CAST(score AS DOUBLE),1) AS score_prev,
                       0.0 AS score_change,
                       tier, CAST(date AS VARCHAR) AS date, model_version
                FROM scores
                WHERE model_version = ? AND CAST(date AS VARCHAR) = ?
                ORDER BY score DESC
                LIMIT ?
                """,
                [ver, today, limit],
            ).fetchdf()
            items = rows.to_dict(orient="records")
            return {"date": today, "model_version": ver, "total": len(items), "items": items}

        today, yesterday = dates_row[0][0], dates_row[1][0]

        sql = """
            SELECT
                t.ticker,
                t.name,
                t.sector,
                ROUND(CAST(t.score  AS DOUBLE), 1) AS score,
                ROUND(CAST(y.score  AS DOUBLE), 1) AS score_prev,
                ROUND(CAST(t.score - y.score AS DOUBLE), 1) AS score_change,
                t.tier,
                CAST(t.date AS VARCHAR) AS date,
                t.model_version
            FROM scores t
            JOIN scores y
              ON t.ticker = y.ticker
             AND t.model_version = y.model_version
            WHERE t.model_version = ?
              AND CAST(t.date AS VARCHAR) = ?
              AND CAST(y.date AS VARCHAR) = ?
            ORDER BY score_change DESC
            LIMIT ?
        """
        rows = con.execute(sql, [ver, today, yesterday, limit]).fetchdf()
        items = rows.to_dict(orient="records")
        return {"date": today, "model_version": ver, "total": len(items), "items": items}

    return _cached("rising_stocks", fetch, ttl=300, model_version=ver, limit=limit)


def run_custom_backtest(
    min_score:     float = 60.0,
    top_k:         int   = 20,
    rebalance:     str   = "monthly",
    start_date:    str   = "2023-01-01",
    end_date:      str   = "2024-12-31",
    model_version: str   = "latest",
) -> dict:
    """
    커스텀 백테스트 시뮬레이션.
    scores + prices 테이블을 사용해 월/분기 리밸런싱 전략을 시뮬레이션합니다.
    """
    from datetime import datetime as _dt, timedelta as _td
    import math

    ver = _resolve_version(model_version)
    # prices.date 는 BIGINT YYYYMMDD 형식 — 비교용 정수 키 준비
    start_int = int(start_date.replace("-", ""))
    end_int   = int(end_date.replace("-", ""))

    def _bigint_to_iso(d) -> str:
        s = str(int(d))
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"

    def fetch():
        con = _con()

        # 날짜 범위 내 scores 조회
        scores_df = con.execute(
            """
            SELECT CAST(date AS VARCHAR) AS date, ticker,
                   ROUND(CAST(score AS DOUBLE), 1) AS score, tier
            FROM scores
            WHERE model_version = ?
              AND CAST(date AS VARCHAR) BETWEEN ? AND ?
            ORDER BY date, score DESC
            """,
            [ver, start_date, end_date],
        ).fetchdf()

        if scores_df.empty:
            raise RuntimeError("해당 기간의 scores 데이터가 없습니다.")

        # 리밸런싱 주기 결정 (월/분기 첫 번째 데이터 날짜 사용)
        dates = sorted(scores_df["date"].unique())
        rebalance_dates = []
        last_ym = None
        for d in dates:
            dt = _dt.strptime(d, "%Y-%m-%d")
            if rebalance == "quarterly":
                key = (dt.year, (dt.month - 1) // 3)
            else:
                key = (dt.year, dt.month)
            if key != last_ym:
                rebalance_dates.append(d)
                last_ym = key

        # 각 리밸런싱 날짜에서 포트폴리오 구성
        portfolio_dates = []
        for rd in rebalance_dates:
            day_df = scores_df[scores_df["date"] == rd]
            eligible = day_df[day_df["score"] >= min_score].head(int(top_k))
            if not eligible.empty:
                portfolio_dates.append((rd, eligible["ticker"].tolist()))

        if not portfolio_dates:
            raise RuntimeError("조건에 맞는 종목이 없습니다. min_score를 낮춰보세요.")

        # prices 테이블에서 KOSPI 대용 종목(삼성전자 005930) 및 보유 종목 가격 조회
        all_tickers = list({t for _, tickers in portfolio_dates for t in tickers})
        all_tickers_str = ", ".join(f"'{t.zfill(6)}'" for t in all_tickers)
        prices_df = con.execute(
            f"""
            SELECT ticker, date, close
            FROM prices
            WHERE ticker IN ({all_tickers_str})
              AND date BETWEEN ? AND ?
            ORDER BY date
            """,
            [start_int, end_int],
        ).fetchdf()
        if not prices_df.empty:
            prices_df["date"] = prices_df["date"].apply(_bigint_to_iso)

        # KOSPI 벤치마크 (삼성전자 수익률 대용)
        benchmark_ticker = "005930"
        bench_df = con.execute(
            """
            SELECT date, close
            FROM prices
            WHERE ticker = ?
              AND date BETWEEN ? AND ?
            ORDER BY date
            """,
            [benchmark_ticker, start_int, end_int],
        ).fetchdf()
        if not bench_df.empty:
            bench_df["date"] = bench_df["date"].apply(_bigint_to_iso)

        # 월별 수익률 계산
        monthly_returns = []
        strategy_cum = 100.0
        benchmark_cum = 100.0
        trade_count = 0
        returns_list = []

        for i, (rd, tickers) in enumerate(portfolio_dates):
            next_rd = portfolio_dates[i + 1][0] if i + 1 < len(portfolio_dates) else end_date

            # 전략: 해당 기간 동안 포트폴리오 보유 → 평균 수익률
            period_returns = []
            for ticker in tickers:
                t = ticker.zfill(6)
                t_prices = prices_df[(prices_df["ticker"] == t) &
                                     (prices_df["date"] >= rd) &
                                     (prices_df["date"] <= next_rd)]["close"]
                if len(t_prices) >= 2:
                    ret = (t_prices.iloc[-1] / t_prices.iloc[0] - 1) * 100
                    period_returns.append(ret)
                    trade_count += 1

            strat_ret = sum(period_returns) / len(period_returns) if period_returns else 0.0

            # 벤치마크 수익률
            bench_period = bench_df[(bench_df["date"] >= rd) & (bench_df["date"] <= next_rd)]["close"]
            bench_ret = (bench_period.iloc[-1] / bench_period.iloc[0] - 1) * 100 if len(bench_period) >= 2 else 0.0

            strategy_cum  += strategy_cum  * strat_ret  / 100
            benchmark_cum += benchmark_cum * bench_ret  / 100

            dt = _dt.strptime(rd, "%Y-%m-%d")
            month_label = f"{dt.year % 100:02d}.{dt.month:02d}"
            monthly_returns.append({
                "month":     month_label,
                "strategy":  round(strategy_cum, 2),
                "benchmark": round(benchmark_cum, 2),
            })
            returns_list.append(strat_ret)

        total_return     = round(strategy_cum - 100, 2)
        benchmark_return = round(benchmark_cum - 100, 2)

        # MDD 계산
        peak = 100.0
        mdd  = 0.0
        cum  = 100.0
        for item in monthly_returns:
            cum = item["strategy"]
            if cum > peak:
                peak = cum
            drawdown = (cum - peak) / peak * 100
            if drawdown < mdd:
                mdd = drawdown

        # Sharpe ratio (단순 근사: 평균수익률 / 표준편차)
        if len(returns_list) > 1:
            mean_r = sum(returns_list) / len(returns_list)
            var_r  = sum((r - mean_r) ** 2 for r in returns_list) / len(returns_list)
            std_r  = math.sqrt(var_r) if var_r > 0 else 1e-9
            sharpe = round(mean_r / std_r * (12 ** 0.5), 2)
        else:
            sharpe = 0.0

        win_rate = round(sum(1 for r in returns_list if r > 0) / len(returns_list) * 100, 1) if returns_list else 0.0

        return {
            "total_return":     total_return,
            "benchmark_return": benchmark_return,
            "mdd":              round(mdd, 2),
            "sharpe":           sharpe,
            "win_rate":         win_rate,
            "trade_count":      trade_count,
            "monthly":          monthly_returns,
        }

    return _cached(
        "custom_backtest", fetch, ttl=300,
        model_version=ver, min_score=min_score, top_k=top_k,
        rebalance=rebalance, start_date=start_date, end_date=end_date,
    )


# ── 마켓 레이더 (시장 기상도) ─────────────────────────────────────────────────

def get_market_regime(model_version: str = "latest") -> dict:
    """Tier A 종목 비율로 현재 시장 국면(greed/neutral/fear)을 판단."""
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()
        date_row = con.execute(
            "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version=?",
            [ver],
        ).fetchone()
        latest = date_row[0] if date_row else None
        if not latest:
            raise RuntimeError(f"scores 데이터 없음 (model_version={ver})")

        row = con.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN tier='A' THEN 1 ELSE 0 END) AS tier_a
            FROM scores
            WHERE model_version=? AND CAST(date AS VARCHAR)=?
            """,
            [ver, latest],
        ).fetchone()
        total  = int(row[0] or 0)
        tier_a = int(row[1] or 0)
        ratio  = (tier_a / total * 100) if total else 0.0

        if ratio >= 10:
            status, weather, msg = "greed", "맑음", "상승 모멘텀이 강합니다. 적극적인 투자가 유리한 국면입니다."
        elif ratio >= 5:
            status, weather, msg = "neutral", "흐림", "방향성 탐색 구간입니다. 선별적인 종목 접근이 필요합니다."
        else:
            status, weather, msg = "fear", "비", "시장 변동성이 커지고 있습니다. 현금 비중 확대를 권장합니다."

        return {
            "date":          latest,
            "model_version": ver,
            "total_count":   total,
            "tier_a_count":  tier_a,
            "tier_a_ratio":  round(ratio, 2),
            "status":        status,
            "weather":       weather,
            "message":       msg,
        }

    return _cached("market_regime", fetch, ttl=300, model_version=ver)


# ── KOSPI 200 맞춤형 포트폴리오 ──────────────────────────────────────────────

def get_kospi200_portfolio(
    portfolio_type: str = "growth",
    model_version: str = "latest",
) -> dict:
    """KOSPI 종목 중 사용자 성향에 맞는 Top 10 자동 포트폴리오.

    - growth : score 상위 10
    - stable : Tier A·B + 최신 PBR < 1.5 → score 상위 10
    """
    from ..core.config import SEED_CSV
    ver        = _resolve_version(model_version)
    seed_path  = str(SEED_CSV).replace("\\", "/")
    is_stable  = (portfolio_type == "stable")

    def fetch():
        con = _con()
        row = con.execute(
            "SELECT MAX(CAST(date AS VARCHAR)) FROM scores WHERE model_version=?",
            [ver],
        ).fetchone()
        latest = row[0] if row else None
        if not latest:
            raise RuntimeError(f"scores 데이터 없음 (model_version={ver})")

        if is_stable:
            sql = f"""
                WITH last_finance AS (
                    SELECT ticker, MAX(year * 10 + quarter) AS yq_max
                    FROM finance
                    WHERE pbr IS NOT NULL
                    GROUP BY ticker
                )
                SELECT s.ticker, s.name, s.sector,
                       CAST(s.score AS FLOAT)  AS score,
                       s.tier,
                       CAST(f.pbr   AS FLOAT)  AS pbr
                FROM scores s
                INNER JOIN read_csv_auto('{seed_path}') seed
                    ON s.ticker = LPAD(CAST(seed.ticker AS VARCHAR), 6, '0')
                INNER JOIN last_finance lf
                    ON s.ticker = lf.ticker
                INNER JOIN finance f
                    ON f.ticker = lf.ticker AND (f.year * 10 + f.quarter) = lf.yq_max
                WHERE s.model_version = ?
                  AND CAST(s.date AS VARCHAR) = ?
                  AND seed.exchange = 'KOSPI'
                  AND s.tier IN ('A', 'B')
                  AND f.pbr < 1.5
                ORDER BY s.score DESC
                LIMIT 10
            """
            df = con.execute(sql, [ver, latest]).fetchdf()
        else:  # growth
            sql = f"""
                SELECT s.ticker, s.name, s.sector,
                       CAST(s.score AS FLOAT) AS score,
                       s.tier
                FROM scores s
                INNER JOIN read_csv_auto('{seed_path}') seed
                    ON s.ticker = LPAD(CAST(seed.ticker AS VARCHAR), 6, '0')
                WHERE s.model_version = ?
                  AND CAST(s.date AS VARCHAR) = ?
                  AND seed.exchange = 'KOSPI'
                ORDER BY s.score DESC
                LIMIT 10
            """
            df = con.execute(sql, [ver, latest]).fetchdf()

        items = []
        for i, r in df.iterrows():
            item = {
                "rank":   i + 1,
                "ticker": r["ticker"],
                "name":   r.get("name"),
                "sector": r.get("sector"),
                "score":  float(r["score"]),
                "tier":   r["tier"],
                "pbr":    float(r["pbr"]) if is_stable and pd.notna(r.get("pbr")) else None,
            }
            items.append(item)

        return {
            "type":          portfolio_type,
            "date":          latest,
            "model_version": ver,
            "total":         len(items),
            "items":         items,
        }

    return _cached(
        "kospi200_portfolio", fetch, ttl=300,
        portfolio_type=portfolio_type, model_version=ver,
    )


# ── 뉴스 피드 (FinBERT 감성 분석) ──────────────────────────────────────────────

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


# ── 모델 모니터링 (드리프트 감지) ────────────────────────────────────────────

def get_model_metrics(
    model_version: str = "latest",
    window_days: int = 30,
) -> dict:
    """
    최근 `window_days` 거래일의 일별 점수 분포 + 티어 분포.

    응답 형식::

        {
          "model_version": "v8",
          "window_days": 30,
          "metrics": [
            {"date": "2026-04-30",
             "n": 200, "mean": 50.1, "median": 49.8, "stddev": 28.7,
             "p10": 12.3, "p25": 26.0, "p50": 49.8, "p75": 74.5, "p90": 88.1,
             "tier_a": 22, "tier_b": 41, "tier_c": 79, "tier_d": 58},
            ...
          ],
          "summary": {
            "mean_of_means": 50.0,
            "stddev_of_means": 1.2,
            "drift_alert": false        # 평균이 ±2σ 벗어났는지
          }
        }
    """
    ver = _resolve_version(model_version)

    def fetch():
        con = _con()
        # 최신 N개 distinct 날짜
        date_rows = con.execute(
            """
            SELECT DISTINCT CAST(date AS VARCHAR)
            FROM scores
            WHERE model_version = ?
            ORDER BY 1 DESC
            LIMIT ?
            """,
            [ver, int(window_days)],
        ).fetchall()
        if not date_rows:
            return {
                "model_version": ver,
                "window_days": window_days,
                "metrics": [],
                "summary": {
                    "mean_of_means": None,
                    "stddev_of_means": None,
                    "drift_alert": False,
                },
            }
        dates = [r[0] for r in date_rows]
        dates.reverse()  # 오름차순으로 반환

        df = con.execute(
            """
            SELECT
                CAST(date AS VARCHAR)              AS date,
                COUNT(*)                           AS n,
                AVG(CAST(score AS DOUBLE))         AS mean,
                MEDIAN(CAST(score AS DOUBLE))      AS median,
                STDDEV_POP(CAST(score AS DOUBLE))  AS stddev,
                QUANTILE_CONT(CAST(score AS DOUBLE), 0.10) AS p10,
                QUANTILE_CONT(CAST(score AS DOUBLE), 0.25) AS p25,
                QUANTILE_CONT(CAST(score AS DOUBLE), 0.50) AS p50,
                QUANTILE_CONT(CAST(score AS DOUBLE), 0.75) AS p75,
                QUANTILE_CONT(CAST(score AS DOUBLE), 0.90) AS p90,
                SUM(CASE WHEN tier='A' THEN 1 ELSE 0 END) AS tier_a,
                SUM(CASE WHEN tier='B' THEN 1 ELSE 0 END) AS tier_b,
                SUM(CASE WHEN tier='C' THEN 1 ELSE 0 END) AS tier_c,
                SUM(CASE WHEN tier='D' THEN 1 ELSE 0 END) AS tier_d,
                -- prob_ensemble 분포 (모델 신호 강도 모니터링)
                AVG(CAST(prob_ensemble AS DOUBLE))         AS prob_mean,
                STDDEV_POP(CAST(prob_ensemble AS DOUBLE))  AS prob_std,
                MIN(CAST(prob_ensemble AS DOUBLE))         AS prob_min,
                MAX(CAST(prob_ensemble AS DOUBLE))         AS prob_max,
                -- prob 클러스터 비율: 0.28~0.32 범위에 몰린 종목 비율 (%)
                ROUND(
                    SUM(CASE WHEN prob_ensemble BETWEEN 0.28 AND 0.32 THEN 1 ELSE 0 END)
                    * 100.0 / COUNT(*), 1
                ) AS prob_cluster_pct
            FROM scores
            WHERE model_version = ?
              AND CAST(date AS VARCHAR) IN ({plc})
            GROUP BY date
            ORDER BY date ASC
            """.format(plc=",".join("?" * len(dates))),
            [ver, *dates],
        ).fetchdf()

        _f = lambda v: round(float(v), 4) if pd.notna(v) else None
        _i = lambda v: int(v) if pd.notna(v) else 0

        metrics = []
        for _, row in df.iterrows():
            metrics.append({
                "date":            row["date"],
                "n":               _i(row["n"]),
                "mean":            _f(row["mean"]),
                "median":          _f(row["median"]),
                "stddev":          _f(row["stddev"]),
                "p10":             _f(row["p10"]),
                "p25":             _f(row["p25"]),
                "p50":             _f(row["p50"]),
                "p75":             _f(row["p75"]),
                "p90":             _f(row["p90"]),
                "tier_a":          _i(row["tier_a"]),
                "tier_b":          _i(row["tier_b"]),
                "tier_c":          _i(row["tier_c"]),
                "tier_d":          _i(row["tier_d"]),
                # prob 신호 강도 지표
                "prob_mean":       _f(row["prob_mean"]),
                "prob_std":        _f(row["prob_std"]),
                "prob_min":        _f(row["prob_min"]),
                "prob_max":        _f(row["prob_max"]),
                "prob_cluster_pct": _f(row["prob_cluster_pct"]),
            })

        # 드리프트 알림: 가장 최근 mean 이 전체 mean ± 2σ 벗어나면 true
        means_series = df["mean"].dropna()
        prob_std_series = df["prob_std"].dropna()
        if len(means_series) >= 5:
            mean_of_means = float(means_series.mean())
            stddev_of_means = float(means_series.std(ddof=0)) or 1e-9
            latest_mean = float(means_series.iloc[-1])
            drift_alert = abs(latest_mean - mean_of_means) > (2.0 * stddev_of_means)
            # prob_std 기준 신호 품질 (< 0.03이면 클러스터링 경고)
            avg_prob_std = float(prob_std_series.mean()) if len(prob_std_series) else None
            prob_signal_ok = avg_prob_std > 0.03 if avg_prob_std is not None else None
            summary = {
                "mean_of_means":  round(mean_of_means, 2),
                "stddev_of_means": round(stddev_of_means, 2),
                "latest_mean":    round(latest_mean, 2),
                "drift_alert":    bool(drift_alert),
                # 신호 품질 지표 (prob_std < 0.03 → 모델 클러스터링 경고)
                "avg_prob_std":   round(avg_prob_std, 4) if avg_prob_std is not None else None,
                "prob_signal_ok": prob_signal_ok,
            }
        else:
            summary = {
                "mean_of_means":  None,
                "stddev_of_means": None,
                "latest_mean":    None,
                "drift_alert":    False,
                "avg_prob_std":   None,
                "prob_signal_ok": None,
            }

        return {
            "model_version": ver,
            "window_days":   window_days,
            "metrics":       metrics,
            "summary":       summary,
        }

    return _cached(
        "model_metrics", fetch, ttl=300,
        model_version=ver, window_days=window_days,
    )
