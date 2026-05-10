"""
train_lambdarank_v11.py
=======================
W5A — LightGBM LambdaRank v11 학습.

설계:
  - 입력 features: data_pipeline/train_features_v9_cache.parquet  (4.49M × 122)
  - 입력 labels:   DuckDB market_data.multi_labels                  (W4 결과)
  - join key:      (ticker, date)
  - group:         as_of_date (일별 ranking)
  - split:         v9 meta 동일 — train ≤ 2024-12-31, valid 2025-01-01~2025-09-30
  - objective:     lambdarank, label_gain=ranking from fwd_return_20d 백분위 binning
                   (LightGBM lambdarank 는 정수 relevance 필요 — 0~31 binning)

variant:
  v11a (현재) : single label fwd_return_20d, 임베딩 X
  v11b (W5B) : + 임베딩 64dim
  v11c (W5C) : alpha_20d 라벨로 변경
  v11d (W5D) : 임베딩 + alpha_20d

박제 위치: project_data/models/v11{a,b,c,d}/
  - model.txt          (LightGBM Booster)
  - feature_cols.json  (학습에 쓰인 컬럼 순서)
  - meta.json          (split·n_features·valid_ndcg10·built_at)

사용:
  py train_lambdarank_v11.py                            # variant=a (default)
  py train_lambdarank_v11.py --variant b                # 임베딩 추가
  py train_lambdarank_v11.py --target-label alpha_20d   # variant=c 라벨 교체
  py train_lambdarank_v11.py --max-rows 100000          # 빠른 시연
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import duckdb
import numpy as np
import pandas as pd


# ── 경로 ────────────────────────────────────────────────────────────────────

CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data"))
FEATURES_PARQUET = CAPSTONE_ROOT / "data_pipeline" / "train_features_v9_cache.parquet"
DUCKDB_PATH      = CAPSTONE_ROOT / "project_data" / "db" / "market_data.duckdb"
MODELS_ROOT      = CAPSTONE_ROOT / "project_data" / "models"

# v9 동일 분할.
TRAIN_END   = "2024-12-31"
VALID_START = "2025-01-01"
VALID_END   = "2025-09-30"

# group=date 안에서 fwd_return 백분위 → 정수 relevance.
# LightGBM lambdarank 는 [0, label_gain_size) 범위 정수 필요. 32-bin 이 NDCG 표준.
N_RELEVANCE_BINS = 32

# 메타·식별자 컬럼 — feature 에서 제외.
META_COLS = {
    "ticker", "date", "sector", "exchange",
    # 라벨·target 류 (혹시 cache 에 섞여있을 경우).
    "target", "fwd_return_5d", "fwd_return_20d", "fwd_return_60d",
    "alpha_5d", "alpha_20d", "alpha_60d", "sharpe_20d",
    # 식별 메타.
    "종목코드", "회사명", "wics_large_name",
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 데이터 로딩 ─────────────────────────────────────────────────────────────

def sanitize_feature_names(df: pd.DataFrame) -> pd.DataFrame:
    """LightGBM 은 feature 이름의 JSON 특수문자(괄호·콤마·공백·한글 등) 거부.
    영숫자·언더스코어로 정규화. 동일 이름 충돌 시 suffix.
    """
    rename: dict[str, str] = {}
    seen: set[str] = set()
    for col in df.columns:
        new = re.sub(r"[^0-9A-Za-z_]+", "_", str(col))
        new = re.sub(r"_+", "_", new).strip("_") or "col"
        base = new
        i = 1
        while new in seen:
            new = f"{base}_{i}"; i += 1
        seen.add(new)
        if new != col:
            rename[col] = new
    return df.rename(columns=rename) if rename else df


def load_features(max_rows: int = 0) -> pd.DataFrame:
    if not FEATURES_PARQUET.exists():
        raise FileNotFoundError(f"features parquet 없음: {FEATURES_PARQUET}")
    df = pd.read_parquet(FEATURES_PARQUET)
    df["date"] = pd.to_datetime(df["date"])
    df = sanitize_feature_names(df)
    if max_rows > 0:
        df = df.head(max_rows).copy()
    return df


def load_labels(target_label: str, dates: pd.Series) -> pd.DataFrame:
    """DuckDB multi_labels 에서 (ticker, date, label) 추출."""
    if target_label not in {"fwd_return_5d", "fwd_return_20d", "fwd_return_60d",
                            "alpha_5d", "alpha_20d", "alpha_60d", "sharpe_20d"}:
        raise ValueError(f"지원되지 않는 target_label: {target_label}")

    # date 는 DuckDB 에 BIGINT(YYYYMMDD) 로 저장됨. parquet 의 datetime 과 맞춤.
    date_min = int(dates.min().strftime("%Y%m%d"))
    date_max = int(dates.max().strftime("%Y%m%d"))

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        sql = f"""
            SELECT date, ticker, {target_label} AS label
            FROM multi_labels
            WHERE date BETWEEN {date_min} AND {date_max}
              AND {target_label} IS NOT NULL
        """
        df = con.execute(sql).fetchdf()
    finally:
        con.close()

    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")
    return df


def join_features_labels(feat_df: pd.DataFrame, lbl_df: pd.DataFrame) -> pd.DataFrame:
    merged = feat_df.merge(lbl_df, on=["ticker", "date"], how="inner")
    return merged.sort_values(["date", "ticker"]).reset_index(drop=True)


# ── 임베딩 (v11b 이상) ─────────────────────────────────────────────────────

def _embeddings_from_pg() -> Optional[list[tuple[str, list[float]]]]:
    """PG ticker_embeddings 시도. 실패 또는 비어있으면 None."""
    try:
        from sqlalchemy import create_engine, text
        pg_url = os.getenv("EVENTS_PG_URL",
                          "postgresql://postgres:postgres@localhost:5432/wp_capstone")
        engine = create_engine(pg_url, future=True)
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT ticker, vector FROM ticker_embeddings")).all()
        return [(r[0], list(r[1])) for r in rows] if rows else None
    except Exception as e:
        log(f"[WARN] PG ticker_embeddings 조회 실패: {e}")
        return None


def _embeddings_from_checkpoint(checkpoint_path: Path) -> list[tuple[str, list[float]]]:
    """sanity 와 동일한 fallback — emb_v1.pt 에서 즉석 추출."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from extract_embeddings import extract_all, load_model_from_checkpoint  # type: ignore

    log(f"  [fallback] loading model from {checkpoint_path}")
    model, _, _ = load_model_from_checkpoint(checkpoint_path)
    rows = extract_all(model, DUCKDB_PATH, max_tickers=0)
    # extract_all 반환: list[(ticker, vector, date_start, date_end)]
    return [(t, list(v)) for (t, v, *_) in rows]


def attach_embeddings(df: pd.DataFrame, *,
                      checkpoint_path: Optional[Path] = None,
                      ) -> tuple[pd.DataFrame, list[str]]:
    """ticker → 64dim 임베딩 좌측 결합.
    PG ticker_embeddings 우선, 비어있거나 실패면 checkpoint 즉석 추출.
    매칭 안 된 ticker 는 0 벡터.
    """
    rows = _embeddings_from_pg()
    if not rows:
        if checkpoint_path is None:
            # 차차기 W3 — emb_v2 가 운영 default. 차차차기 ablation 재실행 시 변수.
            checkpoint_path = MODELS_ROOT / "emb_v2.pt"
        if not checkpoint_path.exists():
            raise FileNotFoundError(
                f"PG 비어있음 + checkpoint 없음: {checkpoint_path}. "
                "extract_embeddings.py 먼저 실행 또는 --emb-checkpoint 명시."
            )
        rows = _embeddings_from_checkpoint(checkpoint_path)

    if not rows:
        raise RuntimeError("임베딩 0개 — PG 도 checkpoint 도 빈 결과")

    D = len(rows[0][1])
    data: dict[str, list] = {"ticker": [r[0] for r in rows]}
    for i in range(D):
        data[f"emb_{i:02d}"] = [r[1][i] for r in rows]
    emb_df = pd.DataFrame(data)

    emb_cols = [c for c in emb_df.columns if c.startswith("emb_")]
    out = df.merge(emb_df, on="ticker", how="left")
    out[emb_cols] = out[emb_cols].fillna(0.0)
    n_matched = (out[emb_cols[0]] != 0.0).sum()
    log(f"  embeddings: {len(rows)} ticker, joined rows {n_matched:,}/{len(out):,}")
    return out, emb_cols


# ── 라벨 binning ───────────────────────────────────────────────────────────

def bin_relevance_per_group(df: pd.DataFrame, *, n_bins: int = N_RELEVANCE_BINS) -> np.ndarray:
    """
    LambdaRank 는 정수 relevance 필요. group(date) 내 라벨 백분위 → [0, n_bins) 정수.
    같은 그룹 내 상대 순위 → relevance — 절대값 의존 제거 (다양한 라벨에 일반적).
    """
    out = np.empty(len(df), dtype=np.int32)
    label_arr = df["label"].to_numpy()
    # `.indices` 는 positional integer ndarray — `.groups` (Index 라벨) 와 다름.
    for _, idx in df.groupby("date", sort=False).indices.items():
        sub = label_arr[idx]
        if len(sub) <= 1:
            out[idx] = 0
            continue
        ranks = pd.Series(sub).rank(method="average", pct=True).to_numpy()
        rel = np.clip((ranks * n_bins).astype(np.int32), 0, n_bins - 1)
        out[idx] = rel
    return out


# ── feature 선택 ───────────────────────────────────────────────────────────

def select_feature_cols(
    df: pd.DataFrame,
    extra_cols: Optional[list[str]] = None,
    allowlist:  Optional[list[str]] = None,
) -> list[str]:
    """allowlist 가 있으면 그 컬럼만 (df 안에 존재하는 것에 한해), 없으면 자동 선택."""
    extra = set(extra_cols or [])
    if allowlist is not None:
        present = [c for c in allowlist if c in df.columns]
        if extra:
            for c in (extra_cols or []):
                if c in df.columns and c not in present:
                    present.append(c)
        return present
    cols: list[str] = []
    for c in df.columns:
        if c in META_COLS or c == "label":
            continue
        if c in extra:
            cols.append(c)
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            cols.append(c)
    return cols


# ── 학습 ────────────────────────────────────────────────────────────────────

def train_lambdarank(
    df: pd.DataFrame,
    feature_cols: list[str],
    *,
    n_estimators: int = 500,
    learning_rate: float = 0.05,
    num_leaves:    int   = 63,
    early_stopping_rounds: int = 30,
    seed: int = 42,
):
    import lightgbm as lgb

    train = df[df["date"] <= TRAIN_END].copy()
    valid = df[(df["date"] >= VALID_START) & (df["date"] <= VALID_END)].copy()
    log(f"  train rows: {len(train):,}  valid rows: {len(valid):,}")

    train["relevance"] = bin_relevance_per_group(train)
    valid["relevance"] = bin_relevance_per_group(valid)

    train_groups = train.groupby("date", sort=True).size().to_numpy()
    valid_groups = valid.groupby("date", sort=True).size().to_numpy()

    X_train = train[feature_cols].astype(np.float32).fillna(0.0).to_numpy()
    y_train = train["relevance"].to_numpy()
    X_valid = valid[feature_cols].astype(np.float32).fillna(0.0).to_numpy()
    y_valid = valid["relevance"].to_numpy()

    dtrain = lgb.Dataset(X_train, label=y_train, group=train_groups,
                         feature_name=feature_cols)
    dvalid = lgb.Dataset(X_valid, label=y_valid, group=valid_groups,
                         feature_name=feature_cols, reference=dtrain)

    params = {
        "objective":      "lambdarank",
        "metric":         "ndcg",
        "ndcg_eval_at":   [5, 10, 20],
        "label_gain":     list(range(N_RELEVANCE_BINS)),
        "learning_rate":  learning_rate,
        "num_leaves":     num_leaves,
        "min_data_in_leaf": 100,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq":   5,
        "seed":           seed,
        "verbose":        -1,
    }

    log("  LightGBM lambdarank 학습 시작 …")
    booster = lgb.train(
        params,
        dtrain,
        num_boost_round=n_estimators,
        valid_sets=[dtrain, dvalid],
        valid_names=["train", "valid"],
        callbacks=[
            lgb.early_stopping(early_stopping_rounds, verbose=False),
            lgb.log_evaluation(period=20),
        ],
    )
    return booster, len(train), len(valid)


# ── 박제 ────────────────────────────────────────────────────────────────────

def archive_model(
    booster,
    *,
    variant: str,
    feature_cols: list[str],
    target_label: str,
    n_train: int,
    n_valid: int,
    use_embeddings: bool,
    force: bool = False,
    suffix: str = "",
) -> Path:
    out_dir = MODELS_ROOT / f"v11{variant}{suffix}"
    if out_dir.exists() and any(out_dir.iterdir()) and not force:
        raise FileExistsError(f"[REFUSED] 이미 박제: {out_dir}. --force 로 덮어쓰기.")
    out_dir.mkdir(parents=True, exist_ok=True)

    booster.save_model(str(out_dir / "model.txt"), num_iteration=booster.best_iteration)
    (out_dir / "feature_cols.json").write_text(
        json.dumps(feature_cols, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    best_iter = booster.best_iteration or booster.current_iteration()
    valid_ndcg10 = booster.best_score.get("valid", {}).get("ndcg@10")
    valid_ndcg5  = booster.best_score.get("valid", {}).get("ndcg@5")
    valid_ndcg20 = booster.best_score.get("valid", {}).get("ndcg@20")

    meta = {
        "model_version":       f"v11{variant}",
        "objective":           "lambdarank",
        "target_label":        target_label,
        "use_embeddings":      use_embeddings,
        "embedding_version":   "emb_v1" if use_embeddings else None,
        "n_features":          len(feature_cols),
        "n_train_rows":        int(n_train),
        "n_valid_rows":        int(n_valid),
        "train_end":           TRAIN_END,
        "valid_start":         VALID_START,
        "valid_end":           VALID_END,
        "n_relevance_bins":    N_RELEVANCE_BINS,
        "best_iteration":      int(best_iter),
        "valid_ndcg@5":        float(valid_ndcg5)  if valid_ndcg5  is not None else None,
        "valid_ndcg@10":       float(valid_ndcg10) if valid_ndcg10 is not None else None,
        "valid_ndcg@20":       float(valid_ndcg20) if valid_ndcg20 is not None else None,
        "built_at":            datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return out_dir


# ── 메인 ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="W5A — LambdaRank v11 학습")
    parser.add_argument("--variant",      default="a", choices=["a", "b", "c", "d"])
    parser.add_argument("--target-label", default="fwd_return_20d")
    parser.add_argument("--use-embeddings", action="store_true",
                        help="ticker_embeddings (PG) join. variant b·d 에서 자동 활성.")
    parser.add_argument("--emb-checkpoint", default=None,
                        help="PG 비어있을 때 fallback. emb_v1.pt 경로.")
    parser.add_argument("--feature-allowlist", default=None,
                        help="JSON 파일 경로. 명시한 컬럼만 사용 (W7A holdout 호환용).")
    parser.add_argument("--variant-suffix", default="",
                        help="모델 박제 디렉터리 접미사 (예: '_prime' → v11a_prime).")
    parser.add_argument("--max-rows",   type=int, default=0)
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--lr",         type=float, default=0.05)
    parser.add_argument("--seed",       type=int, default=42)
    parser.add_argument("--force",      action="store_true")
    parser.add_argument("--dry-run",    action="store_true",
                        help="학습 후 박제 생략 (빠른 검증).")
    args = parser.parse_args()

    use_embeddings = args.use_embeddings or args.variant in {"b", "d"}

    log("=== train_lambdarank_v11 (W5A) ===")
    log(f"  variant:        v11{args.variant}")
    log(f"  target_label:   {args.target_label}")
    log(f"  use_embeddings: {use_embeddings}")
    log(f"  features:       {FEATURES_PARQUET}")

    # 1. 로드 + join.
    log("  loading features parquet …")
    feat_df = load_features(args.max_rows)
    log(f"    shape: {feat_df.shape}")

    log("  loading labels (multi_labels) …")
    lbl_df = load_labels(args.target_label, feat_df["date"])
    log(f"    rows: {len(lbl_df):,}")

    log("  joining features × labels …")
    df = join_features_labels(feat_df, lbl_df)
    log(f"    joined rows: {len(df):,}")
    if df.empty:
        log("[ERROR] join 결과 0 행")
        return 2

    # 2. 임베딩 (variant b·d).
    extra_feat: list[str] = []
    if use_embeddings:
        log("  attaching embeddings …")
        ckpt = Path(args.emb_checkpoint) if args.emb_checkpoint else None
        df, extra_feat = attach_embeddings(df, checkpoint_path=ckpt)
        log(f"    embedding cols: {len(extra_feat)}")

    # 3. feature 선택.
    allowlist = None
    if args.feature_allowlist:
        with open(args.feature_allowlist, encoding="utf-8") as f:
            allowlist = json.load(f)
        log(f"  feature allowlist: {len(allowlist)} columns ({args.feature_allowlist})")
    feature_cols = select_feature_cols(df, extra_cols=extra_feat, allowlist=allowlist)
    log(f"  n_features: {len(feature_cols)}")

    # 4. 학습.
    booster, n_train, n_valid = train_lambdarank(
        df, feature_cols,
        n_estimators=args.n_estimators,
        learning_rate=args.lr,
        seed=args.seed,
    )

    # 5. 박제.
    if args.dry_run:
        log("--- dry-run (박제 생략) ---")
        log(f"  best_iteration: {booster.best_iteration}")
        log(f"  valid scores:   {booster.best_score.get('valid', {})}")
        return 0

    out_dir = archive_model(
        booster,
        variant=args.variant,
        feature_cols=feature_cols,
        target_label=args.target_label,
        n_train=n_train,
        n_valid=n_valid,
        use_embeddings=use_embeddings,
        force=args.force,
        suffix=args.variant_suffix,
    )
    log(f"  archived → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
