"""
compute_shap.py
===============
Tier 1.3 (PRD §4.4 / 차별화 §2.3) — v9 LightGBM 모델로 SHAP 기여도를 계산하고
종목별 상위 3개 기여 피처를 `scores` 테이블의 `top_factors` JSON 컬럼에 적재.

설계 원칙:
  - 운영 중인 v9_inference.py 를 건드리지 않는다 (회귀 위험).
  - 본 스크립트는 추론 *후* 단계로 동작: scores 테이블이 이미 채워져 있다는 가정.
  - top_factors 컬럼은 ALTER TABLE ADD COLUMN IF NOT EXISTS 로 비파괴 추가.
  - LightGBM 단일 모델의 SHAP 만 사용 — 앙상블 SHAP 은 캡스톤 범위 외.
    (앙상블 분산은 Tier 1.4 신뢰구간이 별도로 다룸).

사용법:
  py -3 compute_shap.py                       # 모든 v9 행에 대해 계산
  py -3 compute_shap.py --latest-only         # 가장 최신 일자만 (시연용)
  py -3 compute_shap.py --date 2026-05-06     # 특정 일자만
  py -3 compute_shap.py --dry-run             # DB 저장 생략, 미리보기만

회귀 안전망:
  - 본 스크립트 실행은 scores 테이블의 다른 컬럼을 수정하지 않는다.
  - 실패 시 top_factors 는 NULL 로 남고 API 응답은 빈 리스트 반환 (graceful).
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

from shap_extractor import (
    extract_top_factors_batch,
    load_descriptions,
    serialize_top_factors,
)


warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ── 경로 ─────────────────────────────────────────────────────────────────────

CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
MODEL_DIR     = CAPSTONE_ROOT / "models" / "v9"
DB_PATH       = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))
INPUT_FILE    = CAPSTONE_ROOT.parent / "data_pipeline" / "inference_input_v5.parquet"

LGBM_PATH = MODEL_DIR / "lgbm_model.txt"
FEAT_PATH = MODEL_DIR / "feature_cols.json"        # safe ASCII
ORIG_PATH = MODEL_DIR / "feature_cols_orig.json"   # 원본 한글
MAP_PATH  = MODEL_DIR / "col_name_map.json"
CLIP_PATH = MODEL_DIR / "clip_bounds.json"

MODEL_VERSION = "v9"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 모델·메타 로드 ─────────────────────────────────────────────────────────────

def load_artifacts():
    log("Loading v9 LightGBM + feature metadata...")

    with open(FEAT_PATH, encoding="utf-8") as f:
        safe_cols: list[str] = json.load(f)
    with open(ORIG_PATH, encoding="utf-8") as f:
        orig_cols: list[str] = json.load(f)
    with open(MAP_PATH, encoding="utf-8") as f:
        col_name_map: dict[str, str] = json.load(f)
    with open(CLIP_PATH, encoding="utf-8") as f:
        clip_bounds: dict = json.load(f)

    import lightgbm as lgb
    booster = lgb.Booster(model_file=str(LGBM_PATH))
    log(f"  Features: {len(safe_cols)} | Booster trees: {booster.num_trees()}")

    # safe → orig 역매핑 (자연어 변환에 사용).
    inv_map = {safe: orig for orig, safe in col_name_map.items()}

    return booster, safe_cols, orig_cols, col_name_map, inv_map, clip_bounds


def preprocess(df_raw: pd.DataFrame, orig_cols, col_name_map, clip_bounds) -> pd.DataFrame:
    """v9_inference.py 의 preprocess 와 동일 순서. 누락 컬럼 0 채움 → clip → rename."""
    for c in orig_cols:
        if c not in df_raw.columns:
            df_raw[c] = 0.0
    X = df_raw[orig_cols].copy().replace([np.inf, -np.inf], np.nan)
    for orig_col, b in clip_bounds.items():
        if orig_col in X.columns:
            X[orig_col] = X[orig_col].clip(b["lo"], b["hi"])
    X = X.fillna(0.0).astype(np.float32)
    X.columns = [col_name_map.get(c, c) for c in orig_cols]
    return X


# ── DuckDB 헬퍼 ────────────────────────────────────────────────────────────────

def ensure_top_factors_column(con: duckdb.DuckDBPyConnection) -> None:
    """scores 테이블에 top_factors VARCHAR 컬럼이 없으면 추가 (idempotent)."""
    # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk).
    cols = {row[1] for row in con.execute("PRAGMA table_info('scores')").fetchall()}
    if "top_factors" not in cols:
        con.execute("ALTER TABLE scores ADD COLUMN top_factors VARCHAR")
        log("  Added column scores.top_factors")
    else:
        log("  scores.top_factors already exists")


def load_scored_keys(
    con: duckdb.DuckDBPyConnection,
    *,
    target_date: Optional[str] = None,
) -> pd.DataFrame:
    """SHAP 을 채워야 할 (date, ticker) 키 목록 — 이미 채워진 행은 제외 (idempotent)."""
    where = "model_version = ?"
    params: list = [MODEL_VERSION]
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


# ── 메인 파이프라인 ────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="v9 SHAP 기여도 → scores.top_factors 적재")
    parser.add_argument("--latest-only", action="store_true",
                        help="가장 최신 일자만 처리 (시연용 빠른 모드)")
    parser.add_argument("--date", help="특정 일자(YYYY-MM-DD)만 처리")
    parser.add_argument("--top-k", type=int, default=3, help="저장할 상위 기여 피처 수")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 생략")
    args = parser.parse_args()

    if not DB_PATH.exists():
        log(f"[ERROR] DuckDB 없음: {DB_PATH}")
        return 1
    if not INPUT_FILE.exists():
        log(f"[ERROR] 추론 입력 parquet 없음: {INPUT_FILE}")
        return 1
    if not LGBM_PATH.exists():
        log(f"[ERROR] v9 LightGBM 모델 없음: {LGBM_PATH}")
        return 1

    booster, safe_cols, orig_cols, col_name_map, inv_map, clip_bounds = load_artifacts()
    descriptions = load_descriptions()

    log(f"Loading inference input: {INPUT_FILE.name}")
    df_raw = pd.read_parquet(INPUT_FILE)
    df_raw["date"] = pd.to_datetime(df_raw["date"])
    df_raw["date_str"] = df_raw["date"].dt.strftime("%Y-%m-%d")
    log(f"  Rows: {len(df_raw):,} | Date range: {df_raw['date_str'].min()} ~ {df_raw['date_str'].max()}")

    # 처리 대상 일자 결정.
    target_date: Optional[str] = args.date
    if args.latest_only and not target_date:
        target_date = df_raw["date_str"].max()
        log(f"  --latest-only → {target_date}")

    if target_date:
        df_raw = df_raw[df_raw["date_str"] == target_date].copy()
        if df_raw.empty:
            log(f"[ERROR] {target_date} 데이터가 inference_input 에 없음")
            return 2
        log(f"  Filtered to {target_date}: {len(df_raw):,} rows")

    # 이미 채워진 행 제외 (idempotent).
    con = duckdb.connect(str(DB_PATH))
    try:
        ensure_top_factors_column(con)
        pending = load_scored_keys(con, target_date=target_date)
        log(f"  Pending rows in scores (top_factors NULL): {len(pending):,}")

        if pending.empty:
            log("Nothing to do (모든 행이 이미 채워짐).")
            return 0

        # df_raw 와 pending 을 (date, ticker) 로 inner-join.
        df_raw_subset = df_raw.merge(
            pending,
            left_on=["date_str", "ticker"],
            right_on=["date_str", "ticker"],
            how="inner",
        )
        log(f"  Computing SHAP for: {len(df_raw_subset):,} rows")

        if df_raw_subset.empty:
            log("[WARN] pending 행에 매칭되는 inference_input 이 없음. (date 불일치?)")
            return 0

        # 전처리 + SHAP.
        X = preprocess(df_raw_subset, orig_cols, col_name_map, clip_bounds)
        log(f"  X shape: {X.shape}")

        contribs = booster.predict(X.values, pred_contrib=True)
        log(f"  pred_contrib shape: {contribs.shape}  (last col = bias)")

        factors_list = extract_top_factors_batch(
            contribs,
            feature_names=safe_cols,
            top_k=args.top_k,
            descriptions=descriptions,
            col_name_map_inv=inv_map,
        )

        # 적재용 DataFrame.
        df_update = pd.DataFrame({
            "date":         df_raw_subset["date_str"].values,
            "ticker":       df_raw_subset["ticker"].values,
            "top_factors":  [serialize_top_factors(f) for f in factors_list],
        })

        if args.dry_run:
            log("--- dry-run preview (top 5) ---")
            print(df_update.head(5).to_string(index=False))
            sample = factors_list[0] if factors_list else []
            print(f"\nFirst row factors:\n{json.dumps(sample, ensure_ascii=False, indent=2)}")
            return 0

        # DuckDB UPDATE: 임시 테이블 + JOIN.
        con.register("df_update", df_update)
        updated = con.execute(f"""
            UPDATE scores
            SET top_factors = u.top_factors
            FROM df_update u
            WHERE scores.model_version = '{MODEL_VERSION}'
              AND CAST(scores.date AS VARCHAR) = u.date
              AND scores.ticker = u.ticker
        """).fetchall()
        log(f"  Updated rows: {len(df_update):,}")
        log("Done.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
