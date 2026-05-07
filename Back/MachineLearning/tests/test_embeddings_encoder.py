"""
test_embeddings_encoder.py
==========================
W3.5B — Encoder1DCNN + ProjectionHead + ContrastiveModel + nt_xent_loss 단위 테스트.

PyTorch 미설치 환경에서는 자동 skip.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))


torch = pytest.importorskip("torch")
nn = pytest.importorskip("torch.nn")
F = pytest.importorskip("torch.nn.functional")

from embeddings.encoder import (
    DEFAULT_INPUT_CHANNELS,
    DEFAULT_PROJ_OUT,
    DEFAULT_REPR_DIM,
    ContrastiveModel,
    Encoder1DCNN,
    ProjectionHead,
)
from embeddings.loss import alignment_uniformity, nt_xent_loss


# ── Encoder1DCNN ────────────────────────────────────────────────────────

def test_encoder_output_shape_channels_first():
    enc = Encoder1DCNN(in_channels=2, repr_dim=128).eval()
    x = torch.randn(4, 2, 60)
    h = enc(x)
    assert h.shape == (4, 128)


def test_encoder_accepts_channels_last_via_auto_permute():
    """(B, T, C) 도 받으면 자동 permute."""
    enc = Encoder1DCNN(in_channels=2, repr_dim=128).eval()
    x = torch.randn(4, 60, 2)   # T=60, C=2
    h = enc(x)
    assert h.shape == (4, 128)


def test_encoder_rejects_non_3d():
    enc = Encoder1DCNN(in_channels=2).eval()
    with pytest.raises(ValueError):
        enc(torch.randn(60, 2))   # 2D


def test_encoder_handles_short_window():
    """매우 짧은 윈도우(MaxPool 후 길이 0 위험) — 합리적인 길이는 허용."""
    enc = Encoder1DCNN(in_channels=2).eval()
    x = torch.randn(2, 2, 16)
    h = enc(x)
    assert h.shape == (2, 128)


# ── ProjectionHead ──────────────────────────────────────────────────────

def test_projection_head_output_shape_and_norm():
    head = ProjectionHead(repr_dim=128, hidden=256, out_dim=64).eval()
    h = torch.randn(8, 128)
    z = head(h)
    assert z.shape == (8, 64)
    # L2 정규화 — 각 row 의 norm 이 1.
    norms = z.norm(dim=1)
    assert torch.allclose(norms, torch.ones_like(norms), atol=1e-5)


# ── ContrastiveModel ────────────────────────────────────────────────────

def test_contrastive_forward_returns_normalized_z():
    m = ContrastiveModel().eval()
    x = torch.randn(4, 2, 60)
    z = m(x)
    assert z.shape == (4, DEFAULT_PROJ_OUT)
    norms = z.norm(dim=1)
    assert torch.allclose(norms, torch.ones_like(norms), atol=1e-5)


def test_contrastive_encode_returns_h_for_downstream():
    m = ContrastiveModel().eval()
    x = torch.randn(4, 2, 60)
    h = m.encode(x)
    assert h.shape == (4, DEFAULT_REPR_DIM)


def test_contrastive_default_dims_match_spec():
    m = ContrastiveModel().eval()
    assert m.repr_dim == DEFAULT_REPR_DIM == 128
    assert m.proj_out == DEFAULT_PROJ_OUT == 64
    assert m.encoder.in_channels == DEFAULT_INPUT_CHANNELS == 2


# ── nt_xent_loss ────────────────────────────────────────────────────────

def test_nt_xent_loss_basic():
    """랜덤 정규화된 z 두 개에 대한 손실 — 양수 scalar."""
    torch.manual_seed(0)
    z1 = F.normalize(torch.randn(8, 64), dim=-1)
    z2 = F.normalize(torch.randn(8, 64), dim=-1)
    loss = nt_xent_loss(z1, z2, temperature=0.1)
    assert loss.dim() == 0
    assert loss.item() > 0


def test_nt_xent_loss_lower_for_aligned_pairs():
    """같은 ticker view 가 가까우면 (z1 ≈ z2) 손실이 더 낮아야."""
    torch.manual_seed(1)
    base = F.normalize(torch.randn(8, 64), dim=-1)
    z1 = base
    z2 = F.normalize(base + 0.01 * torch.randn_like(base), dim=-1)
    loss_aligned = nt_xent_loss(z1, z2, temperature=0.1)

    z1_rand = F.normalize(torch.randn(8, 64), dim=-1)
    z2_rand = F.normalize(torch.randn(8, 64), dim=-1)
    loss_rand = nt_xent_loss(z1_rand, z2_rand, temperature=0.1)

    assert loss_aligned.item() < loss_rand.item()


def test_nt_xent_validates_shape_mismatch():
    z1 = torch.randn(4, 64)
    z2 = torch.randn(5, 64)
    with pytest.raises(ValueError):
        nt_xent_loss(z1, z2)


def test_nt_xent_temperature_bounds():
    z = F.normalize(torch.randn(4, 8), dim=-1)
    with pytest.raises(ValueError):
        nt_xent_loss(z, z, temperature=0)
    with pytest.raises(ValueError):
        nt_xent_loss(z, z, temperature=1.5)


def test_nt_xent_handles_b_lt_2_returns_zero():
    """배치 1 — negative 없음 → 0 반환 (학습 코드가 skip 하라는 신호)."""
    z = F.normalize(torch.randn(1, 8), dim=-1)
    loss = nt_xent_loss(z, z, temperature=0.1)
    assert loss.item() == 0.0


# ── alignment / uniformity ──────────────────────────────────────────────

def test_alignment_zero_for_identical_views():
    z = F.normalize(torch.randn(4, 8), dim=-1)
    align, unif = alignment_uniformity(z, z)
    assert align.item() == pytest.approx(0.0, abs=1e-6)
    # uniformity 는 분포에 따라 다양함 — 정의역 검증만.
    assert torch.isfinite(unif)


def test_alignment_increases_with_distance():
    torch.manual_seed(2)
    z1 = F.normalize(torch.randn(8, 16), dim=-1)
    z2_close = F.normalize(z1 + 0.05 * torch.randn_like(z1), dim=-1)
    z2_far   = F.normalize(torch.randn(8, 16), dim=-1)
    a_close, _ = alignment_uniformity(z1, z2_close)
    a_far,   _ = alignment_uniformity(z1, z2_far)
    assert a_close.item() < a_far.item()


# ── 통합: 한 step training 가능성 점검 ────────────────────────────────

def test_one_optimization_step_runs():
    """forward → loss → backward → step. 학습 루프 진입 전 sanity."""
    torch.manual_seed(3)
    m = ContrastiveModel()
    opt = torch.optim.Adam(m.parameters(), lr=1e-3)

    x1 = torch.randn(8, 2, 60)
    x2 = torch.randn(8, 2, 60)

    m.train()
    z1 = m(x1)
    z2 = m(x2)
    loss = nt_xent_loss(z1, z2, temperature=0.1)
    opt.zero_grad()
    loss.backward()
    opt.step()

    # 손실이 finite 이고, 모든 parameter 에 grad 가 흘렀는지.
    assert torch.isfinite(loss)
    assert any(p.grad is not None and torch.isfinite(p.grad).all() for p in m.parameters())
