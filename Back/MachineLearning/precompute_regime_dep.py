# -*- coding: utf-8 -*-
"""
precompute_regime_dep.py — Regime-dep ensemble scores 적재
============================================================
2026-05-19 — deploy_regime_dep.py 의 Phase 2 를 대체하는 신규 적재기.

기존 precompute_scores_v11.py 는 단일 모델 inference 만 지원 (winner 의 10-seed
ensemble 미지원). 본 스크립트는 ensemble_cohort_backtest.py 의 predict_3model_scores
+ regime_dep_score 로직을 그대로 가져와 DB 에 적재한다.

흐름:
  1. fixed8 + legacy cache 로드 (BT_START=2025-01-01)
  2. 3 모델 (winner 10-seed / v11a_prime / v11a) inference → ticker × date × score
  3. 일자별 KOSPI regime 분류 (look-ahead 차단)
  4. regime → mapping → ensemble score (E2a/E2c/E3, z-score 평균 → 100점 백분위)
  5. tier 부여: score 절대 임계 (A≥80, B≥60, C≥40, D<40)
  6. 기존 v11a_prime row 의 meta (name/sector/close) JOIN
  7. DuckDB INSERT INTO scores (model_version='regime_dep')

운영 후 latest 별칭 = regime_dep 으로 전환 (env DEFAULT_MODEL_VERSION).

전제 — 박제 dir 이름 (no-suffix):
  E:\Capstone Data\project_data\models\v11_flow_t6_20260401  (winner 10-seed)
  E:\Capstone Data\project_data\models\v11a_prime            (single seed)
  E:\Capstone Data\project_data\models\v11a                  (single seed)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ML_ROOT = Path(__file__).resolve().parent
BACKTEST_ROOT = ML_ROOT / "report" / "backtest"
sys.path.insert(0, str(ML_ROOT))
sys.path.insert(0, str(BACKTEST_ROOT))

from ensemble_cohort_backtest import (  # noqa: E402
    predict_3model_scores, ensemble_score_filtered, REGIME_MAPPING,
)
from cohort_backtest_v11_flow_t6 import load_fwd_returns  # noqa: E402
from regime_filter import (  # noqa: E402
    load_kospi_series, classify_regime, REGIME_THRESHOLDS,
)

CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data"))
DB_PATH = CAPSTONE_ROOT / "project_data" / "db" / "market_data.duckdb"

MODEL_VERSION_NAME = "regime_dep"
BT_START = "2025-01-01"

# Tier 절대 임계 — 메모리 [project_tier_absolute_2026_05_17] B52 룰.
# v11a_prime 의 prob_ensemble 은 mean -0.44 / std 0.23 (lgbm raw), regime_dep score_raw 는
# mean 0 / std 0.87 (z-score 평균). 두 분포 scale 다름. 메모리의 A≥0 임계는 v11a_prime 분포
# 기준이라 ensemble 에 그대로 적용하면 A ≈ 50%.
# → 동등한 메모리 의도 (강세장 A 多 / 약세장 A 少) 위해 *전체 기간 분포 백분위* 를 절대 임계로 사용.
# 일자별 분위가 아니라 전체 322 dates 의 score_raw 분포 fitting → 시장 시기마다 A 비율 변동.
#   p80 ≈ 0.84 → A (전체 상위 20%, 강세장엔 더 多, 약세장엔 더 少)
#   p50 ≈ 0.00 → B (전체 상위 20-50%)
#   p20 ≈ -0.84 → C (전체 상위 50-80%)
#   그 외     → D (전체 하위 20%)
TIER_A_MIN_Z =  0.84
TIER_B_MIN_Z =  0.00
TIER_C_MIN_Z = -0.84


def assign_tier_by_z(z: float) -> str:
    if pd.isna(z):
        return "D"
    if z >= TIER_A_MIN_Z: return "A"
    if z >= TIER_B_MIN_Z: return "B"
    if z >= TIER_C_MIN_Z: return "C"
    return "D"


def log(m):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    log("=== precompute_regime_dep ===")
    log(f"DB: {DB_PATH}")

    # ──────────────────────────────────────────────────────────────
    # 1) 3-model inference → ticker × date × score (0-1 rank pct)
    # ──────────────────────────────────────────────────────────────
    log("[1/4] 3-model inference (fixed8 + legacy cache)")
    scores_dict = predict_3model_scores()
    if "winner" not in scores_dict:
        raise RuntimeError("winner score 미산출 — v11_flow_t6_20260401 박제 확인 필요")
    log(f"  models: {list(scores_dict.keys())}")

    # ──────────────────────────────────────────────────────────────
    # 2) 일자별 regime 분류 (look-ahead 차단)
    # ──────────────────────────────────────────────────────────────
    log("[2/4] 일자별 regime 분류")
    kospi_df = load_kospi_series()
    all_dates = sorted({d for df in scores_dict.values() for d in df["date"].unique()})
    log(f"  scoring dates: {all_dates[0].date()} ~ {all_dates[-1].date()} ({len(all_dates)} dates)")

    regime_per_date: dict[pd.Timestamp, str] = {}
    for d in all_dates:
        ri = classify_regime(kospi_df, d, REGIME_THRESHOLDS)
        regime_per_date[d] = ri["regime"]
    regime_dist = pd.Series(regime_per_date).value_counts().to_dict()
    log(f"  regime 분포: {regime_dist}")

    # ──────────────────────────────────────────────────────────────
    # 3) regime → ensemble score (100점 백분위)
    # ──────────────────────────────────────────────────────────────
    log("[3/4] regime-dep ensemble score 산출")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    fwd = load_fwd_returns(con, BT_START)
    con.close()

    # 미리 3 가지 ensemble (E2a/E2c/E3) 산출 — 일자 전체.
    ens_cache: dict[tuple, pd.DataFrame] = {}
    for regime, models in REGIME_MAPPING.items():
        key = tuple(sorted(models))
        if key not in ens_cache:
            ens_cache[key] = ensemble_score_filtered(scores_dict, fwd, list(models))
            log(f"  ensemble {key}: {ens_cache[key].shape}")

    combined_rows = []
    for d in all_dates:
        regime = regime_per_date[d]
        models = REGIME_MAPPING[regime]
        key = tuple(sorted(models))
        ens_df = ens_cache[key]
        sub = ens_df[ens_df["date"] == d].copy()
        if sub.empty:
            continue
        sub["regime"] = regime
        sub["models"] = "+".join(models)
        combined_rows.append(sub)
    combined = pd.concat(combined_rows, ignore_index=True) if combined_rows else pd.DataFrame()
    log(f"  combined rows: {len(combined):,}")

    # ──────────────────────────────────────────────────────────────
    # 4) DB 적재 — 기존 v11a_prime row 메타 JOIN + INSERT
    # ──────────────────────────────────────────────────────────────
    log("[4/4] DuckDB INSERT INTO scores")
    con = duckdb.connect(str(DB_PATH), read_only=False)

    # 메타 (date, ticker → close, name, sector, mid_sector) — v11a_prime 행 재활용
    log("  load meta from existing v11a_prime rows")
    meta = con.execute("""
        SELECT date, ticker, name, sector, mid_sector, close
        FROM scores WHERE model_version = 'v11a_prime'
    """).fetchdf()
    meta["date"] = pd.to_datetime(meta["date"])
    log(f"  meta rows: {len(meta):,}")

    combined = combined.merge(meta, on=["date", "ticker"], how="left")
    # B52 절대 임계: z-score 평균 (score_raw) 기준 tier 부여 → 시장 상황 반영.
    combined["tier"] = combined["score_raw"].apply(assign_tier_by_z)

    # rank_in_date / total_in_date
    combined["rank_in_date"] = combined.groupby("date")["score"].rank(ascending=False, method="min").astype(int)
    combined["total_in_date"] = combined.groupby("date")["score"].transform("count").astype(int)

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    combined["model_version"] = MODEL_VERSION_NAME
    combined["inserted_at"] = now_iso
    combined["prob_lgbm"] = None
    combined["prob_xgb"] = None
    combined["prob_cat"] = None
    # prob_ensemble = score/100 (0-1 범위). market_events.compute_market_score 의 avg_prob
    # 항이 (avg - 0.5) × 100 clamp ±10 으로 *0-1 범위* 를 기대 → z-score 평균 (음수 가능) 을
    # 그대로 넣으면 항상 -10 clamp 으로 시장점수 인공 하향.
    # tier 는 score_raw (z-score) 로 이미 계산 완료. prob_ensemble 은 score/100 호환.
    combined["prob_ensemble"] = combined["score"] / 100.0
    combined["top_factors"] = None

    # 기존 regime_dep 적재본 제거 (idempotent)
    n_prev = con.execute(
        "SELECT COUNT(*) FROM scores WHERE model_version = ?", [MODEL_VERSION_NAME]
    ).fetchone()[0]
    if n_prev > 0:
        log(f"  기존 {MODEL_VERSION_NAME} rows {n_prev:,} 삭제")
        con.execute("DELETE FROM scores WHERE model_version = ?", [MODEL_VERSION_NAME])

    insert_cols = [
        "date", "ticker", "name", "sector", "mid_sector", "close",
        "prob_lgbm", "prob_xgb", "prob_cat", "prob_ensemble",
        "score", "rank_in_date", "total_in_date", "tier",
        "model_version", "inserted_at", "top_factors",
    ]
    out_df = combined[insert_cols].copy()
    # DuckDB DATE 컬럼 호환: pd.Timestamp 그대로 OK
    con.register("regime_dep_in", out_df)
    con.execute(f"INSERT INTO scores ({','.join(insert_cols)}) "
                f"SELECT {','.join(insert_cols)} FROM regime_dep_in")
    con.unregister("regime_dep_in")
    n_after = con.execute(
        "SELECT COUNT(*) FROM scores WHERE model_version = ?", [MODEL_VERSION_NAME]
    ).fetchone()[0]
    log(f"  inserted {n_after:,} rows")

    # tier 분포 (참고)
    tier_dist = con.execute(
        "SELECT tier, COUNT(*) FROM scores WHERE model_version = ? GROUP BY tier ORDER BY tier",
        [MODEL_VERSION_NAME]
    ).fetchall()
    log(f"  tier dist: {dict(tier_dist)}")

    con.close()
    log("=== done ===")


if __name__ == "__main__":
    main()
