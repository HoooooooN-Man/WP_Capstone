"""
routers/cohort_backtest.py
==========================
Regime-dep 5코호트 × 16개월 백테 결과 API (단일 variant: K10·H20).

ensemble_cohort_backtest.py 산출 csv 를 읽어 FE 코호트 포트폴리오 페이지가
"백테 성과" 섹션에서 표시할 수 있게 JSON 으로 노출.

엔드포인트:
  GET /api/v1/cohort-backtest/regime-dep
       5-cohort × 16개월 월별 수익률 + cohort summary + KOSPI 비교.
       variant 는 K10·H20 (운영 표준, 매월 rebal · 20일 보유) 만 사용.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/cohort-backtest", tags=["cohort-backtest"])

ML_ROOT = Path(__file__).resolve().parents[2] / "MachineLearning"
CSV_PATH = (
    ML_ROOT / "report" / "backtest" / "_results"
    / "cohort" / "results_Regime_dep" / "cohort_monthly_returns.csv"
)


@router.get("/regime-dep", summary="Regime-dep 5코호트 16개월 백테 (K10·H20)")
def get_regime_dep_backtest():
    """K10·H20 (TOP 10 · 매월 rebal · 1개월 보유) 백테 결과만 노출.

    응답:
      {
        variant, description,
        monthly: [{rebalance_date, cohort, port_return_net_pct, kospi_return_pct}, ...],
        summary: {cohort_name: {avg_return_pct, cum_return_pct, win_rate_pct,
                                  best_month, worst_month}},
        kospi_summary: {...},
        is_advice: false,
      }
    """
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="백테 결과 csv 미적재")

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df["port_return_net"] = df["port_return_net"].astype(float)
    df["kospi_return"] = df["kospi_return"].astype(float)
    df["port_return_net_pct"] = df["port_return_net"] * 100.0
    df["kospi_return_pct"] = df["kospi_return"] * 100.0

    # cohort 별 summary
    summary: dict[str, dict] = {}
    for cohort, g in df.groupby("cohort"):
        nets = g["port_return_net"].dropna()
        if len(nets) == 0:
            continue
        cum = float((nets + 1.0).prod() - 1.0)
        avg = float(nets.mean())
        win_rate = float((nets > 0).mean())
        best_idx = nets.idxmax()
        worst_idx = nets.idxmin()
        summary[str(cohort)] = {
            "n_months": int(len(nets)),
            "avg_return_pct": round(avg * 100, 2),
            "cum_return_pct": round(cum * 100, 2),
            "win_rate_pct": round(win_rate * 100, 1),
            "best_month": {
                "date": str(g.loc[best_idx, "rebalance_date"]),
                "return_pct": round(float(g.loc[best_idx, "port_return_net"]) * 100, 2),
            },
            "worst_month": {
                "date": str(g.loc[worst_idx, "rebalance_date"]),
                "return_pct": round(float(g.loc[worst_idx, "port_return_net"]) * 100, 2),
            },
        }

    k_unique = df.drop_duplicates("rebalance_date")["kospi_return"].dropna()
    kospi_summary = None
    if len(k_unique):
        kospi_summary = {
            "n_months": int(len(k_unique)),
            "avg_return_pct": round(float(k_unique.mean()) * 100, 2),
            "cum_return_pct": round(float((k_unique + 1).prod() - 1) * 100, 2),
            "win_rate_pct": round(float((k_unique > 0).mean()) * 100, 1),
        }

    monthly = df[["rebalance_date", "cohort", "port_return_net_pct", "kospi_return_pct"]].copy()
    monthly = monthly.round(2)
    return {
        "variant": "K10_H20",
        "description": "TOP 10 · 매월 rebal · 20거래일 보유 (운영 표준)",
        "monthly": monthly.to_dict(orient="records"),
        "summary": summary,
        "kospi_summary": kospi_summary,
        "is_advice": False,
    }
