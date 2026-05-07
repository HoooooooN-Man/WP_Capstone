"""
extract_embeddings.py
=====================
W3.5D 진입점 — 학습된 emb_v1.pt → DuckDB prices → ticker별 임베딩 → PG UPSERT.

흐름:
  1. checkpoint 로드 (encoder + head state_dict).
  2. ContrastiveModel 인스턴스 + state 복원 + eval().
  3. DuckDB prices → ticker별 시계열 → 윈도우 추출.
  4. 모델 inference → z 평균 → L2 정규화 → 64차원 벡터.
  5. PG ticker_embeddings 에 UPSERT (ON CONFLICT (ticker) DO UPDATE).

idempotent — 재실행 시 같은 결과 (모델·시계열 동일 시).

사용:
  py extract_embeddings.py                              # 전체 ticker
  py extract_embeddings.py --max-tickers 50             # 빠른 시연
  py extract_embeddings.py --checkpoint <path>          # 다른 체크포인트
  py extract_embeddings.py --dry-run                    # PG 적재 생략
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
DUCKDB_PATH   = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))
MODEL_DIR     = Path(os.getenv("EMB_MODEL_DIR", str(CAPSTONE_ROOT / "models")))

PG_URL = os.getenv(
    "EVENTS_PG_URL",
    "postgresql://postgres:postgres@localhost:5432/wp_capstone",
)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_model_from_checkpoint(checkpoint_path: Path):
    """체크포인트 → ContrastiveModel(eval). embedding_version 도 같이 반환."""
    import torch
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from embeddings.encoder import ContrastiveModel

    payload = torch.load(checkpoint_path, weights_only=False, map_location="cpu")
    version = payload.get("embedding_version", "emb_v1")
    config  = payload.get("config", {})

    model = ContrastiveModel()
    model.encoder.load_state_dict(payload["encoder_state_dict"])
    model.head.load_state_dict(payload["head_state_dict"])
    model.eval()
    return model, version, config


def extract_all(
    model,
    db_path: Path,
    *,
    window: int = 60,
    stride: int = 5,
    max_tickers: int = 0,
    min_window_count: int = 5,
):
    """ticker별 임베딩 추출 → list[(ticker, vector, date_start, date_end)]."""
    import duckdb
    import numpy as np

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from embeddings.data    import extract_windows, series_from_prices
    from embeddings.extract import compute_ticker_embedding

    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB 없음: {db_path}")

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        if max_tickers > 0:
            tickers = [r[0] for r in con.execute(
                "SELECT DISTINCT ticker FROM prices ORDER BY ticker LIMIT ?",
                [max_tickers],
            ).fetchall()]
        else:
            tickers = [r[0] for r in con.execute(
                "SELECT DISTINCT ticker FROM prices ORDER BY ticker"
            ).fetchall()]

        log(f"  Tickers: {len(tickers)}")

        results = []
        skipped = 0
        for t in tickers:
            df = con.execute(
                "SELECT date, close, volume FROM prices "
                "WHERE ticker = ? ORDER BY date",
                [t],
            ).fetchdf()
            if df.empty or len(df) < window + 2:
                skipped += 1
                continue
            series = series_from_prices(df["close"].values, df["volume"].values)
            wins = extract_windows(series, window=window, stride=stride)
            if wins.shape[0] < min_window_count:
                skipped += 1
                continue
            vec = compute_ticker_embedding(model, wins)
            if vec is None:
                skipped += 1
                continue
            d_start = _bigint_to_date(int(df["date"].iloc[0]))
            d_end   = _bigint_to_date(int(df["date"].iloc[-1]))
            results.append((t, vec.tolist(), d_start, d_end))

        log(f"  Extracted: {len(results):,}  skipped: {skipped}")
        return results
    finally:
        con.close()


def _bigint_to_date(v: int):
    """prices.date BIGINT YYYYMMDD → python date."""
    from datetime import date as _date
    s = str(int(v))
    if len(s) < 8:
        return None
    return _date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def upsert_to_pg(rows, embedding_version: str, *, dry_run: bool) -> int:
    """rows: [(ticker, vector(list[float]), date_start, date_end)]"""
    if not rows:
        return 0
    if dry_run:
        log(f"  [dry-run] would upsert {len(rows):,} rows (version={embedding_version})")
        for ticker, vec, ds, de in rows[:3]:
            log(f"    {ticker} dim={len(vec)} norm≈1 [{ds} ~ {de}]")
        return 0

    from sqlalchemy import create_engine, text
    engine = create_engine(PG_URL, future=True)

    sql = text("""
        INSERT INTO ticker_embeddings
            (ticker, embedding_version, vector, computed_at,
             data_window_start, data_window_end)
        VALUES
            (:ticker, :version, :vector, CURRENT_TIMESTAMP, :ds, :de)
        ON CONFLICT (ticker) DO UPDATE SET
            embedding_version  = EXCLUDED.embedding_version,
            vector             = EXCLUDED.vector,
            computed_at        = CURRENT_TIMESTAMP,
            data_window_start  = EXCLUDED.data_window_start,
            data_window_end    = EXCLUDED.data_window_end
    """)
    with engine.begin() as conn:
        for ticker, vec, ds, de in rows:
            conn.execute(sql, {
                "ticker":  ticker, "version": embedding_version,
                "vector":  vec, "ds": ds, "de": de,
            })
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="W3.5D — ticker_embeddings 추출·적재")
    parser.add_argument("--checkpoint", default=str(MODEL_DIR / "emb_v1.pt"))
    parser.add_argument("--max-tickers", type=int, default=0,
                        help="0 = 전체. 빠른 시연은 50.")
    parser.add_argument("--window",      type=int, default=60)
    parser.add_argument("--stride",      type=int, default=5)
    parser.add_argument("--dry-run",     action="store_true")
    args = parser.parse_args()

    log("=== extract_embeddings ===")
    log(f"  checkpoint: {args.checkpoint}")
    log(f"  DuckDB:     {DUCKDB_PATH}")
    log(f"  PG:         {PG_URL}")

    ckpt_path = Path(args.checkpoint)
    if not ckpt_path.exists():
        log(f"[ERROR] 체크포인트 없음: {ckpt_path}. train_embeddings.py 먼저 실행.")
        return 1

    model, version, config = load_model_from_checkpoint(ckpt_path)
    log(f"  loaded — version={version} repr_dim={model.repr_dim} proj_out={model.proj_out}")

    try:
        rows = extract_all(
            model, DUCKDB_PATH,
            window=args.window,
            stride=args.stride,
            max_tickers=args.max_tickers,
        )
    except FileNotFoundError as e:
        log(f"[ERROR] {e}")
        return 1
    if not rows:
        log("[ERROR] 추출 결과 없음 (윈도우 부족·미스매치).")
        return 2

    if not args.dry_run:
        # PG 연결 확인.
        try:
            from sqlalchemy import create_engine
            with create_engine(PG_URL, future=True).connect():
                pass
        except Exception as e:
            log(f"[ERROR] PostgreSQL 연결 실패 ({PG_URL}): {e}")
            return 3

    n = upsert_to_pg(rows, version, dry_run=args.dry_run)
    log(f"Done. upserted={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
