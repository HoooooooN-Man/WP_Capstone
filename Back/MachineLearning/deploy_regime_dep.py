# -*- coding: utf-8 -*-
"""
deploy_regime_dep.py — Regime-dep 운영 통합 cron
==================================================
3 phase 통합 orchestrator. Phase 1 (재학습) + Phase 2 (scores 적재) + Phase 3 (regime 갱신).

운영 의도: 비즈니스 메인 모델 = Regime-dep Ensemble
  - 1억 → 6년 5.128억 (KOSPI 대비 +43%)
  - Worst Calmar 1.57, Bootstrap CI 1.87 ★

cron 구성:
  # 분기 재학습 (3개월 첫 영업일 03:00 KST)
  py deploy_regime_dep.py --retrain
  # 일별 추론 + regime (매일 17:00 KST, 장 종료 후)
  py deploy_regime_dep.py --daily

CLI:
  --retrain     : 3 모델 분기 재학습 + 박제
  --daily       : 일별 추론 (3 모델) + regime 갱신
  --regime-only : regime 만 갱신
  --all         : 위 3 phase 모두 (분기 재학습 시점)
  --dry-run     : DB 변경 없이 시뮬

Atomic swap:
  - 재학습: tmp dir → final dir (성공 시만 swap)
  - scores: 별도 transaction (실패 시 rollback)
  - regime: INSERT (이전 row 보존)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data"))
ML_ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(ML_ROOT))
sys.path.insert(0, str(ML_ROOT / "report" / "backtest"))

from train_lambdarank_v11 import sanitize_feature_names, bin_relevance_per_group, N_RELEVANCE_BINS  # noqa: E402
from flow_features import add_flow_features, FLOW_COLUMNS              # noqa: E402
from exp_target_eng import make_target                                  # noqa: E402

FIXED8 = CAPSTONE_ROOT / "data_pipeline" / "train_features_v9_cache_ext_fixed8.parquet"
LEGACY_CACHE = CAPSTONE_ROOT / "data_pipeline" / "train_features_v9_cache_ext.parquet"
DUCKDB_PATH = Path(os.getenv("DUCKDB_PATH",
                              str(CAPSTONE_ROOT / "project_data" / "db" / "market_data.duckdb")))
MODELS_ROOT = CAPSTONE_ROOT / "project_data" / "models"

WINNER_OPTUNA_PARAMS_JSON = ML_ROOT / "report" / "backtest" / "_results" / "experiments" / "exp_optuna_t6_9fflow.json"
TRAIN_VALID_GAP_MONTHS = 6

# Regime thresholds (사전 결정, in-sample tuning X)
REGIME_THRESHOLDS = {
    "ma_window": 200,
    "hv_window": 60,
    "hv_bull_max": 0.25,
    "hv_bear_min": 0.30,
    "mom_window": 21,
    "mom_bull_min": 0.00,
    "mom_bear_max": -0.05,
}


def log(m):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


def load_winner_params() -> dict:
    if WINNER_OPTUNA_PARAMS_JSON.exists():
        j = json.loads(WINNER_OPTUNA_PARAMS_JSON.read_text(encoding="utf-8"))
        return j.get("best_params", j)
    # 폴백 — exp_optuna_t6_9fflow.json 백업
    for cand in [
        ML_ROOT / "report" / "backtest" / "exp_optuna_t6_9fflow.json",
        ML_ROOT / "report" / "backtest" / "exp_optuna_67fflow_fixed5.json",
    ]:
        if cand.exists():
            j = json.loads(cand.read_text(encoding="utf-8"))
            return j.get("best_params", j)
    log("[WARN] Optuna params 없음 — 디폴트 사용")
    return {}


# ─────────────────────────────────────────────────────────────────
# Phase 1 — 3 모델 재학습 + 박제 (분기/반기)
# ─────────────────────────────────────────────────────────────────
def determine_splits(as_of: pd.Timestamp) -> tuple[str, str, str]:
    valid_end = as_of
    valid_start = (valid_end - pd.DateOffset(months=TRAIN_VALID_GAP_MONTHS)).normalize()
    train_end = valid_start - pd.Timedelta(days=1)
    return (train_end.strftime("%Y-%m-%d"),
            valid_start.strftime("%Y-%m-%d"),
            valid_end.strftime("%Y-%m-%d"))


def train_single_seed(tr, va, feats, params, seed):
    tr_rel = bin_relevance_per_group(tr)
    va_rel = bin_relevance_per_group(va)
    tr_grp = tr.groupby("date", sort=True).size().to_numpy()
    va_grp = va.groupby("date", sort=True).size().to_numpy()
    dtrain = lgb.Dataset(tr[feats].astype(np.float32).fillna(0.0).to_numpy(),
                          label=tr_rel, group=tr_grp)
    dvalid = lgb.Dataset(va[feats].astype(np.float32).fillna(0.0).to_numpy(),
                          label=va_rel, group=va_grp, reference=dtrain)
    base = {"objective": "lambdarank", "metric": "ndcg", "ndcg_eval_at": [10],
            "label_gain": list(range(N_RELEVANCE_BINS)),
            "verbose": -1, "seed": seed}
    base.update(params)
    return lgb.train(base, dtrain, num_boost_round=500,
                     valid_sets=[dvalid], valid_names=["valid"],
                     callbacks=[lgb.early_stopping(30, verbose=False)])


def retrain_winner(as_of: pd.Timestamp, dry_run: bool = False) -> Path | None:
    """Winner: fixed8 + 9f_flow + T6 + 10-seed."""
    log("\n[Phase 1.1] Winner retrain (fixed8 + 9f_flow + T6 + 10-seed)")
    df = sanitize_feature_names(pd.read_parquet(FIXED8))
    df["date"] = pd.to_datetime(df["date"])
    df = add_flow_features(df, sort=True)

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    lbl = con.execute("""SELECT date, ticker, fwd_return_20d, sharpe_20d
                         FROM multi_labels WHERE fwd_return_20d IS NOT NULL""").fetchdf()
    con.close()
    lbl["date"] = pd.to_datetime(lbl["date"].astype(str), format="%Y%m%d")
    df = df.merge(lbl, on=["ticker","date"], how="inner").sort_values(["date","ticker"])

    tr_end, va_s, va_e = determine_splits(as_of)
    tr = df[df["date"] <= tr_end].copy()
    va = df[(df["date"] >= va_s) & (df["date"] <= va_e)].copy()
    tr["label"] = make_target(tr, "T6_resid_full")
    va["label"] = make_target(va, "T6_resid_full")
    tr = tr.dropna(subset=["label"])
    va = va.dropna(subset=["label"])
    log(f"  splits: train ≤ {tr_end}, valid {va_s}~{va_e}, samples tr={len(tr):,} va={len(va):,}")

    feat9 = json.loads((ML_ROOT / "v11_signal9_allowlist.json").read_text(encoding="utf-8"))
    feats = feat9 + FLOW_COLUMNS

    params = load_winner_params()
    seeds = list(range(42, 52))
    boosters = []
    for sd in seeds:
        t0 = datetime.now()
        booster = train_single_seed(tr, va, feats, params, sd)
        bi = int(booster.best_iteration)
        ndcg10 = float(booster.best_score.get("valid", {}).get("ndcg@10", 0))
        dt = (datetime.now() - t0).total_seconds()
        log(f"    seed {sd:>3}: iter {bi:>3} ndcg10 {ndcg10:.4f} ({dt:.0f}s)")
        boosters.append((sd, booster, bi, ndcg10))

    if dry_run:
        log("  [DRY-RUN] 박제 생략")
        return None

    suffix = as_of.strftime("%Y%m%d")
    final_dir = MODELS_ROOT / f"v11_flow_t6_{suffix}"
    tmp_dir = final_dir.with_suffix(".tmp")
    if tmp_dir.exists(): shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    for sd, booster, bi, ndcg10 in boosters:
        booster.save_model(str(tmp_dir / f"model_seed{sd}.txt"), num_iteration=bi)
    (tmp_dir / "feature_cols.json").write_text(json.dumps(feats, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    (tmp_dir / "meta.json").write_text(json.dumps({
        "model_version": "v11_flow_t6", "target": "T6_resid_full", "feature_set": "9f_flow",
        "n_features": len(feats), "n_train": int(len(tr)), "n_valid": int(len(va)),
        "train_end": tr_end, "valid_start": va_s, "valid_end": va_e,
        "as_of": as_of.strftime("%Y-%m-%d"),
        "seeds": seeds,
        "valid_ndcg10": [round(n, 4) for _, _, _, n in boosters],
        "valid_ndcg10_mean": round(float(np.mean([n for _, _, _, n in boosters])), 4),
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lgb_params": params,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    if final_dir.exists():
        backup = final_dir.with_name(final_dir.name + ".bak")
        if backup.exists(): shutil.rmtree(backup)
        final_dir.rename(backup)
        log(f"  prev → {backup}")
    tmp_dir.rename(final_dir)
    log(f"  archived → {final_dir}  (NDCG@10 mean {np.mean([n for _,_,_,n in boosters]):.4f})")
    return final_dir


def retrain_legacy_model(model_name: str, as_of: pd.Timestamp,
                          dry_run: bool = False) -> Path | None:
    """v11a_prime / v11a — legacy cache + single seed."""
    log(f"\n[Phase 1.{model_name}] {model_name} retrain")

    # 기존 박제 dir 의 feature_cols.json 재사용 (피처 set 동일 유지)
    src_dir = MODELS_ROOT / model_name
    if not src_dir.exists():
        log(f"  [SKIP] {src_dir} 미존재")
        return None
    feats = json.loads((src_dir / "feature_cols.json").read_text(encoding="utf-8"))
    log(f"  features: {len(feats)}")

    df = sanitize_feature_names(pd.read_parquet(LEGACY_CACHE))
    df["date"] = pd.to_datetime(df["date"])
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    lbl = con.execute("""SELECT date, ticker, fwd_return_20d
                         FROM multi_labels WHERE fwd_return_20d IS NOT NULL""").fetchdf()
    con.close()
    lbl["date"] = pd.to_datetime(lbl["date"].astype(str), format="%Y%m%d")
    df = df.merge(lbl, on=["ticker","date"], how="inner").sort_values(["date","ticker"])

    tr_end, va_s, va_e = determine_splits(as_of)
    tr = df[df["date"] <= tr_end].copy()
    va = df[(df["date"] >= va_s) & (df["date"] <= va_e)].copy()
    tr["label"] = tr["fwd_return_20d"]
    va["label"] = va["fwd_return_20d"]
    tr = tr.dropna(subset=["label"])
    va = va.dropna(subset=["label"])
    log(f"  splits: train ≤ {tr_end}, samples tr={len(tr):,} va={len(va):,}")

    missing = [c for c in feats if c not in df.columns]
    if missing:
        log(f"  [ERROR] feature 누락 {len(missing)}: {missing[:5]}")
        return None

    params = {"learning_rate": 0.05, "num_leaves": 63, "min_data_in_leaf": 100,
              "feature_fraction": 0.9, "bagging_fraction": 0.9, "bagging_freq": 5}
    t0 = datetime.now()
    booster = train_single_seed(tr, va, feats, params, seed=42)
    bi = int(booster.best_iteration)
    ndcg10 = float(booster.best_score.get("valid", {}).get("ndcg@10", 0))
    log(f"  iter {bi}  ndcg10 {ndcg10:.4f}  ({(datetime.now()-t0).total_seconds():.0f}s)")

    if dry_run:
        log("  [DRY-RUN] 박제 생략")
        return None

    suffix = as_of.strftime("%Y%m%d")
    final_dir = MODELS_ROOT / f"{model_name}_{suffix}"
    tmp_dir = final_dir.with_suffix(".tmp")
    if tmp_dir.exists(): shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    booster.save_model(str(tmp_dir / "model.txt"), num_iteration=bi)
    (tmp_dir / "feature_cols.json").write_text(json.dumps(feats, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    (tmp_dir / "meta.json").write_text(json.dumps({
        "model_version": model_name, "n_features": len(feats),
        "n_train": int(len(tr)), "n_valid": int(len(va)),
        "train_end": tr_end, "valid_end": va_e,
        "valid_ndcg10": round(ndcg10, 4), "best_iter": bi,
        "as_of": as_of.strftime("%Y-%m-%d"),
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    if final_dir.exists():
        backup = final_dir.with_name(final_dir.name + ".bak")
        if backup.exists(): shutil.rmtree(backup)
        final_dir.rename(backup)
    tmp_dir.rename(final_dir)
    log(f"  archived → {final_dir}  (NDCG@10 {ndcg10:.4f})")
    return final_dir


# ─────────────────────────────────────────────────────────────────
# Phase 2 — DB scores 적재 (3 모델)
# ─────────────────────────────────────────────────────────────────
def precompute_scores(model_version: str, model_dir: Path, dry_run: bool = False) -> int:
    """precompute_scores_v11.py 의 단축 wrapper — 3 모델별 호출."""
    log(f"\n[Phase 2.{model_version}] scores 적재")
    if dry_run:
        log("  [DRY-RUN] INSERT 생략")
        return 0
    cmd = [sys.executable, str(ML_ROOT / "precompute_scores_v11.py"),
           "--variant", model_version.replace("v11", "").lstrip("_"),
           "--overwrite",
           "--model-version-name", model_version]
    log(f"  $ {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if r.returncode == 0:
            tail = (r.stdout or "").strip().split("\n")[-5:]
            log("  stdout: " + " | ".join(tail))
            return 1
        log(f"  [FAIL] returncode={r.returncode}\n{r.stderr[-500:]}")
        return -1
    except Exception as e:
        log(f"  [ERROR] {type(e).__name__}: {e}")
        return -1


# ─────────────────────────────────────────────────────────────────
# Phase 3 — Regime classifier 갱신
# ─────────────────────────────────────────────────────────────────
def ensure_regime_table(con):
    """regime_state table 존재 보장 (idempotent)."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS regime_state (
            date BIGINT PRIMARY KEY,
            regime VARCHAR(16),
            kospi_close DOUBLE,
            ma200 DOUBLE,
            hv_60d DOUBLE,
            mom_1m DOUBLE,
            above_ma200 BOOLEAN,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def classify_regime_for_date(con, decision_date: pd.Timestamp,
                              th: dict = REGIME_THRESHOLDS) -> dict:
    """t 종가 시점에 t-1 까지의 데이터로 regime 분류 (look-ahead 차단)."""
    kospi = con.execute("""
        SELECT date, kospi_close FROM market_indices
        WHERE date < ? AND kospi_close IS NOT NULL ORDER BY date
    """, [decision_date]).fetchdf()
    kospi["date"] = pd.to_datetime(kospi["date"])
    kospi["ret"] = kospi["kospi_close"].pct_change()

    if len(kospi) < th["ma_window"] + th["hv_window"]:
        return {"regime": "unknown", "reason": "data_insufficient"}

    assert kospi["date"].max() < decision_date, \
        f"look-ahead violation: {kospi['date'].max()} >= {decision_date}"

    close = kospi["kospi_close"].values
    today_proxy = close[-1]
    ma200 = float(np.mean(close[-th["ma_window"]:]))

    rets = kospi["ret"].dropna().values[-th["hv_window"]:]
    hv_60d = float(np.std(rets, ddof=1) * np.sqrt(252))

    mom_1m = float(today_proxy / close[-th["mom_window"]-1] - 1)
    above_ma200 = today_proxy > ma200

    if above_ma200 and hv_60d < th["hv_bull_max"] and mom_1m > th["mom_bull_min"]:
        regime = "bull"
    elif (not above_ma200) and (hv_60d > th["hv_bear_min"] or mom_1m < th["mom_bear_max"]):
        regime = "bear"
    else:
        regime = "sideways"

    return {
        "regime": regime,
        "kospi_close": float(today_proxy),
        "ma200": float(ma200),
        "above_ma200": bool(above_ma200),
        "hv_60d": float(hv_60d),
        "mom_1m": float(mom_1m),
    }


def update_regime(decision_date: pd.Timestamp, dry_run: bool = False) -> dict:
    log(f"\n[Phase 3] Regime classifier — decision_date={decision_date.date()}")
    con = duckdb.connect(str(DUCKDB_PATH), read_only=False)
    try:
        ensure_regime_table(con)
        info = classify_regime_for_date(con, decision_date)
        log(f"  regime: {info['regime']}  kospi={info.get('kospi_close')}  "
            f"ma200={info.get('ma200')}  hv_60d={info.get('hv_60d')}  mom_1m={info.get('mom_1m')}")
        if dry_run:
            log("  [DRY-RUN] INSERT 생략")
            return info
        if info["regime"] == "unknown":
            log("  insufficient data — INSERT 생략")
            return info
        date_int = int(decision_date.strftime("%Y%m%d"))
        con.execute("DELETE FROM regime_state WHERE date = ?", [date_int])
        con.execute("""
            INSERT INTO regime_state
            (date, regime, kospi_close, ma200, hv_60d, mom_1m, above_ma200, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [date_int, info["regime"], info["kospi_close"], info["ma200"],
               info["hv_60d"], info["mom_1m"], info["above_ma200"]])
        log(f"  INSERTED regime_state[{decision_date.date()}] = {info['regime']}")
    finally:
        con.close()
    return info


# ─────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Regime-dep 운영 통합 cron")
    p.add_argument("--retrain", action="store_true", help="Phase 1 — 3 모델 재학습")
    p.add_argument("--daily", action="store_true", help="Phase 2 + 3 — scores + regime")
    p.add_argument("--regime-only", action="store_true", help="Phase 3 — regime 만")
    p.add_argument("--all", action="store_true", help="Phase 1+2+3 모두")
    p.add_argument("--as-of", default=None, help="기준일 YYYY-MM-DD (재학습용)")
    p.add_argument("--decision-date", default=None, help="regime 기준일 (기본: 오늘)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not (args.retrain or args.daily or args.regime_only or args.all):
        p.error("phase 선택 필수: --retrain / --daily / --regime-only / --all")

    log(f"=== deploy_regime_dep (dry_run={args.dry_run}) ===")

    as_of = pd.to_datetime(args.as_of) if args.as_of else pd.Timestamp(datetime.now().date())
    dd = pd.to_datetime(args.decision_date) if args.decision_date else pd.Timestamp(datetime.now().date())

    # Phase 1 — retrain
    if args.retrain or args.all:
        log(f"\n>>> Phase 1: 3 모델 재학습 (as_of={as_of.date()})")
        retrain_winner(as_of, dry_run=args.dry_run)
        retrain_legacy_model("v11a_prime", as_of, dry_run=args.dry_run)
        retrain_legacy_model("v11a", as_of, dry_run=args.dry_run)

    # Phase 2 — scores 적재
    if args.daily or args.all:
        log(f"\n>>> Phase 2: 3 모델 scores 적재")
        suffix = as_of.strftime("%Y%m%d")
        targets = [
            ("v11_flow_t6", f"v11_flow_t6_{suffix}"),
            ("v11a_prime",  "v11a_prime"),
            ("v11a",        "v11a"),
        ]
        for mv, dirname in targets:
            md = MODELS_ROOT / dirname
            if not md.exists():
                md = MODELS_ROOT / mv  # fallback to canonical
            if md.exists():
                precompute_scores(mv, md, dry_run=args.dry_run)
            else:
                log(f"  [SKIP] {mv}: model dir 없음")

    # Phase 3 — regime
    if args.daily or args.regime_only or args.all:
        update_regime(dd, dry_run=args.dry_run)

    log("\n=== 완료 ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
