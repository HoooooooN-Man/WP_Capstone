"""
train_embeddings.py
===================
W3.5C — 종목 임베딩 학습 진입점.

데이터 → DuckDB prices → ticker 별 (close, volume) 시계열 → (T, 2) log-diff
       → window=60 stride=5 추출 → in-memory list[WindowEntry]
학습 → ContrastiveModel + nt_xent_loss + Adam(lr=1e-3) + epoch 루프
체크포인트 → models/emb_v1.pt (encoder state_dict + meta)

기본은 *적은 epoch + 적은 ticker 샘플* 로 빠르게 sanity 통과 검증.
실전 학습은 `--epochs 100 --max-tickers 0` 등으로 명시적 호출.

CPU 학습 기준 시간 안내:
  - 50 ticker × 10 epoch ≈ 1 분
  - 200 ticker × 50 epoch ≈ 30 분
  - 전 ticker × 100 epoch ≈ 수 시간

Sanity check 는 W3.5E 에서 별도 스크립트가 수행. 본 진입점은 학습만.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np


CAPSTONE_ROOT = Path(os.getenv("CAPSTONE_ROOT", r"E:\Capstone Data\project_data"))
DUCKDB_PATH   = Path(os.getenv("DUCKDB_PATH", str(CAPSTONE_ROOT / "db" / "market_data.duckdb")))
MODEL_DIR     = Path(os.getenv("EMB_MODEL_DIR", str(CAPSTONE_ROOT / "models")))


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── 데이터 로딩 ─────────────────────────────────────────────────────────────

def load_ticker_windows(
    db_path: Path,
    *,
    window: int = 60,
    stride: int = 5,
    max_tickers: int = 0,        # 0 = 전체
    min_window_count: int = 5,   # ticker 가 이만큼 윈도우 못 만들면 skip
):
    """
    DuckDB prices → list[WindowEntry]. ticker 별로:
      1. (close, volume) 시계열 정렬 로드
      2. series_from_prices → (T, 2) log-diff
      3. extract_windows → (N, 60, 2)
      4. 각 행을 WindowEntry 로 push.

    PyTorch 의존이라 lazy import.
    """
    import duckdb
    from embeddings.data import series_from_prices, extract_windows
    from embeddings.dataset import WindowEntry

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

        entries = []
        skipped = 0
        for t in tickers:
            df = con.execute(
                "SELECT close, volume FROM prices WHERE ticker = ? ORDER BY date",
                [t],
            ).fetchdf()
            if df.empty or len(df) < window + 2:
                skipped += 1
                continue
            close  = df["close"].values
            volume = df["volume"].values
            series = series_from_prices(close, volume)
            wins = extract_windows(series, window=window, stride=stride)
            if wins.shape[0] < min_window_count:
                skipped += 1
                continue
            for w in wins:
                entries.append(WindowEntry(ticker=t, window=w))

        log(f"  Total windows: {len(entries):,} (skipped tickers: {skipped})")
        return entries
    finally:
        con.close()


# ── 학습 루프 ──────────────────────────────────────────────────────────────

def train(
    entries,
    *,
    epochs: int = 10,
    batch_size: int = 256,
    lr: float = 1e-3,
    temperature: float = 0.1,
    seed: int = 42,
    log_interval: int = 50,
):
    import torch
    from torch.utils.data import DataLoader

    from embeddings.dataset import TickerWindowDataset, make_collate_fn
    from embeddings.encoder import ContrastiveModel
    from embeddings.loss    import alignment_uniformity, nt_xent_loss

    torch.manual_seed(seed)
    np.random.seed(seed)

    ds = TickerWindowDataset(entries)
    collate = make_collate_fn(seed=seed)
    loader = DataLoader(
        ds, batch_size=batch_size, shuffle=True,
        collate_fn=collate, num_workers=0, drop_last=True,
    )
    log(f"  Dataset: {len(ds):,} windows / batches per epoch: {len(loader)}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ContrastiveModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for step, (a, b, _tickers) in enumerate(loader, 1):
            a = a.to(device).permute(0, 2, 1)   # (B, T, C) → (B, C, T)
            b = b.to(device).permute(0, 2, 1)

            z1 = model(a)
            z2 = model(b)
            loss = nt_xent_loss(z1, z2, temperature=temperature)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            epoch_loss += float(loss.item())
            n_batches += 1
            if step % log_interval == 0:
                log(f"    epoch {epoch} step {step}/{len(loader)} loss={loss.item():.4f}")

        avg = epoch_loss / max(n_batches, 1)
        # 마지막 배치 진단.
        with torch.no_grad():
            align, unif = alignment_uniformity(z1, z2)
        log(f"  epoch {epoch:>3}: loss={avg:.4f} align={align.item():.4f} unif={unif.item():.4f}")
        history.append({
            "epoch": epoch,
            "loss":  round(avg, 4),
            "align": round(float(align.item()), 4),
            "unif":  round(float(unif.item()), 4),
        })

    return model, history


# ── 체크포인트 ─────────────────────────────────────────────────────────────

def save_checkpoint(
    model,
    history,
    *,
    out_path: Path,
    embedding_version: str = "emb_v1",
    config: Optional[dict] = None,
) -> None:
    import torch
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "embedding_version": embedding_version,
        "saved_at":  datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "encoder_state_dict": model.encoder.state_dict(),
        "head_state_dict":    model.head.state_dict(),
        "config": config or {},
        "history": history,
    }
    torch.save(payload, out_path)
    log(f"  Saved checkpoint: {out_path}")


# ── 메인 ───────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="W3.5C — 임베딩 학습")
    parser.add_argument("--epochs",      type=int, default=10)
    parser.add_argument("--batch-size",  type=int, default=256)
    parser.add_argument("--lr",          type=float, default=1e-3)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-tickers", type=int, default=50,
                        help="0 = 전체. 빠른 sanity 학습은 50 권장.")
    parser.add_argument("--window",      type=int, default=60)
    parser.add_argument("--stride",      type=int, default=5)
    parser.add_argument("--seed",        type=int, default=42)
    parser.add_argument("--out",         default=str(MODEL_DIR / "emb_v1.pt"))
    parser.add_argument("--version",     default="emb_v1")
    args = parser.parse_args()

    log("=== train_embeddings ===")
    log(f"  DB:           {DUCKDB_PATH}")
    log(f"  out:          {args.out}")
    log(f"  epochs={args.epochs} batch={args.batch_size} lr={args.lr} τ={args.temperature}")
    log(f"  max_tickers={args.max_tickers} window={args.window} stride={args.stride}")

    try:
        entries = load_ticker_windows(
            DUCKDB_PATH,
            window=args.window,
            stride=args.stride,
            max_tickers=args.max_tickers,
        )
    except FileNotFoundError as e:
        log(f"[ERROR] {e}")
        return 1
    if len(entries) < args.batch_size:
        log(f"[ERROR] 윈도우 수 {len(entries)} < batch {args.batch_size}. "
            "max_tickers 늘리거나 batch_size 줄이세요.")
        return 2

    model, history = train(
        entries,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        temperature=args.temperature,
        seed=args.seed,
    )
    save_checkpoint(
        model, history,
        out_path=Path(args.out),
        embedding_version=args.version,
        config={
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "temperature": args.temperature,
            "max_tickers": args.max_tickers,
            "window": args.window,
            "stride": args.stride,
            "seed": args.seed,
        },
    )
    log("Done.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
