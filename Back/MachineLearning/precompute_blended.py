# -*- coding: utf-8 -*-
"""
precompute_blended.py — T1.1 Production swap: regime_dep → winner 4주 blended rollout 로더.
(FINAL_REPORT §10.12.8, v1.7)

blended_rank = (1-w)·regime_dep_rank + w·winner_rank,  w: 0→0.3→0.5→0.7→1.0 (4주).
tier = *percentile* 기반(regime_dep 비율 정합 A15.6/B36.8/C30.0/D17.6 — 모델 교체 자동 적응).
winner = v11_flow_t6_20260401(최신 롤링 박제, 라이브 forward 서빙용).

안전 설계:
  --backup     : 현 live scores → parquet 백업(읽기전용 + 로컬파일). 라이브 서빙 불변.
  --unit-test  : w-grid 정합 검증(w0≈regime_dep, w1≈winner, 단조, tier-A≈15.6%). 계산만.
  --stage W    : blended(W) → 스테이징 parquet (라이브 DB 미적재).
  --apply  W   : ★라이브 scores 테이블 적재(outward-facing) — 명시 confirm 후에만.

Week 0 = --backup --unit-test (라이브 변경 0). Week 1~4 = --apply 0.3/0.5/0.7/1.0 (각 주 confirm).
"""
from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "report" / "backtest" / "experiments"))
import quant_common as Q

DB = Q.DB
WINNER_STAMP = "v11_flow_t6_20260401"
BACKUP_DIR = Q.OUT
TIER_CUM = {"A": 0.156, "B": 0.524, "C": 0.824}     # 누적 cutoff (percentile)
WGRID = [0.0, 0.3, 0.5, 0.7, 1.0]
MONITOR_DIR = HERE / "report" / "backtest" / "_results" / "presentation"
TIER_GAP_THR = 0.10                                 # ROLLBACK tier_gap (§10.12.8) — 즉시 체크 가능
IC_WARN, IC_SEVERE = 0.04, 0.02                     # ROLLBACK ic_warn/ic_severe (성숙 후 체크)


def log(m): print(f"[{datetime.now():%H:%M:%S}] {m}", flush=True)


def pct_tier(rankpct: np.ndarray) -> np.ndarray:
    return np.where(rankpct >= 1 - TIER_CUM["A"], "A",
           np.where(rankpct >= 1 - TIER_CUM["B"], "B",
           np.where(rankpct >= 1 - TIER_CUM["C"], "C", "D")))


def backup_scores():
    con = duckdb.connect(str(DB), read_only=True)
    df = con.execute("SELECT * FROM scores").fetchdf()
    con.close()
    p = BACKUP_DIR / f"scores_backup_pre_v1.7_swap_{datetime.now():%Y%m%d}.parquet"
    df.to_parquet(p, index=False)
    log(f"[backup] live scores {df.shape} → {p.name} (라이브 서빙 불변)")
    return p


def compute_blended(w: float, dates=None) -> pd.DataFrame:
    """blended(w) score+tier. regime_dep_rank(DB) + winner_rank(stamp). dates=None → 최신일."""
    con = duckdb.connect(str(DB), read_only=True)
    q = "SELECT date, ticker, score FROM scores WHERE model_version='regime_dep'"
    if dates is None:
        q += " AND date=(SELECT max(date) FROM scores WHERE model_version='regime_dep')"
    rd = con.execute(q).fetchdf()
    con.close()
    rd["date"] = pd.to_datetime(rd["date"]); rd["ticker"] = rd["ticker"].astype(str).str.zfill(6)
    rd["rd_rank"] = rd.groupby("date")["score"].rank(pct=True)

    panel = Q.universe(Q.load_panel()[0], need_fwd=False)   # 서빙: 최신일 fwd 미존재 허용
    ev = panel[panel["date"].isin(rd["date"].unique())].copy()
    ev["w_score"] = Q.predict_stamp(ev, WINNER_STAMP)
    ev["w_rank"] = pd.Series(ev["w_score"], index=ev.index).groupby(ev["date"]).rank(pct=True)
    m = rd.merge(ev[["date", "ticker", "w_rank"]], on=["date", "ticker"], how="inner")
    m["blended_rank"] = (1 - w) * m["rd_rank"] + w * m["w_rank"]
    m["score"] = m.groupby("date")["blended_rank"].rank(pct=True) * 100
    m["tier"] = pct_tier((m["score"] / 100).to_numpy())
    m["model_version"] = f"blended_w{w:.1f}"
    return m


def unit_test():
    log("[unit-test] w-grid 정합 검증 (최신일) …")
    base = compute_blended(0.0)         # w=0
    win = compute_blended(1.0)          # w=1
    b_s = base.set_index("ticker")["blended_rank"]      # ticker 정렬(최신 단일일)
    w_s = win.set_index("ticker")["blended_rank"]
    rows, ok = [], True
    for w in WGRID:
        m = compute_blended(w) if w not in (0.0, 1.0) else (base if w == 0 else win)
        m_s = m.set_index("ticker")["blended_rank"]
        corr_rd = m_s.corr(b_s, method="spearman")
        corr_w = m_s.corr(w_s, method="spearman")
        tierA = float((m["tier"] == "A").mean())
        rows.append({"w": w, "corr_regime_dep": round(float(corr_rd), 3),
                     "corr_winner": round(float(corr_w), 3), "tierA": round(tierA, 3)})
    df = pd.DataFrame(rows)
    # 정합 조건: w=0 corr_rd≈1, w=1 corr_w≈1, corr_w 단조↑, tierA 전부 0.13~0.18
    c1 = df[df.w == 0]["corr_regime_dep"].iloc[0] > 0.99
    c2 = df[df.w == 1]["corr_winner"].iloc[0] > 0.99
    c3 = df["corr_winner"].is_monotonic_increasing
    c4 = df["tierA"].between(0.13, 0.18).all()
    ok = bool(c1 and c2 and c3 and c4)
    print(df.to_string(index=False))
    print(f"  정합: w0≈rd {c1} | w1≈winner {c2} | corr_winner 단조↑ {c3} | tierA∈[.13,.18] {c4} → {'PASS' if ok else 'FAIL'}")
    return ok


def stage(w: float):
    m = compute_blended(w)
    p = BACKUP_DIR / f"staging_blended_w{w:.1f}.parquet"
    m.to_parquet(p, index=False)
    log(f"[stage] blended_w{w:.1f} {m.shape} → {p.name} (라이브 DB 미적재)")
    log(f"  tier dist: {m['tier'].value_counts().to_dict()}")


def apply_live(w: float, full_history: bool = False):
    """★라이브 scores 적재 (idempotent·atomic). meta 는 regime_dep row 에서 JOIN.
    fresh inserted_at → resolve_version('latest') inserted_at fallback 로 자동 서빙.
    full_history=False → 최신일 1건만(서빙 스냅샷). True → regime_dep 전 기간 백필(추이차트용).
      · 최신일 score 는 두 경로 동일 공식 → idempotent (값 불변).
    rollback: DELETE FROM scores WHERE model_version='blended_w{w}' (→ regime_dep 최신 복귀) 또는 백업 복원."""
    mv = f"blended_w{w:.1f}"
    # dates 인자가 None 이 아니면 compute_blended 가 regime_dep 전 날짜 + winner 예측으로 전체 이력 산출
    bl = compute_blended(w, dates=("all" if full_history else None))
    con = duckdb.connect(str(DB), read_only=False)
    # regime_dep meta JOIN (name·sector·mid_sector·close·top_factors)
    meta = con.execute("SELECT date, ticker, name, sector, mid_sector, close, top_factors "
                       "FROM scores WHERE model_version='regime_dep'").fetchdf()
    meta["date"] = pd.to_datetime(meta["date"]); meta["ticker"] = meta["ticker"].astype(str).str.zfill(6)
    out = bl.merge(meta, on=["date", "ticker"], how="inner")
    out["prob_lgbm"] = out["prob_xgb"] = out["prob_cat"] = out["prob_ensemble"] = out["blended_rank"]
    out["rank_in_date"] = out.groupby("date")["score"].rank(ascending=False, method="first").astype(int)
    out["total_in_date"] = out.groupby("date")["score"].transform("size").astype(int)
    out["model_version"] = mv
    out["inserted_at"] = datetime.utcnow().isoformat() + "Z"
    cols = ["date", "ticker", "name", "sector", "mid_sector", "close", "prob_lgbm", "prob_xgb",
            "prob_cat", "prob_ensemble", "score", "rank_in_date", "total_in_date", "tier",
            "model_version", "inserted_at", "top_factors"]
    out_df = out[cols]
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute("DELETE FROM scores WHERE model_version = ?", [mv])
        con.register("blended_in", out_df)
        con.execute(f"INSERT INTO scores ({','.join(cols)}) SELECT {','.join(cols)} FROM blended_in")
        con.unregister("blended_in")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK"); con.close(); raise
    n = con.execute("SELECT count(*) FROM scores WHERE model_version=?", [mv]).fetchone()[0]
    td = con.execute("SELECT tier, count(*) FROM scores WHERE model_version=? GROUP BY 1 ORDER BY 1", [mv]).fetchall()
    sr = con.execute("SELECT min(score), max(score) FROM scores WHERE model_version=?", [mv]).fetchone()
    con.close()
    log(f"[apply] ★ live 적재 {mv}: {n} rows | tier {dict(td)} | score [{sr[0]:.1f},{sr[1]:.1f}] | inserted_at=now")
    log(f"  rollback: DELETE FROM scores WHERE model_version='{mv}' (또는 백업 복원)")
    return {"model_version": mv, "rows": n, "tier": dict(td), "score_range": [round(sr[0], 1), round(sr[1], 1)]}


def _topk(df, k=20):
    return set(df.sort_values("score", ascending=False).head(k)["ticker"])


def monitor(live_mv: str | None = None, day: str = ""):
    """라이브 blended 서빙 헬스 체크 (rollout 모니터링, §10.12.9 후속). Day-0/3/7 비교용 dated JSON 적재.
    - tier_gap(즉시): 라이브 tier-A 비율 vs 목표 0.156, |gap|>0.10 → tier 재캘리브 (ROLLBACK).
    - Jaccard TOP-20(즉시): 라이브 vs regime_dep 안정성 baseline.
    - 실현 IC(성숙 후): 서빙일 fwd_return_20d 가 존재하면 blended score 와 spearman; 미성숙이면 PENDING.
    rollback 트리거는 *판정만* 하고 자동 실행 안 함(outward-facing) — 운영자 확인."""
    live_mv = live_mv or os.getenv("DEFAULT_MODEL_VERSION") or "blended_w0.3"
    con = duckdb.connect(str(DB), read_only=True)
    ld = con.execute("SELECT max(date) FROM scores WHERE model_version=?", [live_mv]).fetchone()[0]
    if ld is None:
        con.close(); raise RuntimeError(f"라이브 모델 '{live_mv}' 적재 없음")
    live = con.execute("SELECT ticker, score, tier FROM scores WHERE model_version=? AND date=?",
                       [live_mv, ld]).fetchdf()
    rd = con.execute("SELECT ticker, score, tier FROM scores WHERE model_version='regime_dep' "
                     "AND date=(SELECT max(date) FROM scores WHERE model_version='regime_dep')").fetchdf()
    con.close()
    live["ticker"] = live["ticker"].astype(str).str.zfill(6)
    rd["ticker"] = rd["ticker"].astype(str).str.zfill(6)

    # 1) tier-A gap (즉시)
    tierA = float((live["tier"] == "A").mean())
    tier_gap = abs(tierA - TIER_CUM["A"])
    tier_verdict = "PASS" if tier_gap <= TIER_GAP_THR else "FAIL→tier 재캘리브"

    # 2) Jaccard TOP-20 (즉시, baseline)
    a, b = _topk(live, 20), _topk(rd, 20)
    jac = round(len(a & b) / len(a | b), 3) if (a | b) else 0.0

    # 3) 실현 IC (성숙 시): 서빙일 fwd_return_20d vs blended score
    ic, ic_verdict, n_ic = None, "PENDING(fwd 미성숙)", 0
    try:
        panel = Q.universe(Q.load_panel()[0], need_fwd=False)
        srv = panel[panel["date"] == pd.Timestamp(ld)][["ticker", "fwd_return_20d"]].dropna()
        srv["ticker"] = srv["ticker"].astype(str).str.zfill(6)
        mg = live.merge(srv, on="ticker", how="inner")
        n_ic = len(mg)
        if n_ic >= 20:
            ic = round(float(mg["score"].rank().corr(mg["fwd_return_20d"].rank())), 4)
            ic_verdict = ("PASS" if ic >= IC_WARN else
                          "WARN→w증가 보류" if ic >= IC_SEVERE else "SEVERE→직전 w 롤백")
    except Exception as e:
        ic_verdict = f"PENDING(계산오류: {type(e).__name__})"

    rec = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "day": day, "live_model": live_mv, "serving_date": str(ld),
        "n_live": int(len(live)),
        "tier_dist": live["tier"].value_counts().sort_index().to_dict(),
        "tierA_ratio": round(tierA, 4), "tierA_target": TIER_CUM["A"],
        "tier_gap": round(tier_gap, 4), "tier_verdict": tier_verdict,
        "jaccard_top20_vs_regime_dep": jac,
        "realized_ic": ic, "ic_n": n_ic, "ic_verdict": ic_verdict,
    }
    MONITOR_DIR.mkdir(parents=True, exist_ok=True)
    tag = day or datetime.now().strftime("%Y%m%d")
    p = MONITOR_DIR / f"blended_monitor_{tag}.json"
    json.dump(rec, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    log(f"[monitor] {live_mv} @ {ld} | tier-A {tierA:.3f} (gap {tier_gap:.3f} {tier_verdict}) | "
        f"Jaccard20 {jac} | IC {ic if ic is not None else '—'} ({ic_verdict}) → {p.name}")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backup", action="store_true")
    ap.add_argument("--unit-test", action="store_true")
    ap.add_argument("--stage", type=float, default=None)
    ap.add_argument("--apply", type=float, default=None)
    ap.add_argument("--apply-history", type=float, default=None,
                    help="★blended_w{W} 를 regime_dep 전 기간(322일) 백필 — 추이차트 회귀 복구. 최신일 값 불변(idempotent).")
    ap.add_argument("--monitor", action="store_true", help="라이브 blended 헬스 체크 (tier_gap·Jaccard·IC)")
    ap.add_argument("--day", default="", help="모니터링 라벨 (예: D0/D3/D7) — dated JSON 파일명에 사용")
    a = ap.parse_args()
    if a.backup: backup_scores()
    if a.unit_test: unit_test()
    if a.stage is not None: stage(a.stage)
    if a.apply is not None: apply_live(a.apply)
    if a.apply_history is not None: apply_live(a.apply_history, full_history=True)
    if a.monitor: monitor(day=a.day)
    if not any([a.backup, a.unit_test, a.stage is not None, a.apply is not None,
                a.apply_history is not None, a.monitor]):
        ap.print_help()


if __name__ == "__main__":
    main()
