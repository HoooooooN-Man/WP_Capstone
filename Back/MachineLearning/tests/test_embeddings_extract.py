"""
test_embeddings_extract.py
==========================
W3.5D — 임베딩 추출 순수 함수 + checkpoint round-trip 단위 테스트.

PyTorch 미설치 환경에서는 skip. PG 의존 통합은 별도 환경에서.
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

from embeddings.encoder import ContrastiveModel
from embeddings.extract import compute_ticker_embedding, cosine_distance_matrix


def test_compute_ticker_embedding_shape_and_norm():
    torch.manual_seed(0)
    model = ContrastiveModel().eval()
    windows = np.random.RandomState(0).randn(7, 60, 2).astype(np.float32)
    v = compute_ticker_embedding(model, windows)
    assert v.shape == (model.proj_out,)   # 64
    assert v.dtype == np.float32
    # L2 정규화.
    assert abs(float(np.linalg.norm(v)) - 1.0) < 1e-5


def test_compute_ticker_embedding_handles_single_window():
    """N=1 도 정상 동작."""
    torch.manual_seed(1)
    model = ContrastiveModel().eval()
    windows = np.random.RandomState(1).randn(1, 60, 2).astype(np.float32)
    v = compute_ticker_embedding(model, windows)
    assert v.shape == (model.proj_out,)


def test_compute_ticker_embedding_returns_none_for_empty():
    model = ContrastiveModel().eval()
    assert compute_ticker_embedding(model, np.zeros((0, 60, 2), dtype=np.float32)) is None
    assert compute_ticker_embedding(model, None) is None


def test_compute_ticker_embedding_validates_shape():
    model = ContrastiveModel().eval()
    with pytest.raises(ValueError):
        compute_ticker_embedding(model, np.zeros((60, 2), dtype=np.float32))


def test_compute_ticker_embedding_deterministic_in_eval():
    """eval 모드 + 같은 입력 → 같은 출력. BatchNorm running stats 가 frozen."""
    model = ContrastiveModel().eval()
    windows = np.random.RandomState(0).randn(5, 60, 2).astype(np.float32)
    v1 = compute_ticker_embedding(model, windows)
    v2 = compute_ticker_embedding(model, windows)
    assert np.allclose(v1, v2, atol=1e-6)


def test_compute_ticker_embedding_batch_size_invariant():
    """batch_size 변경에도 결과 동일 (수치 오차 내)."""
    model = ContrastiveModel().eval()
    windows = np.random.RandomState(2).randn(10, 60, 2).astype(np.float32)
    v_full = compute_ticker_embedding(model, windows, batch_size=10)
    v_chunk = compute_ticker_embedding(model, windows, batch_size=3)
    # mean → normalize 라 chunk 분할 결과가 정확히 같음 (sum 동일).
    assert np.allclose(v_full, v_chunk, atol=1e-5)


# ── cosine_distance_matrix ──────────────────────────────────────────────

def test_cosine_distance_diagonal_zero():
    rng = np.random.default_rng(3)
    v = rng.normal(size=(5, 8)).astype(np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    D = cosine_distance_matrix(v)
    assert D.shape == (5, 5)
    assert np.allclose(np.diag(D), 0.0, atol=1e-5)


def test_cosine_distance_symmetric():
    rng = np.random.default_rng(4)
    v = rng.normal(size=(6, 8)).astype(np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    D = cosine_distance_matrix(v)
    assert np.allclose(D, D.T, atol=1e-6)


def test_cosine_distance_validates_2d():
    with pytest.raises(ValueError):
        cosine_distance_matrix(np.zeros(8))


# ── checkpoint round-trip + extract ─────────────────────────────────────

def test_load_model_from_checkpoint_round_trip(tmp_path):
    """train → save → extract_embeddings.load 로 모델 복원 + 동일 inference."""
    from train_embeddings import save_checkpoint, train
    from extract_embeddings import load_model_from_checkpoint

    # 작은 학습 1 epoch.
    from embeddings.dataset import WindowEntry
    rng = np.random.default_rng(5)
    entries = [
        WindowEntry(ticker=f"00{i:04d}",
                    window=rng.normal(0, 0.01, (60, 2)).astype(np.float32))
        for i in range(16)
    ]
    model_orig, history = train(entries, epochs=1, batch_size=8, seed=5, log_interval=1000)
    out = tmp_path / "emb_test.pt"
    save_checkpoint(model_orig, history, out_path=out,
                    embedding_version="emb_v1_test", config={"smoke": True})

    # 복원.
    model_loaded, version, config = load_model_from_checkpoint(out)
    assert version == "emb_v1_test"
    assert config["smoke"] is True

    # 같은 입력에 같은 임베딩.
    w = np.random.RandomState(6).randn(3, 60, 2).astype(np.float32)
    v_orig   = compute_ticker_embedding(model_orig.eval(),   w)
    v_loaded = compute_ticker_embedding(model_loaded,        w)
    assert np.allclose(v_orig, v_loaded, atol=1e-5)


# ── ORM 클래스 import ───────────────────────────────────────────────────

def test_ticker_embedding_orm_importable():
    """SQLAlchemy 모델이 import 되고 핵심 속성이 정의됐는지."""
    db_root = Path(__file__).resolve().parents[3] / "Back" / "db"
    if str(db_root) not in sys.path:
        sys.path.insert(0, str(db_root))
    try:
        from db.models import TickerEmbedding
    except (ModuleNotFoundError, ImportError) as e:
        pytest.skip(f"PG ORM dep missing: {e}")
    assert TickerEmbedding.__tablename__ == "ticker_embeddings"
    cols = {c.name for c in TickerEmbedding.__table__.columns}
    assert {"ticker", "embedding_version", "vector",
            "computed_at", "data_window_start", "data_window_end"} <= cols
    pk = [c.name for c in TickerEmbedding.__table__.primary_key.columns]
    assert pk == ["ticker"]
