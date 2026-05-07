"""
test_embeddings_train.py
========================
W3.5C — Dataset · collate · train smoke 단위 테스트.

PyTorch 미설치 환경에서는 자동 skip.
DuckDB 의존 없이 *랜덤 시계열* 로 학습 루프 1~2 epoch 동작 보장.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))


torch = pytest.importorskip("torch")

from embeddings.data    import AugmentParams
from embeddings.dataset import (
    TickerWindowDataset,
    WindowEntry,
    make_collate_fn,
    two_view_collate,
)


def _make_random_entries(n_tickers: int = 8, n_per: int = 4, T: int = 60, C: int = 2):
    rng = np.random.default_rng(0)
    out = []
    for ti in range(n_tickers):
        ticker = f"00{ti:04d}"
        for _ in range(n_per):
            w = rng.normal(0, 0.01, size=(T, C)).astype(np.float32)
            out.append(WindowEntry(ticker=ticker, window=w))
    return out


# ── Dataset ─────────────────────────────────────────────────────────────

def test_dataset_len_and_getitem():
    entries = _make_random_entries(4, 3)
    ds = TickerWindowDataset(entries)
    assert len(ds) == 12
    assert isinstance(ds[0], WindowEntry)


def test_dataset_rejects_empty():
    with pytest.raises(ValueError):
        TickerWindowDataset([])


# ── two_view_collate ────────────────────────────────────────────────────

def test_two_view_collate_shapes():
    entries = _make_random_entries(3, 2, T=60, C=2)
    a, b, tickers = two_view_collate(entries, AugmentParams())
    assert a.shape == (6, 60, 2)
    assert b.shape == (6, 60, 2)
    assert len(tickers) == 6
    assert a.dtype == torch.float32


def test_two_view_collate_views_differ():
    entries = _make_random_entries(2, 2)
    a, b, _ = two_view_collate(entries)
    # 같은 입력에서 두 view 가 *서로 다름*.
    assert not torch.equal(a, b)


def test_collate_fn_is_seedable():
    entries = _make_random_entries(2, 2)
    fn1 = make_collate_fn(seed=123)
    fn2 = make_collate_fn(seed=123)
    a1, b1, _ = fn1(entries)
    a2, b2, _ = fn2(entries)
    assert torch.equal(a1, a2)
    assert torch.equal(b1, b2)


# ── 학습 루프 smoke ──────────────────────────────────────────────────────

def test_train_one_epoch_random_data_runs():
    """train() 가 랜덤 데이터로 1 epoch 정상 종료 + loss 가 finite."""
    from train_embeddings import train

    # 배치 16 × 2 = 32 windows 면 충분.
    entries = _make_random_entries(n_tickers=8, n_per=4)   # 32 windows
    model, history = train(
        entries,
        epochs=1,
        batch_size=8,
        lr=1e-3,
        temperature=0.1,
        seed=0,
        log_interval=1000,   # smoke 에서 stdout 줄임
    )
    assert len(history) == 1
    assert torch.is_tensor(next(model.parameters()))
    # 첫 epoch loss 가 finite 양수.
    h0 = history[0]
    assert h0["loss"] > 0
    assert np.isfinite(h0["loss"])
    assert np.isfinite(h0["align"])
    assert np.isfinite(h0["unif"])


def test_train_two_epoch_loss_finite():
    """2 epoch 가 모두 finite — 학습이 발산하지 않음."""
    from train_embeddings import train

    entries = _make_random_entries(n_tickers=8, n_per=8)   # 64 windows
    _, history = train(entries, epochs=2, batch_size=16, lr=1e-3, seed=1, log_interval=1000)
    assert len(history) == 2
    assert all(np.isfinite(h["loss"]) for h in history)


# ── checkpoint round-trip ───────────────────────────────────────────────

def test_save_and_load_checkpoint(tmp_path):
    from train_embeddings import save_checkpoint, train
    from embeddings.encoder import ContrastiveModel

    entries = _make_random_entries(4, 4)
    model, history = train(entries, epochs=1, batch_size=8, seed=2, log_interval=1000)

    out_path = tmp_path / "emb_v1.pt"
    save_checkpoint(model, history, out_path=out_path,
                    embedding_version="emb_v1_test",
                    config={"smoke": True})
    assert out_path.exists()

    loaded = torch.load(out_path, weights_only=False)
    assert loaded["embedding_version"] == "emb_v1_test"
    assert "encoder_state_dict" in loaded
    assert "head_state_dict"    in loaded
    assert loaded["config"]["smoke"] is True

    # 새 모델 인스턴스에 가중치 복원 가능 — shape compatibility 확인.
    fresh = ContrastiveModel()
    fresh.encoder.load_state_dict(loaded["encoder_state_dict"])
    fresh.head.load_state_dict(loaded["head_state_dict"])
