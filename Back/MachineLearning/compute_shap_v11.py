"""
compute_shap_v11.py
===================
v11 lambdarank 모델의 SHAP 기여도 → `scores.top_factors` 적재.

설계:
  - v9 compute_shap.py 의 v11 변형. v11 은 단일 LightGBM lambdarank 모델이라
    pred_contrib 단일 호출로 SHAP 추출 가능.
  - precompute_scores_v11 과 동일 전처리(sanitize_feature_names + DART 부착)
    적용 후 동일 X 매트릭스에서 SHAP 계산.
  - 적재 대상: scores.top_factors WHERE model_version=v11{variant} AND top_factors IS NULL.

사용:
  py compute_shap_v11.py --variant a_prime_dart                  # 전체
  py compute_shap_v11.py --variant a_prime_dart --latest-only    # 최신 일자만
  py compute_shap_v11.py --variant a_prime_dart --date 2026-04-29
  py compute_shap_v11.py --variant a_prime_dart --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional

import duckdb
import numpy as np
import pandas as pd
import lightgbm as lgb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shap_extractor import (
    extract_top_factors_batch,
    load_descriptions,
    serialize_top_factors,
)
from train_lambdarank_v11 import sanitize_feature_names


warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data"))
DB_PATH       = Path(os.getenv("DUCKDB_PATH",
                                str(CAPSTONE_ROOT / "project_data" / "db" / "market_data.duckdb")))
INPUT_FILE    = CAPSTONE_ROOT / "data_pipeline" / "inference_input_v5.parquet"
MODELS_ROOT   = CAPSTONE_ROOT / "project_data" / "models"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_v11_artifacts(variant: str) -> tuple[lgb.Booster, list[str]]:
    model_dir = MODELS_ROOT / f"v11{variant}"
    if not model_dir.exists():
        raise FileNotFoundError(f"v11{variant} 모델 디렉터리 없음: {model_dir}")
    booster = lgb.Booster(model_file=str(model_dir / "model.txt"))
    feature_cols = json.loads((model_dir / "feature_cols.json").read_text(encoding="utf-8"))
    log(f"  v11{variant} loaded: {len(feature_cols)} features, {booster.num_trees()} trees")
    return booster, feature_cols


def ensure_top_factors_column(con: duckdb.DuckDBPyConnection) -> None:
    cols = {row[1] for row in con.execute("PRAGMA table_info('scores')").fetchall()}
    if "top_factors" not in cols:
        con.execute("ALTER TABLE scores ADD COLUMN top_factors VARCHAR")
        log("  Added column scores.top_factors")


def load_scored_keys(
    con: duckdb.DuckDBPyConnection,
    model_version: str,
    *,
    target_date: Optional[str] = None,
) -> pd.DataFrame:
    where = "model_version = ?"
    params: list = [model_version]
    if target_date:
        where += " AND CAST(date AS VARCHAR) = ?"
        params.append(target_date)
    sql = f"""
        SELECT CAST(date AS VARCHAR) AS date_str, ticker
        FROM scores
        WHERE {where}
          AND (top_factors IS NULL OR top_factors = '')
    """
    return con.execute(sql, params).fetchdf()


def main() -> int:
    parser = argparse.ArgumentParser(description="v11 SHAP → scores.top_factors")
    parser.add_argument("--variant", default="a_prime_dart",
                        help="모델 디렉터리 접미사 (예: a_prime, a_prime_dart).")
    parser.add_argument("--model-version-name", default=None,
                        help="DB model_version 값 (기본: v11{variant}).")
    parser.add_argument("--latest-only", action="store_true")
    parser.add_argument("--date", default=None)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    model_version = args.model_version_name or f"v11{args.variant}"
    log(f"=== compute_shap_v11 ({model_version}) ===")
    log(f"  DuckDB: {DB_PATH}")
    log(f"  parquet: {INPUT_FILE.name}")

    if not DB_PATH.exists():
        log(f"[ERROR] DuckDB 없음: {DB_PATH}")
        return 1
    if not INPUT_FILE.exists():
        log(f"[ERROR] 추론 입력 없음: {INPUT_FILE}")
        return 1

    booster, feature_cols = load_v11_artifacts(args.variant)
    descriptions = load_descriptions()

    log(f"Loading inference input …")
    df_raw = pd.read_parquet(INPUT_FILE)
    df_raw["date"] = pd.to_datetime(df_raw["date"])
    df_raw["date_str"] = df_raw["date"].dt.strftime("%Y-%m-%d")
    log(f"  rows: {len(df_raw):,}  range: {df_raw['date_str'].min()} ~ {df_raw['date_str'].max()}")

    target_date = args.date
    if args.latest_only and not target_date:
        target_date = df_raw["date_str"].max()
        log(f"  --latest-only → {target_date}")
    if target_date:
        df_raw = df_raw[df_raw["date_str"] == target_date].copy()
        if df_raw.empty:
            log(f"[ERROR] {target_date} 데이터 없음")
            return 2

    # DART feature 부착 (precompute_scores_v11 과 동일 로직)
    dart_needed = [c for c in feature_cols if c.startswith("dart_")]
    if dart_needed:
        log(f"  attaching DART features ({len(dart_needed)}) …")
        from dart_features import build_features_table, load_disclosures_from_duckdb
        disc = load_disclosures_from_duckdb(str(DB_PATH))
        target_dt = df_raw[["ticker", "date"]].copy()
        feats = build_features_table(disc, target_dt)
        df_raw = df_raw.merge(feats, on=["ticker", "date"], how="left")
        df_raw[dart_needed] = df_raw[dart_needed].fillna(0).astype("int32")

    df_raw = sanitize_feature_names(df_raw)

    # dry-run 은 read-only (실행 중인 FastAPI 와 동시 가능). 실제 UPDATE 는 write lock 필요.
    con = duckdb.connect(str(DB_PATH), read_only=args.dry_run)
    try:
        if not args.dry_run:
            ensure_top_factors_column(con)
        pending = load_scored_keys(con, model_version, target_date=target_date)
        log(f"  pending in scores (top_factors NULL): {len(pending):,}")
        if pending.empty:
            log("Nothing to do.")
            return 0

        # join — date_str + ticker 매칭
        df_raw["ticker"] = df_raw["ticker"].astype(str).str.zfill(6)
        pending["ticker"] = pending["ticker"].astype(str).str.zfill(6)
        df_subset = df_raw.merge(
            pending, on=["date_str", "ticker"], how="inner",
        )
        log(f"  computing SHAP for: {len(df_subset):,} rows")
        if df_subset.empty:
            log("[WARN] pending rows 와 inference_input 매칭 0건.")
            return 0

        # Missing 컬럼 0 채움 (v11 precompute 와 동일)
        for c in feature_cols:
            if c not in df_subset.columns:
                df_subset[c] = 0.0
        X = df_subset[feature_cols].astype(np.float32).fillna(0.0).to_numpy()
        log(f"  X shape: {X.shape}")

        contribs = booster.predict(X, pred_contrib=True,
                                    num_iteration=booster.best_iteration)
        log(f"  pred_contrib shape: {contribs.shape}  (last col = bias)")

        # v11 은 col_name_map 없음 — feature 이름 자체가 사용자 한글일 수도 있고
        # sanitize 처리된 ASCII 일 수도 있음. descriptions yaml 의 키와 매칭.
        factors_list = extract_top_factors_batch(
            contribs,
            feature_names=feature_cols,
            top_k=args.top_k,
            descriptions=descriptions,
            col_name_map_inv=None,
        )

        df_update = pd.DataFrame({
            "date":         df_subset["date_str"].values,
            "ticker":       df_subset["ticker"].values,
            "top_factors":  [serialize_top_factors(f) for f in factors_list],
        })

        if args.dry_run:
            log("--- dry-run preview (top 3) ---")
            print(df_update.head(3).to_string(index=False))
            sample = factors_list[0] if factors_list else []
            print(f"\nFirst row factors:\n{json.dumps(sample, ensure_ascii=False, indent=2)}")
            return 0

        con.register("df_update", df_update)
        con.execute(f"""
            UPDATE scores
            SET top_factors = u.top_factors
            FROM df_update u
            WHERE scores.model_version = '{model_version}'
              AND CAST(scores.date AS VARCHAR) = u.date
              AND scores.ticker = u.ticker
        """)
        log(f"  Updated rows: {len(df_update):,}")
        log("Done.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
