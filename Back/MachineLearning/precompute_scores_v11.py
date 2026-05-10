"""
precompute_scores_v11.py
========================
W7B Step 2 — v11{variant} 모델 점수 → DuckDB `scores` 테이블 적재.

목적:
  AB_SPLIT 분기 활성 시 라우터가 model_version="v11a_prime" 으로 svc.get_recommendations
  를 호출. svc 는 scores 테이블을 조회하므로 사전 적재가 필수.
  v9 와 *동일 schema·동일 DB* 에 model_version 만 다르게 INSERT — 라우터 코드 변경 X.

흐름:
  1. v11{variant} model.txt + feature_cols.json 로드.
  2. inference_input_v5.parquet 로드 → sanitize → predict → score (raw lambdarank).
  3. 날짜별 백분위 → score 1~100 (v9 와 동일 정의), tier A/B/C/D.
  4. seed.csv 로 name·sector·mid_sector 보완.
  5. scores 테이블 INSERT (model_version="v11{variant}_prime" 등 명시).

scores 테이블 schema 는 *v9 prob_lgbm/xgb/cat 컬럼* 을 기대. v11 LightGBM lambdarank 는 단일 모델이라:
  - prob_lgbm     = raw lambdarank score (참고용)
  - prob_xgb·cat  = NULL
  - prob_ensemble = raw lambdarank score (svc 가 prob_ensemble 로도 정렬할 수 있음)
  - score·tier    = 백분위 변환 (라우터·UI 가 사용하는 핵심)

사용:
  py precompute_scores_v11.py --variant a_prime
  py precompute_scores_v11.py --variant a_prime --overwrite   # 재적재
  py precompute_scores_v11.py --variant a_prime --dry-run     # INSERT 생략
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import duckdb
import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_schema import assert_aligned
from train_lambdarank_v11 import sanitize_feature_names


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data"))
INFER_PARQUET = CAPSTONE_ROOT / "data_pipeline" / "inference_input_v5.parquet"
SEED_CSV      = CAPSTONE_ROOT / "project_data" / "preprocessing" / "seed.csv"
DUCKDB_PATH   = Path(os.getenv("DUCKDB_PATH",
                               str(CAPSTONE_ROOT / "project_data" / "db" / "market_data.duckdb")))
MODELS_ROOT   = CAPSTONE_ROOT / "project_data" / "models"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 점수 변환 (v9 와 동일) ──────────────────────────────────────────────────

def score_and_tier(df: pd.DataFrame, raw_col: str = "raw_score") -> pd.DataFrame:
    """
    raw_col → 날짜별 백분위 → score 1~100 (1등 100, 최하위 0) + tier ABCD.
    v9 precompute_scores.compute_scores 와 동일 정의.
    """
    df["rank_in_date"]  = df.groupby("date")[raw_col].rank(ascending=False, method="min").astype(int)
    df["total_in_date"] = df.groupby("date")[raw_col].transform("count").astype(int)
    pct = (df["rank_in_date"] - 1) / (df["total_in_date"] - 1).clip(lower=1)
    df["score"] = ((1.0 - pct) * 100).clip(0, 100).round(1)
    df["tier"]  = pd.cut(
        df["score"],
        bins=[-0.1, 40, 60, 80, 100.1],
        labels=["D", "C", "B", "A"],
    ).astype(str)
    return df


# ── 데이터 로딩 ─────────────────────────────────────────────────────────────

def load_model(variant: str) -> tuple[lgb.Booster, list[str]]:
    model_dir = MODELS_ROOT / f"v11{variant}"
    booster = lgb.Booster(model_file=str(model_dir / "model.txt"))
    feature_cols = json.loads((model_dir / "feature_cols.json").read_text(encoding="utf-8"))
    return booster, feature_cols


def join_seed(df: pd.DataFrame) -> pd.DataFrame:
    """seed.csv → name, sector(wics_large_name), mid_sector(wics_mid_name) 보완."""
    if not SEED_CSV.exists():
        log(f"  [WARN] seed.csv 부재: {SEED_CSV}")
        df["name"] = None
        df["mid_sector"] = None
        if "sector" not in df.columns:
            df["sector"] = None
        return df
    seed = pd.read_csv(SEED_CSV, dtype={"ticker": str},
                       usecols=["ticker", "name", "wics_large_name", "wics_mid_name"])
    seed["ticker"] = seed["ticker"].str.zfill(6)
    out = df.merge(seed.rename(columns={
        "wics_large_name": "_sector_seed",
        "wics_mid_name":   "mid_sector",
    }), on="ticker", how="left")
    if "sector" not in out.columns:
        out["sector"] = out["_sector_seed"]
    else:
        out["sector"] = out["sector"].fillna(out["_sector_seed"])
    out.drop(columns=["_sector_seed"], inplace=True, errors="ignore")
    return out


# ── 적재 ────────────────────────────────────────────────────────────────────

def upsert_scores(con: duckdb.DuckDBPyConnection, df: pd.DataFrame,
                  model_version: str, overwrite: bool) -> int:
    """
    v9 precompute_scores 와 동일 schema. PK=(date, ticker, model_version).
    실제 schema 는 PK 가 없을 수 있어 overwrite 옵션 별도 처리.
    """
    cols = [
        "date", "ticker", "name", "sector", "mid_sector", "close",
        "prob_lgbm", "prob_xgb", "prob_cat", "prob_ensemble",
        "score", "rank_in_date", "total_in_date", "tier",
        "model_version", "inserted_at",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols]

    if overwrite:
        n_del = con.execute(
            "DELETE FROM scores WHERE model_version = ?", [model_version],
        ).fetchone()
        log(f"  overwrite: {model_version} 기존 행 삭제")

    existing = con.execute(
        "SELECT COUNT(*) FROM scores WHERE model_version = ?", [model_version],
    ).fetchone()[0]
    if existing > 0 and not overwrite:
        log(f"  [SKIP] {model_version} 이미 {existing:,}행. --overwrite 명시 시 재적재.")
        return 0

    # 명시적 컬럼 INSERT — top_factors 등 추후 컬럼 추가에도 안전.
    con.register("upsert_df", df)
    con.execute(f"""
        INSERT INTO scores ({', '.join(cols)})
        SELECT {', '.join(cols)} FROM upsert_df
    """)
    con.unregister("upsert_df")
    return len(df)


# ── 메인 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="W7B Step 2 — v11 점수 scores 테이블 적재")
    parser.add_argument("--variant", default="a_prime",
                        help="모델 디렉터리 접미사 (예: a, a_prime, b).")
    parser.add_argument("--model-version-name", default=None,
                        help="DB 의 model_version 컬럼 값 (기본: v11{variant}).")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run",   action="store_true")
    args = parser.parse_args()

    name = args.model_version_name or f"v11{args.variant}"
    log("=== precompute_scores_v11 (W7B Step 2) ===")
    log(f"  variant:        v11{args.variant}")
    log(f"  model_version:  {name}")
    log(f"  DuckDB:         {DUCKDB_PATH}")

    booster, feature_cols = load_model(args.variant)
    log(f"  features (model): {len(feature_cols)}")

    df = pd.read_parquet(INFER_PARQUET)
    df = sanitize_feature_names(df)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    log(f"  inference rows: {len(df):,}")

    # 차차기 W4 — schema 카테고리 일치 검증 (numeric 기대 컬럼이 numeric 인지).
    # 이전 missing 검사는 schema 가 흡수.
    assert_aligned(df, where="precompute_scores_v11", required=feature_cols)

    X = df[feature_cols].astype(np.float32).fillna(0.0).to_numpy()
    df["raw_score"] = booster.predict(X, num_iteration=booster.best_iteration)
    df["prob_lgbm"]     = df["raw_score"].astype(np.float32)
    df["prob_xgb"]      = None
    df["prob_cat"]      = None
    df["prob_ensemble"] = df["raw_score"].astype(np.float32)

    log("  scoring (백분위·tier) …")
    df = score_and_tier(df, raw_col="raw_score")

    log("  joining seed (name·sector·mid_sector) …")
    df = join_seed(df)

    df["model_version"] = name
    df["inserted_at"]   = datetime.now(timezone.utc).isoformat(timespec="seconds")

    log(f"  score range: {df['score'].min():.1f} ~ {df['score'].max():.1f}")
    log(f"  tier counts: {df['tier'].value_counts().to_dict()}")

    if args.dry_run:
        log("--- dry-run (적재 생략) ---")
        return 0

    if not DUCKDB_PATH.exists():
        log(f"[ERROR] DuckDB 없음: {DUCKDB_PATH}")
        return 1

    con = duckdb.connect(str(DUCKDB_PATH))
    try:
        n = upsert_scores(con, df, model_version=name, overwrite=args.overwrite)
        if n > 0:
            log(f"  inserted: {n:,} rows ({name})")
        total = con.execute(
            "SELECT COUNT(*) FROM scores WHERE model_version = ?", [name]
        ).fetchone()[0]
        log(f"  scores total ({name}): {total:,}")
    finally:
        con.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
