"""
services/metrics_svc.py
=======================
Tier 1B 4.5 — `data.py` 분할 결과물.

모델 모니터링·드리프트 감지 도메인.
함수: get_model_metrics
"""

from __future__ import annotations

import pandas as pd

from ._core import (
    con as _con,
    cached as _cached,
    resolve_version as _resolve_version,
)


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

        # Tier 1B 4.1 — 캘리브레이션(holdout 박제 ECE) 합쳐서 노출.
        # 라이브 데이터에는 forward 라벨이 없으므로, 박제 결과를 *참조* 한다.
        from .holdout_archive import get_holdout_metrics_summary
        summary.update(get_holdout_metrics_summary())

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
