"""
services/backtest_svc.py
========================
Tier 1B 4.5 — `data.py` 분할 결과물.

백테스트 도메인.
함수: get_backtest_monthly_returns, get_backtest_summary, run_custom_backtest
"""

from __future__ import annotations

import pandas as pd

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
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
