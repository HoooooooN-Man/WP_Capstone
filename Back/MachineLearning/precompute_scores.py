"""
precompute_scores.py
====================
v7 / 미래 모델의 test_predictions parquet 3종(LGBM·XGB·CatBoost)을 병합하여
날짜별 백분위 점수(1~100)·티어·랭크를 계산하고 scores.duckdb 에 append 합니다.

사용법:
    # v7 기본 경로 (CAPSTONE_ROOT 자동 감지)
    python precompute_scores.py --model-version v7

    # 경로 직접 지정 (새 모델 추가 시)
    python precompute_scores.py --model-version v8 \\
        --lgbm path/to/lgbm_test_predictions.parquet \\
        --xgb  path/to/xgb_test_predictions.parquet \\
        --cat  path/to/cat_test_predictions.parquet

    # 기존 버전 데이터 덮어쓰기 (재적재)
    python precompute_scores.py --model-version v7 --overwrite
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

# ── 경로 설정 ────────────────────────────────────────────────────────────────
# Back/MachineLearning/precompute_scores.py → Back/ → WP_Capstone/ → Capstone Data/
_HERE = Path(__file__).resolve().parent          # Back/MachineLearning/
_BACK = _HERE.parent                              # Back/
_REPO = _BACK.parent                              # WP_Capstone/
CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", str(_REPO.parent)))  # Capstone Data/

# 기본 parquet 경로 (버전 → 폴더명 매핑)
_DEFAULT_MODEL_DIRS: dict[str, dict[str, str]] = {
    "v7": {
        "lgbm": str(CAPSTONE_ROOT / "models" / "v7_alpha_target" / "LightGBM" / "model_output" / "lgbm_test_predictions.parquet"),
        "xgb":  str(CAPSTONE_ROOT / "models" / "v7_alpha_target" / "XGBoost"  / "model_output" / "xgb_test_predictions.parquet"),
        "cat":  str(CAPSTONE_ROOT / "models" / "v7_alpha_target" / "CatBoost" / "model_output" / "cat_test_predictions.parquet"),
    },
    "v6": {
        "lgbm": str(CAPSTONE_ROOT / "models" / "v6_advanced" / "LightGBM" / "model_output_advanced" / "lgbm_test_predictions.parquet"),
        "xgb":  str(CAPSTONE_ROOT / "models" / "v6_advanced" / "XGBoost"  / "model_output_advanced" / "xgb_test_predictions.parquet"),
        "cat":  str(CAPSTONE_ROOT / "models" / "v6_advanced" / "CatBoost" / "model_output_advanced" / "cat_test_predictions.parquet"),
    },
}

SEED_CSV    = CAPSTONE_ROOT / "preprocessing" / "seed.csv"
DUCKDB_PATH = _BACK / "FastAPI" / "scores.duckdb"

# ── 스코어 계산 ───────────────────────────────────────────────────────────────

def load_and_merge(lgbm_path: str, xgb_path: str, cat_path: str) -> pd.DataFrame:
    """parquet 3종 로드 및 병합."""
    print("  [1/4] parquet 로드 중...")
    df_l = pd.read_parquet(lgbm_path, columns=["date", "종목코드", "wics_large_name", "close", "prob_lgbm"])
    df_x = pd.read_parquet(xgb_path,  columns=["date", "종목코드", "prob_xgb"])
    df_c = pd.read_parquet(cat_path,   columns=["date", "종목코드", "prob_cat"])

    df = (
        df_l
        .merge(df_x, on=["date", "종목코드"], how="inner")
        .merge(df_c, on=["date", "종목코드"], how="inner")
    )
    df["date"] = pd.to_datetime(df["date"]).dt.date
    print(f"     병합 완료: {len(df):,}행 / 날짜 {df['date'].nunique()}개 / 종목 {df['종목코드'].nunique()}개")
    return df


def join_seed(df: pd.DataFrame) -> pd.DataFrame:
    """seed.csv 에서 종목명·섹터를 join하여 None 보완."""
    print("  [2/4] seed.csv join 중...")
    if not SEED_CSV.exists():
        print(f"     [WARN] seed.csv 없음 ({SEED_CSV}) — 섹터·종목명 None으로 유지")
        df["name"]       = None
        df["mid_sector"] = None
        return df

    seed = pd.read_csv(
        SEED_CSV,
        dtype={"ticker": str},
        usecols=["ticker", "name", "wics_large_name", "wics_mid_name"],
    )
    seed["ticker"] = seed["ticker"].str.zfill(6)
    df["종목코드"] = df["종목코드"].astype(str).str.zfill(6)

    df = df.merge(
        seed.rename(columns={
            "ticker": "종목코드",
            "wics_large_name": "_sector_seed",
            "wics_mid_name": "mid_sector",
        }),
        on="종목코드",
        how="left",
    )
    # parquet에 있는 섹터 우선, None이면 seed로 채움
    df["sector"] = df["wics_large_name"].where(
        df["wics_large_name"].notna(), df["_sector_seed"]
    )
    df.drop(columns=["wics_large_name", "_sector_seed"], inplace=True)
    print(f"     섹터 보완 완료 (non-null: {df['sector'].notna().sum():,}/{len(df):,})")
    return df


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    """앙상블 확률 → 날짜별 백분위 점수·티어·랭크."""
    print("  [3/4] 스코어 계산 중...")
    df["prob_ensemble"] = (df["prob_lgbm"] + df["prob_xgb"] + df["prob_cat"]) / 3.0

    # 날짜별 내림차순 랭크 (1 = 가장 좋음)
    df["rank_in_date"]  = df.groupby("date")["prob_ensemble"].rank(ascending=False, method="min").astype(int)
    df["total_in_date"] = df.groupby("date")["prob_ensemble"].transform("count").astype(int)

    # 1~100 점수: 상위 1등 → 100, 최하위 → ~0
    pct = (df["rank_in_date"] - 1) / (df["total_in_date"] - 1).clip(lower=1)
    df["score"] = ((1.0 - pct) * 100).clip(0, 100).round(1)

    # 티어
    df["tier"] = pd.cut(
        df["score"],
        bins=[-0.1, 40, 60, 80, 100.1],
        labels=["D", "C", "B", "A"],
    ).astype(str)

    print(f"     점수 범위: {df['score'].min():.1f} ~ {df['score'].max():.1f}")
    return df


def save_to_duckdb(df: pd.DataFrame, model_version: str, overwrite: bool) -> None:
    """결과를 scores.duckdb 에 저장(append 또는 overwrite)."""
    print("  [4/4] DuckDB 저장 중...")
    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)

    df["model_version"] = model_version
    df["inserted_at"]   = datetime.utcnow().isoformat()

    # 컬럼 순서 통일 (스키마 계약)
    cols = [
        "date", "종목코드", "name", "sector", "mid_sector", "close",
        "prob_lgbm", "prob_xgb", "prob_cat", "prob_ensemble",
        "score", "rank_in_date", "total_in_date", "tier",
        "model_version", "inserted_at",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].rename(columns={"종목코드": "ticker"})

    con = duckdb.connect(str(DUCKDB_PATH))
    con.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            date          DATE,
            ticker        VARCHAR,
            name          VARCHAR,
            sector        VARCHAR,
            mid_sector    VARCHAR,
            close         FLOAT,
            prob_lgbm     FLOAT,
            prob_xgb      FLOAT,
            prob_cat      FLOAT,
            prob_ensemble FLOAT,
            score         FLOAT,
            rank_in_date  INTEGER,
            total_in_date INTEGER,
            tier          VARCHAR,
            model_version VARCHAR,
            inserted_at   VARCHAR
        )
    """)

    if overwrite:
        con.execute("DELETE FROM scores WHERE model_version = ?", [model_version])
        print(f"     기존 {model_version} 데이터 삭제 완료")

    existing = con.execute(
        "SELECT COUNT(*) FROM scores WHERE model_version = ?", [model_version]
    ).fetchone()[0]
    if existing > 0 and not overwrite:
        print(f"     [SKIP] {model_version} 이미 {existing:,}행 존재 (재적재하려면 --overwrite 사용)")
        con.close()
        return

    con.execute("INSERT INTO scores SELECT * FROM df")
    total = con.execute("SELECT COUNT(*) FROM scores WHERE model_version = ?", [model_version]).fetchone()[0]
    con.close()
    print(f"     저장 완료: {model_version} → {total:,}행")
    print(f"     DuckDB: {DUCKDB_PATH}")


# ── 진입점 ────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="parquet → scores.duckdb 적재")
    ap.add_argument("--model-version", required=True, help="모델 버전 태그 (예: v7, v8)")
    ap.add_argument("--lgbm", default=None, help="LightGBM test_predictions.parquet 경로")
    ap.add_argument("--xgb",  default=None, help="XGBoost  test_predictions.parquet 경로")
    ap.add_argument("--cat",  default=None, help="CatBoost  test_predictions.parquet 경로")
    ap.add_argument("--overwrite", action="store_true", help="기존 버전 데이터 삭제 후 재적재")
    args = ap.parse_args()

    ver = args.model_version
    defaults = _DEFAULT_MODEL_DIRS.get(ver, {})

    lgbm = args.lgbm or defaults.get("lgbm")
    xgb  = args.xgb  or defaults.get("xgb")
    cat  = args.cat  or defaults.get("cat")

    missing = [name for name, p in [("--lgbm", lgbm), ("--xgb", xgb), ("--cat", cat)] if not p]
    if missing:
        ap.error(f"다음 경로가 필요합니다: {', '.join(missing)}")

    for label, path in [("LGBM", lgbm), ("XGB", xgb), ("CAT", cat)]:
        if not Path(path).exists():
            print(f"[ERROR] {label} parquet 없음: {path}", file=sys.stderr)
            sys.exit(1)

    print(f"\n=== precompute_scores  model_version={ver}  overwrite={args.overwrite} ===")
    print(f"    CAPSTONE_ROOT : {CAPSTONE_ROOT}")
    print(f"    LGBM          : {lgbm}")
    print(f"    XGB           : {xgb}")
    print(f"    CAT           : {cat}")
    print()

    df = load_and_merge(lgbm, xgb, cat)
    df = join_seed(df)
    df = compute_scores(df)
    save_to_duckdb(df, model_version=ver, overwrite=args.overwrite)
    print("\n완료.")


if __name__ == "__main__":
    main()
