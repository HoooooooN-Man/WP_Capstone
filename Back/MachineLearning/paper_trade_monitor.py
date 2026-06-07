# -*- coding: utf-8 -*-
"""
paper_trade_monitor.py — Phase 1 Paper Trading (5-Cohort, NO 1억 NAV)
======================================================================
사용자 결정 (2026-05-19):
  "1억 백테로 안하고 5코호트 추천만 진행할거야."

방식:
  - 매 월 첫 영업일 (또는 --date 지정): regime 분류 + 5 cohort × TOP K=10 picks 스냅샷
  - 매 일 (또는 --measure): 20 거래일 경과한 스냅샷에 실현 fwd_return_20d 결합
  - 누적 metrics: 월별 IC, realized port return, 90d CAGR proxy

합격 기준 (Phase 1 paper trading checklist):
  - 실현 IC ≥ 0.05 (월별 평균, spearman)
  - Realized 90d CAGR ≥ -5% (boost-up: worst-fold 백테 +9.84% 보수 보정)
  - 코드 오류 0건
  - Regime 분류 정확 (deploy_regime_dep.py 결과와 일치)

NO-GO 시:
  - Regime classifier 임계값 재검토
  - 매핑 (강세→E2c, 약세→E2a) 재검증

CLI:
  python paper_trade_monitor.py --snapshot [--date YYYY-MM-DD]
  python paper_trade_monitor.py --measure
  python paper_trade_monitor.py --report

산출:
  report/backtest/_results/paper_trade/snapshots.parquet
  report/backtest/_results/paper_trade/measurements.parquet
  report/backtest/_results/paper_trade/report.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data"))
ML_ROOT = Path(__file__).resolve().parent
BACKTEST_ROOT = ML_ROOT / "report" / "backtest"
FASTAPI_SVC = ML_ROOT.parent / "FastAPI" / "services"

sys.path.insert(0, str(ML_ROOT))
sys.path.insert(0, str(FASTAPI_SVC))
sys.path.insert(0, str(BACKTEST_ROOT))

from ensemble_cohort_backtest import (  # noqa: E402
    predict_3model_scores, ensemble_score_filtered, REGIME_MAPPING,
)
from cohort_backtest_v11_flow_t6 import (  # noqa: E402
    attach_volatility_60d, attach_dividend_yield, attach_names,
    load_fwd_returns, COHORTS,
)
from regime_filter import (  # noqa: E402
    load_kospi_series, classify_regime, REGIME_THRESHOLDS,
)
from personalization import rerank_for_cohort  # noqa: E402

DB_PATH = CAPSTONE_ROOT / "project_data" / "db" / "market_data.duckdb"
OUT_ROOT = BACKTEST_ROOT / "_results" / "paper_trade"
OUT_ROOT.mkdir(parents=True, exist_ok=True)

SNAPSHOTS_PARQUET = OUT_ROOT / "snapshots.parquet"
MEASUREMENTS_PARQUET = OUT_ROOT / "measurements.parquet"
REPORT_MD = OUT_ROOT / "report.md"

TOP_K = 10
HOLD_DAYS = 20  # 거래일
BT_START = "2025-01-01"

PASS_IC_MIN = 0.05
PASS_CAGR_MIN = -0.05  # 90d realized CAGR ≥ -5%

# T1.1 blended rollout 자동 rollback 임계 (§10.12.8, Week1~4 라이브 적용 시)
ROLLBACK = {
    "ic_warn":   {"thr": 0.04, "days": 5, "action": "w 증가 보류·1주 모니터링"},   # 위험
    "ic_severe": {"thr": 0.02, "days": 3, "action": "직전 단계 w 롤백"},           # 심각
    "mdd_severe": {"thr": -0.10, "action": "즉시 롤백·원인 분석"},                 # 드라이런 예상 초과
    "tier_gap":  {"thr": 0.10, "action": "tier 재캘리브 재실행"},                  # 운영
    "complaints": {"action": "사용자 공지 + 대응"},                               # 운영(채널 있을 시)
}


def log(m):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


# ─────────────────────────────────────────────────────────────────
# Snapshot
# ─────────────────────────────────────────────────────────────────
def build_snapshot(decision_date: pd.Timestamp) -> pd.DataFrame:
    """decision_date 시점에 regime + 5 cohort × TOP K=10 picks 산출."""
    log(f"[snapshot] decision_date = {decision_date.date()}")

    kospi_df = load_kospi_series()
    regime_info = classify_regime(kospi_df, decision_date, REGIME_THRESHOLDS)
    regime = regime_info["regime"]
    log(f"  regime = {regime}  (above_ma200={regime_info.get('above_ma200')}, "
        f"hv60={regime_info.get('hv_60d', 0):.3f}, mom1m={regime_info.get('mom_1m', 0):.3f})")

    log("  predicting 3-model scores ...")
    scores_dict = predict_3model_scores()

    # decision_date 가 cache 에 없으면 → 가장 가까운 직전 영업일로 폴백
    all_dates = sorted({d for df in scores_dict.values() for d in df["date"].unique()})
    avail_dates = [d for d in all_dates if d <= decision_date]
    if not avail_dates:
        raise RuntimeError(f"no score available ≤ {decision_date}")
    score_date = pd.Timestamp(avail_dates[-1])
    if score_date != decision_date:
        log(f"  score_date fallback → {score_date.date()} "
            f"(latest cache ≤ decision_date)")

    # 모델 fwd_return — outlier filter 용
    con = duckdb.connect(str(DB_PATH), read_only=True)
    fwd = load_fwd_returns(con, BT_START)

    models = REGIME_MAPPING[regime]
    log(f"  regime '{regime}' → ensemble = {models}")
    ensemble = ensemble_score_filtered(scores_dict, fwd, models)
    ensemble = ensemble[ensemble["date"] == score_date].copy()
    if ensemble.empty:
        con.close()
        raise RuntimeError(f"ensemble score empty at {score_date}")

    # meta 결합 (cohort filter 용)
    meta = scores_dict["winner"][["date", "ticker", "sector", "per", "pbr", "ret_lag_60d"]]
    scored = ensemble.merge(meta, on=["date", "ticker"], how="left")
    scored = attach_volatility_60d(scored, con, BT_START)
    scored = attach_dividend_yield(scored, con)
    scored = attach_names(scored, con)
    con.close()

    # attach_dividend_yield 가 percent→fraction 변환하지만, rerank_for_cohort 는
    # PERCENT 단위 (>2.0) 를 기대 (B3 fix 기준). production 동작 일치 위해 복원.
    if "dividend_yield" in scored.columns:
        med = scored["dividend_yield"].replace(0, np.nan).median()
        if med is not None and med < 1.0:
            scored["dividend_yield"] = scored["dividend_yield"] * 100.0

    cohort_cols = ["ticker", "name", "score", "per", "pbr", "dividend_yield",
                   "volatility_60d", "ret_lag_60d"]
    day = scored[scored["date"] == score_date].sort_values("score", ascending=False)
    rows = day[cohort_cols].to_dict("records")

    snap_rows = []
    for cohort in COHORTS:
        picks = rerank_for_cohort(rows, cohort, top_k=TOP_K)
        for rk, p in enumerate(picks, 1):
            snap_rows.append({
                "snapshot_date": decision_date.date().isoformat(),
                "score_date": score_date.date().isoformat(),
                "regime": regime,
                "models": "+".join(models),
                "cohort": cohort,
                "rank": rk,
                "ticker": p["ticker"],
                "name": p.get("name"),
                "score": round(float(p["score"]), 3),
                "per": p.get("per"),
                "pbr": p.get("pbr"),
                "dividend_yield": p.get("dividend_yield"),
                "volatility_60d": p.get("volatility_60d"),
                "kospi_close": float(regime_info.get("kospi", np.nan)),
                "ma200": float(regime_info.get("ma200", np.nan)),
                "hv_60d": float(regime_info.get("hv_60d", np.nan)),
                "mom_1m": float(regime_info.get("mom_1m", np.nan)),
                "above_ma200": bool(regime_info.get("above_ma200", False)),
                "snapshot_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            })
    snap = pd.DataFrame(snap_rows)
    log(f"  picks: {len(snap)} rows × {snap['cohort'].nunique()} cohort")
    return snap


def backfill_from_backtest() -> pd.DataFrame:
    """ensemble_cohort_backtest.py 의 Regime-dep 결과 CSV 를 paper-trade 스냅샷 포맷으로 변환.

    목적: 과거 16 개월 (2025-01~2026-04) 의 snapshot+realized 를 한번에 적재하여
    Pass 기준 평가를 즉시 가능하게 함. 한 번만 실행 (이후 monthly snapshot 누적).
    """
    csv_path = BACKTEST_ROOT / "_results" / "cohort" / "results_Regime_dep" / "cohort_selected_stocks.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"backtest CSV 없음: {csv_path}")
    bt = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"ticker": str})
    bt["ticker"] = bt["ticker"].astype(str).str.zfill(6)
    log(f"[backfill] backtest CSV: {len(bt)} rows from {csv_path.name}")

    kospi_df = load_kospi_series()
    rows = []
    for rebal_date_str, g in bt.groupby("rebalance_date"):
        d = pd.Timestamp(rebal_date_str)
        ri = classify_regime(kospi_df, d, REGIME_THRESHOLDS)
        regime = ri["regime"]
        models = REGIME_MAPPING.get(regime, REGIME_MAPPING["unknown"])
        for _, r in g.iterrows():
            rows.append({
                "snapshot_date": d.date().isoformat(),
                "score_date": d.date().isoformat(),
                "regime": regime,
                "models": "+".join(models),
                "cohort": r["cohort"],
                "rank": int(r["rank"]),
                "ticker": r["ticker"],
                "name": r.get("name"),
                "score": round(float(r["score"]), 3),
                "per": float(r["per"]) if pd.notna(r.get("per")) else None,
                "pbr": float(r["pbr"]) if pd.notna(r.get("pbr")) else None,
                "dividend_yield": float(r["dividend_yield"]) if pd.notna(r.get("dividend_yield")) else None,
                "volatility_60d": float(r["volatility_60d"]) if pd.notna(r.get("volatility_60d")) else None,
                "kospi_close": float(ri.get("kospi", np.nan)),
                "ma200": float(ri.get("ma200", np.nan)),
                "hv_60d": float(ri.get("hv_60d", np.nan)),
                "mom_1m": float(ri.get("mom_1m", np.nan)),
                "above_ma200": bool(ri.get("above_ma200", False)),
                "snapshot_at": "backfill",
            })
    snap = pd.DataFrame(rows)
    log(f"[backfill] generated {len(snap)} rows × {snap['snapshot_date'].nunique()} dates "
        f"× {snap['cohort'].nunique()} cohort")
    return snap


def append_snapshot(snap: pd.DataFrame) -> None:
    if SNAPSHOTS_PARQUET.exists():
        prev = pd.read_parquet(SNAPSHOTS_PARQUET)
        # 같은 snapshot_date 가 있으면 교체 (재실행 안전)
        prev = prev[prev["snapshot_date"] != snap["snapshot_date"].iloc[0]]
        out = pd.concat([prev, snap], ignore_index=True)
    else:
        out = snap
    out.to_parquet(SNAPSHOTS_PARQUET, index=False)
    log(f"  → {SNAPSHOTS_PARQUET} ({len(out)} total rows)")


# ─────────────────────────────────────────────────────────────────
# Measurement (실현)
# ─────────────────────────────────────────────────────────────────
def measure_realized() -> pd.DataFrame:
    """20 거래일 경과한 snapshot 에 fwd_return_20d 결합 + IC/return 계산."""
    if not SNAPSHOTS_PARQUET.exists():
        log("[measure] no snapshots — skip")
        return pd.DataFrame()
    snap = pd.read_parquet(SNAPSHOTS_PARQUET)
    snap["score_date_ts"] = pd.to_datetime(snap["score_date"])

    con = duckdb.connect(str(DB_PATH), read_only=True)
    fwd = load_fwd_returns(con, BT_START)
    con.close()
    fwd_idx = fwd.set_index(["date", "ticker"])["fwd_return_20d"]

    rows = []
    for (sd, cohort), g in snap.groupby(["score_date_ts", "cohort"]):
        rets, scores = [], []
        for _, r in g.iterrows():
            v = fwd_idx.get((sd, r["ticker"]), np.nan)
            rets.append(v)
            scores.append(r["score"])
        rets_arr = np.array(rets, dtype=float)
        scores_arr = np.array(scores, dtype=float)
        valid = ~np.isnan(rets_arr)
        n_valid = int(valid.sum())
        if n_valid < 3:
            ic = np.nan
            port_ret = np.nan
        else:
            # spearman IC
            sr = pd.Series(scores_arr[valid]).rank()
            rr = pd.Series(rets_arr[valid]).rank()
            ic = float(sr.corr(rr))
            port_ret = float(rets_arr[valid].mean())
        rows.append({
            "snapshot_date": g["snapshot_date"].iloc[0],
            "score_date": g["score_date"].iloc[0],
            "regime": g["regime"].iloc[0],
            "cohort": cohort,
            "n_picks": int(len(g)),
            "n_realized": n_valid,
            "ic_spearman": None if np.isnan(ic) else round(ic, 4),
            "port_return_20d": None if np.isnan(port_ret) else round(port_ret, 6),
            "port_return_net": (None if np.isnan(port_ret)
                                else round(port_ret - 2 * 0.0015, 6)),
        })
    meas = pd.DataFrame(rows).sort_values(["snapshot_date", "cohort"]).reset_index(drop=True)
    meas.to_parquet(MEASUREMENTS_PARQUET, index=False)
    n_measured = int(meas["n_realized"].gt(0).sum())
    log(f"[measure] {len(meas)} (snapshot×cohort) rows — {n_measured} with realized data")
    log(f"  → {MEASUREMENTS_PARQUET}")
    return meas


# ─────────────────────────────────────────────────────────────────
# Report (pass/fail)
# ─────────────────────────────────────────────────────────────────
def build_report() -> str:
    if not MEASUREMENTS_PARQUET.exists():
        return "# Paper Trade Report\n\n(no measurements yet)\n"
    meas = pd.read_parquet(MEASUREMENTS_PARQUET)
    meas["score_date_ts"] = pd.to_datetime(meas["score_date"])
    snap = pd.read_parquet(SNAPSHOTS_PARQUET) if SNAPSHOTS_PARQUET.exists() else pd.DataFrame()

    # KOSPI 벤치마크 (alpha 계산용)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    kospi_df = con.execute("""
        SELECT date, kospi_close FROM market_indices WHERE kospi_close IS NOT NULL
    """).fetchdf()
    con.close()
    kospi_df["date"] = pd.to_datetime(kospi_df["date"])
    kospi_df["kospi_fwd_20d"] = kospi_df["kospi_close"].shift(-HOLD_DAYS) / kospi_df["kospi_close"] - 1

    # 합격 기준 평가
    completed = meas[meas["ic_spearman"].notna()].copy()
    if completed.empty:
        ic_pass, cagr_pass = None, None
        ic_mean, cagr, kospi_cagr, alpha = np.nan, np.nan, np.nan, np.nan
        hit_rate = np.nan
    else:
        ic_mean = float(completed["ic_spearman"].mean())
        ic_pass = ic_mean >= PASS_IC_MIN

        # 90d CAGR proxy = balanced 코호트 cumprod (1 + port_return_net)
        bal = completed[completed["cohort"] == "balanced"].sort_values("score_date_ts")
        if len(bal) >= 1:
            rets = bal["port_return_net"].fillna(0).to_numpy()
            cum = float(np.prod(1 + rets) - 1)
            n_months = len(bal)
            years = n_months / 12.0
            cagr = (1 + cum) ** (1 / max(years, 1 / 12)) - 1 if years > 0 else cum
            cagr_pass = cagr >= PASS_CAGR_MIN

            # KOSPI 동기간 CAGR
            bal["score_date_ts"] = pd.to_datetime(bal["score_date"])
            k_rets = []
            kospi_idx = kospi_df.set_index("date")["kospi_fwd_20d"]
            for d in bal["score_date_ts"]:
                k_rets.append(float(kospi_idx.get(d, np.nan)))
            k_arr = np.array([r for r in k_rets if not np.isnan(r)], dtype=float)
            if len(k_arr) > 0:
                k_cum = float(np.prod(1 + k_arr) - 1)
                k_years = len(k_arr) / 12.0
                kospi_cagr = (1 + k_cum) ** (1 / max(k_years, 1/12)) - 1
                alpha = cagr - kospi_cagr
            else:
                kospi_cagr, alpha = np.nan, np.nan
            hit_rate = float(np.mean(rets > 0))
        else:
            cagr = np.nan
            cagr_pass = None
            kospi_cagr, alpha, hit_rate = np.nan, np.nan, np.nan

    n_snapshots = int(snap["snapshot_date"].nunique()) if not snap.empty else 0
    n_completed = int(completed["snapshot_date"].nunique()) if not completed.empty else 0

    lines = []
    lines.append("# Paper Trade Monitor — Phase 1 Report")
    lines.append("")
    lines.append(f"_생성_: {datetime.utcnow().isoformat(timespec='seconds')}Z")
    lines.append("")
    lines.append("## 진행 현황")
    lines.append("")
    lines.append(f"- 누적 스냅샷: **{n_snapshots}** (월별 첫 영업일 기준)")
    lines.append(f"- 실현 완료: **{n_completed}** (20 거래일 경과)")
    lines.append("")

    lines.append("## 합격 기준 평가")
    lines.append("")
    lines.append("| 기준 | 목표 | 실측 | 판정 |")
    lines.append("|---|---|---|---|")

    def mark(p):
        if p is None: return "—"
        return "PASS" if p else "FAIL"

    lines.append(f"| 실현 IC (spearman, 월별 평균) | ≥ {PASS_IC_MIN:.2f} | "
                 f"{ic_mean if not np.isnan(ic_mean) else '—':.4f} | {mark(ic_pass)} |"
                 if not np.isnan(ic_mean) else
                 "| 실현 IC (spearman, 월별 평균) | ≥ 0.05 | — | — |")
    lines.append(f"| Realized 누적 CAGR (balanced, net) | ≥ {PASS_CAGR_MIN:+.0%} | "
                 f"{cagr*100:+.2f}% | {mark(cagr_pass)} |"
                 if not np.isnan(cagr) else
                 "| Realized 누적 CAGR (balanced, net) | ≥ -5% | — | — |")
    lines.append("| 코드 오류 | 0건 | — (별도 로그 확인) | — |")
    lines.append("| Regime 분류 정확 | deploy_regime_dep 일치 | (스냅샷 regime ↔ regime_state 비교) | — |")
    lines.append("")

    if not np.isnan(cagr):
        lines.append("### 보조 지표 (참고)")
        lines.append("")
        lines.append(f"- KOSPI 동기간 CAGR: **{kospi_cagr*100:+.2f}%**" if not np.isnan(kospi_cagr) else "- KOSPI CAGR: —")
        lines.append(f"- α (paper − KOSPI): **{alpha*100:+.2f}%**" if not np.isnan(alpha) else "")
        lines.append(f"- 월별 hit rate (balanced, net > 0): **{hit_rate*100:.1f}%**")
        lines.append(f"- N=10 picks/cohort 의 spearman IC 는 noise floor (~0.3) 가 커서 "
                     f"단일 지표로 PASS/FAIL 판정 부적절. CAGR + hit rate 가 더 신뢰.")
        lines.append("")

    def md_table(df: pd.DataFrame, index: bool = True) -> str:
        out = []
        if index:
            cols = [df.index.name or ""] + list(df.columns.astype(str))
            out.append("| " + " | ".join(cols) + " |")
            out.append("|" + "|".join(["---"] * len(cols)) + "|")
            for i, row in df.iterrows():
                cells = [str(i)] + [("" if pd.isna(v) else f"{v}") for v in row]
                out.append("| " + " | ".join(cells) + " |")
        else:
            cols = list(df.columns.astype(str))
            out.append("| " + " | ".join(cols) + " |")
            out.append("|" + "|".join(["---"] * len(cols)) + "|")
            for _, row in df.iterrows():
                cells = [("" if pd.isna(v) else f"{v}") for v in row]
                out.append("| " + " | ".join(cells) + " |")
        return "\n".join(out)

    if not completed.empty:
        lines.append("## 월별 IC × 코호트")
        lines.append("")
        pivot_ic = completed.pivot_table(
            index="score_date", columns="cohort", values="ic_spearman", aggfunc="mean"
        ).round(3)
        lines.append(md_table(pivot_ic))
        lines.append("")
        lines.append("## 월별 net return × 코호트")
        lines.append("")
        pivot_r = completed.pivot_table(
            index="score_date", columns="cohort", values="port_return_net", aggfunc="mean"
        ).round(4)
        lines.append(md_table(pivot_r))
        lines.append("")

    if not snap.empty:
        regime_log = (snap.groupby(["snapshot_date", "regime"]).size()
                      .reset_index(name="n_picks"))
        regime_summary = (regime_log.groupby("snapshot_date")
                          .agg({"regime": "first"}).reset_index())
        lines.append("## Regime 로그")
        lines.append("")
        lines.append(md_table(regime_summary, index=False))
        lines.append("")

    if not completed.empty:
        lines.append("## NO-GO 트리거 진단")
        lines.append("")
        if ic_pass is False:
            lines.append("- 실현 IC 미달 → Regime classifier 임계값/매핑 재검토 필요.")
        if cagr_pass is False:
            lines.append("- Realized CAGR 미달 → 매핑(강세→E2c, 약세→E2a) 재검증 필요.")
        if ic_pass and cagr_pass:
            lines.append("- 모든 기준 PASS — Phase 2 (점진 rollout) 진입 가능.")
        lines.append("")

    return "\n".join(lines) + "\n"


def write_report() -> None:
    md = build_report()
    REPORT_MD.write_text(md, encoding="utf-8")
    log(f"[report] → {REPORT_MD}")


PASS_MDD_MIN = -0.25       # rolling MDD 차단 룰 (§6.7.5)
ROLL_N = 3                 # 최근 N개월 rolling 창


def check_alerts() -> list[str]:
    """라이브 모니터링 알람 (D1, §10.11): 최근 ROLL_N개월 rolling IC<0.05 / CAGR<-5% / MDD<-25%.
    cron 에서 호출 → alerts.json 기록(이메일/Slack/webhook 연동 지점)."""
    import json as _json
    alerts = []
    if not MEASUREMENTS_PARQUET.exists():
        return ["(no measurements)"]
    m = pd.read_parquet(MEASUREMENTS_PARQUET)
    comp = m[m["ic_spearman"].notna()].copy()
    comp["score_date_ts"] = pd.to_datetime(comp["score_date"])
    if comp.empty:
        return ["(no completed measurements)"]
    recent_dates = sorted(comp["score_date_ts"].unique())[-ROLL_N:]
    rec = comp[comp["score_date_ts"].isin(recent_dates)]
    roll_ic = float(rec["ic_spearman"].mean())
    if roll_ic < PASS_IC_MIN:
        alerts.append(f"⚠️ rolling IC {roll_ic:+.3f} < {PASS_IC_MIN} (최근 {ROLL_N}개월) — 신호 약화")
    bal = comp[comp["cohort"] == "balanced"].sort_values("score_date_ts")
    if len(bal) >= ROLL_N:
        r = bal["port_return_net"].fillna(0).to_numpy()
        eq = np.cumprod(1 + r); mdd = float((eq / np.maximum.accumulate(eq) - 1).min())
        roll_cagr = float((1 + (np.prod(1 + r[-ROLL_N:]) - 1)) ** (12 / ROLL_N) - 1)
        if mdd < PASS_MDD_MIN:
            alerts.append(f"⚠️ MDD {mdd:+.1%} < {PASS_MDD_MIN:+.0%} — 자본 보전 차단룰")
        if roll_cagr < PASS_CAGR_MIN:
            alerts.append(f"⚠️ rolling CAGR {roll_cagr:+.1%} < {PASS_CAGR_MIN:+.0%}")
    if not alerts:
        alerts.append(f"✅ 정상 (rolling IC {roll_ic:+.3f} ≥ {PASS_IC_MIN})")
    _json.dump({"checked_at": datetime.utcnow().isoformat() + "Z", "roll_n_months": ROLL_N,
                "rolling_ic": round(roll_ic, 4), "alerts": alerts},
               open(OUT_ROOT / "alerts.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for a in alerts:
        log(f"[alert] {a}")
    return alerts


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", action="store_true",
                   help="현 시점 (또는 --date) 스냅샷 적재")
    p.add_argument("--measure", action="store_true",
                   help="20 거래일 경과 스냅샷에 실현 결합")
    p.add_argument("--report", action="store_true",
                   help="누적 metrics + pass/fail 리포트")
    p.add_argument("--backfill", action="store_true",
                   help="backtest CSV → paper-trade snapshot 변환 (1회성)")
    p.add_argument("--alerts", action="store_true",
                   help="rolling IC/CAGR/MDD 알람 체크 (D1 라이브 모니터링)")
    p.add_argument("--date", default=None,
                   help="snapshot decision_date (default = today)")
    args = p.parse_args()

    if not (args.snapshot or args.measure or args.report or args.backfill or args.alerts):
        p.print_help()
        return

    err_count = 0

    if args.backfill:
        try:
            snap = backfill_from_backtest()
            # 전체 교체 (idempotent)
            snap.to_parquet(SNAPSHOTS_PARQUET, index=False)
            log(f"  → {SNAPSHOTS_PARQUET}")
        except Exception:
            err_count += 1
            log("[ERROR] backfill failed")
            traceback.print_exc()

    if args.snapshot:
        try:
            d = pd.Timestamp(args.date) if args.date else pd.Timestamp.today().normalize()
            snap = build_snapshot(d)
            append_snapshot(snap)
        except Exception:
            err_count += 1
            log("[ERROR] snapshot failed")
            traceback.print_exc()

    if args.measure:
        try:
            measure_realized()
        except Exception:
            err_count += 1
            log("[ERROR] measure failed")
            traceback.print_exc()

    if args.report:
        try:
            write_report()
        except Exception:
            err_count += 1
            log("[ERROR] report failed")
            traceback.print_exc()

    if args.alerts:
        try:
            check_alerts()
        except Exception:
            err_count += 1
            log("[ERROR] alerts failed")
            traceback.print_exc()

    log(f"[done] errors = {err_count}")
    sys.exit(1 if err_count else 0)


if __name__ == "__main__":
    main()
