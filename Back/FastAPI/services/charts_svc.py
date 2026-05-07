"""
services/charts_svc.py
======================
Tier 1B 4.5 — `data.py` 분할 결과물.

차트·가격·급상승 도메인.
함수: get_chart, get_stock_price, get_rising_stocks
"""

from __future__ import annotations

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
)


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
