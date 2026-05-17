# -*- coding: utf-8 -*-
"""
rolling_retrain_v11_flow_t6.py
================================
운영 롤링 재학습 cron — 분기(또는 반기) 단위로 최신 데이터까지 재학습.

`09` 가 IC 감쇠 차단의 핵심 lever 임을 증명 (정적 3~4년 내 0, 롤링 ~+0.10 유지).
본 스크립트는 `report/11_full_pipeline.md` 의 최종 winner config 를 자동 재학습한다.

Config (`11` Phase 3 winner):
  - feature set    : 9f_flow (signal9 + flow_features 16)
  - target         : T6_resid_full (sec+size+vol+mom 4-way demean)
  - hyperparams    : Optuna best (Phase 2)
  - ensemble       : 10 seeds (42~51)
  - split          : train = ALL - last_18M / valid = last_18M~last_6M / test = last_6M

설계 원칙:
  - 멱등성 (idempotent) — 같은 cutoff 로 재실행 시 동일 산출물
  - 박제 위치 : project_data/models/v11_flow_t6_{YYYYMMDD}/
  - DuckDB scores 테이블 갱신 — model_version = "v11_flow_t6"
  - 실패 시 이전 모델 유지 (atomic swap via temp dir → final dir)

운영 cron 예시 (Windows schtasks 또는 GitHub Actions):
  - 분기: 매 분기 첫 영업일 03:00 KST
  - 반기: 매 반기 첫 영업일 03:00 KST

CLI:
  py rolling_retrain_v11_flow_t6.py                      # 분기 자동 (오늘 기준)
  py rolling_retrain_v11_flow_t6.py --as-of 2026-04-29   # 명시 cutoff
  py rolling_retrain_v11_flow_t6.py --seeds 10 --dry-run  # 박제 생략
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data"))
ML_ROOT       = Path(__file__).resolve().parent  # Back/MachineLearning/
FEATURE_CACHE = CAPSTONE_ROOT / "data_pipeline" / "train_features_v9_cache_ext.parquet"
DUCKDB_PATH   = CAPSTONE_ROOT / "project_data" / "db" / "market_data.duckdb"
MODELS_ROOT   = CAPSTONE_ROOT / "project_data" / "models"

sys.path.insert(0, str(ML_ROOT))
sys.path.insert(0, str(ML_ROOT / "report" / "backtest"))
from train_lambdarank_v11 import sanitize_feature_names, bin_relevance_per_group, N_RELEVANCE_BINS  # noqa: E402
from flow_features import add_flow_features, FLOW_COLUMNS  # noqa: E402
from exp_target_eng import make_target  # noqa: E402


# 운영 winner config — 11_full_pipeline.md Phase 3
WINNER_TARGET = "T6_resid_full"
WINNER_FEATURES = "9f_flow"
WINNER_OPTUNA_PARAMS_JSON = ML_ROOT / "report" / "backtest" / "exp_optuna_t6_9fflow.json"
WINNER_SEEDS_DEFAULT = 10

# 분할 룰 — 데이터 끝 - 6M 까지 train, 마지막 6M 을 valid 로 (early stopping)
TRAIN_VALID_GAP_MONTHS = 6


def log(m):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


def load_winner_params() -> dict:
    if WINNER_OPTUNA_PARAMS_JSON.exists():
        with open(WINNER_OPTUNA_PARAMS_JSON, encoding="utf-8") as f:
            j = json.load(f)
        return j.get("best_params", j)
    log(f"[WARN] Optuna params 없음 ({WINNER_OPTUNA_PARAMS_JSON}) — 디폴트 사용")
    return {}


def determine_splits(as_of: pd.Timestamp) -> tuple[str, str, str]:
    """as_of 기준 (train_end, valid_start, valid_end)."""
    valid_end = as_of
    valid_start = (valid_end - pd.DateOffset(months=TRAIN_VALID_GAP_MONTHS)).normalize()
    # train end = valid_start - 1 day
    train_end = valid_start - pd.Timedelta(days=1)
    return (train_end.strftime("%Y-%m-%d"),
            valid_start.strftime("%Y-%m-%d"),
            valid_end.strftime("%Y-%m-%d"))


def train_single_seed(tr, va, feats, params: dict, seed: int):
    tr_rel = bin_relevance_per_group(tr)
    va_rel = bin_relevance_per_group(va)
    tr_grp = tr.groupby("date", sort=True).size().to_numpy()
    va_grp = va.groupby("date", sort=True).size().to_numpy()
    dtrain = lgb.Dataset(tr[feats].astype(np.float32).fillna(0.0).to_numpy(),
                         label=tr_rel, group=tr_grp)
    dvalid = lgb.Dataset(va[feats].astype(np.float32).fillna(0.0).to_numpy(),
                         label=va_rel, group=va_grp, reference=dtrain)
    base = {
        "objective": "lambdarank", "metric": "ndcg", "ndcg_eval_at": [10],
        "label_gain": list(range(N_RELEVANCE_BINS)),
        "verbose": -1, "seed": seed,
    }
    base.update(params)
    booster = lgb.train(base, dtrain, num_boost_round=500,
                        valid_sets=[dvalid], valid_names=["valid"],
                        callbacks=[lgb.early_stopping(30, verbose=False)])
    return booster


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--as-of", default=None, help="cutoff date (default = data 끝)")
    p.add_argument("--seeds", type=int, default=WINNER_SEEDS_DEFAULT)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out-dir-suffix", default=None,
                   help="박제 디렉터리 접미사 override (default = as_of YYYYMMDD)")
    args = p.parse_args()

    log("=== rolling_retrain_v11_flow_t6 ===")
    log(f"  target={WINNER_TARGET}  features={WINNER_FEATURES}  seeds={args.seeds}")

    params = load_winner_params()
    log(f"  optuna params: {params}")

    # 1. 데이터 로드 + flow features
    log("  loading feature cache …")
    df = sanitize_feature_names(pd.read_parquet(FEATURE_CACHE))
    df["date"] = pd.to_datetime(df["date"])
    log(f"    cache: {df.shape}")
    log("  engineering flow features …")
    df = add_flow_features(df, sort=True)
    log(f"    + {len(FLOW_COLUMNS)} flow cols")

    # 2. labels join
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    lbl = con.execute("""SELECT date, ticker, fwd_return_20d, sharpe_20d
                         FROM multi_labels WHERE fwd_return_20d IS NOT NULL""").fetchdf()
    con.close()
    lbl["date"] = pd.to_datetime(lbl["date"].astype(str), format="%Y%m%d")
    df = df.merge(lbl, on=["ticker", "date"], how="inner").sort_values(["date", "ticker"])
    data_end = df["date"].max()
    log(f"    joined: {df.shape}  data_end={data_end.date()}")

    # 3. 분할 결정
    as_of = pd.to_datetime(args.as_of) if args.as_of else data_end
    tr_end, va_start, va_end = determine_splits(as_of)
    log(f"  splits: train ≤ {tr_end}  valid {va_start} ~ {va_end}")
    tr_full = df[df["date"] <= tr_end].copy()
    va_full = df[(df["date"] >= va_start) & (df["date"] <= va_end)].copy()
    tr_full["label"] = make_target(tr_full, WINNER_TARGET)
    va_full["label"] = make_target(va_full, WINNER_TARGET)
    tr = tr_full.dropna(subset=["label"])
    va = va_full.dropna(subset=["label"])
    log(f"    train: {len(tr):,}  valid: {len(va):,}")

    # 4. feature set
    feat9 = json.loads((ML_ROOT / "v11_signal9_allowlist.json").read_text(encoding="utf-8"))
    feats = feat9 + FLOW_COLUMNS
    log(f"    n_features: {len(feats)}")

    # 5. 학습 (N seeds)
    seeds = list(range(42, 42 + args.seeds))
    boosters = []
    for sd in seeds:
        t0 = datetime.now()
        booster = train_single_seed(tr, va, feats, params, sd)
        bi = int(booster.best_iteration)
        ndcg10 = float(booster.best_score.get("valid", {}).get("ndcg@10", 0))
        dt = (datetime.now() - t0).total_seconds()
        log(f"    seed {sd:>3}: iter {bi:>3}  ndcg10 {ndcg10:.4f}  ({dt:.0f}s)")
        boosters.append((sd, booster, bi, ndcg10))

    # 6. 박제 (atomic swap)
    if args.dry_run:
        log("--- dry-run (박제 생략) ---")
        return 0

    suffix = args.out_dir_suffix or as_of.strftime("%Y%m%d")
    final_dir = MODELS_ROOT / f"v11_flow_t6_{suffix}"
    tmp_dir = final_dir.with_suffix(".tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    for sd, booster, bi, ndcg10 in boosters:
        booster.save_model(str(tmp_dir / f"model_seed{sd}.txt"), num_iteration=bi)
    (tmp_dir / "feature_cols.json").write_text(
        json.dumps(feats, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "model_version":   "v11_flow_t6",
        "config_lineage":  "11_full_pipeline.md Phase 3 winner",
        "target":          WINNER_TARGET,
        "feature_set":     WINNER_FEATURES,
        "n_features":      len(feats),
        "n_train_rows":    int(len(tr)),
        "n_valid_rows":    int(len(va)),
        "train_end":       tr_end,
        "valid_start":     va_start,
        "valid_end":       va_end,
        "as_of":           as_of.strftime("%Y-%m-%d"),
        "data_end":        data_end.strftime("%Y-%m-%d"),
        "lgb_params":      params,
        "seeds":           seeds,
        "best_iters":      [bi for _, _, bi, _ in boosters],
        "valid_ndcg10":    [round(n, 4) for _, _, _, n in boosters],
        "valid_ndcg10_mean": round(float(np.mean([n for _, _, _, n in boosters])), 4),
        "built_at":        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "retrain_command": " ".join(sys.argv),
    }
    (tmp_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # atomic swap
    if final_dir.exists():
        backup = final_dir.with_name(final_dir.name + ".bak")
        if backup.exists():
            shutil.rmtree(backup)
        final_dir.rename(backup)
        log(f"  previous version moved → {backup}")
    tmp_dir.rename(final_dir)
    log(f"  archived → {final_dir}")
    log(f"  valid_ndcg10 mean: {meta['valid_ndcg10_mean']:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
