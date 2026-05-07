"""
embeddings/encoder.py
=====================
W3.5B — 1D-CNN 인코더 + projection head (PyTorch).

차기_사이클.md §W3.5 명세:
  - 인코더: 1D-CNN 3 layer + projection head 64 → 128 → 64
  - 입력: (batch, window=60, channels=2) → permute → (batch, 2, 60)
  - 출력 z: (batch, 64) L2 정규화 (InfoNCE 입력 표준)

설계:
  - Encoder: Conv1d(2→32→64→128) + GAP → 128차원 표현 (h)
  - ProjectionHead: 128 → 256 → 64 (MLP, ReLU + 마지막 L2 정규화)
  - SimCLR 표준 — h 가 다운스트림 (W3 MMR) 에 사용, z 는 학습 손실용.

본 모듈은 *순수 모듈* (학습 루프 없음). W3.5C 가 학습 진입점.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


# 명세 상수.
DEFAULT_INPUT_CHANNELS = 2          # log_return + log_volume_diff
DEFAULT_REPR_DIM       = 128        # h: backbone 출력
DEFAULT_PROJ_HIDDEN    = 256
DEFAULT_PROJ_OUT       = 64         # z: contrastive loss 입력


class Encoder1DCNN(nn.Module):
    """
    1D-CNN backbone — (B, C_in, T) → (B, repr_dim).

    구조 (3 layer):
      Conv1d(C_in→32, k=5, p=2) + BN + ReLU + MaxPool(2)
      Conv1d(32→64,   k=5, p=2) + BN + ReLU + MaxPool(2)
      Conv1d(64→repr_dim, k=3, p=1) + BN + ReLU
      AdaptiveAvgPool1d(1)
      Flatten → (B, repr_dim)
    """

    def __init__(
        self,
        in_channels: int = DEFAULT_INPUT_CHANNELS,
        repr_dim:    int = DEFAULT_REPR_DIM,
    ) -> None:
        super().__init__()
        self.in_channels = in_channels
        self.repr_dim    = repr_dim

        self.block1 = nn.Sequential(
            nn.Conv1d(in_channels, 32, kernel_size=5, padding=2),
            nn.BatchNorm1d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
        )
        self.block2 = nn.Sequential(
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
        )
        self.block3 = nn.Sequential(
            nn.Conv1d(64, repr_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(repr_dim),
            nn.ReLU(inplace=True),
        )
        self.gap = nn.AdaptiveAvgPool1d(1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, C_in, T)  또는  (B, T, C_in) — 후자는 자동 permute.
        반환: (B, repr_dim).
        """
        if x.ndim != 3:
            raise ValueError(f"입력은 3D — got shape {tuple(x.shape)}")
        if x.shape[1] != self.in_channels and x.shape[2] == self.in_channels:
            x = x.transpose(1, 2)
        h = self.block1(x)
        h = self.block2(h)
        h = self.block3(h)
        h = self.gap(h).squeeze(-1)        # (B, repr_dim)
        return h


class ProjectionHead(nn.Module):
    """
    SimCLR-style projection head: h(repr) → z(proj). 학습 시에만 사용.

    구조: Linear → BN → ReLU → Linear → L2 normalize.
    """

    def __init__(
        self,
        repr_dim: int = DEFAULT_REPR_DIM,
        hidden:   int = DEFAULT_PROJ_HIDDEN,
        out_dim:  int = DEFAULT_PROJ_OUT,
    ) -> None:
        super().__init__()
        self.fc1 = nn.Linear(repr_dim, hidden)
        self.bn  = nn.BatchNorm1d(hidden)
        self.fc2 = nn.Linear(hidden, out_dim)
        self.out_dim = out_dim

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        z = self.fc1(h)
        z = self.bn(z)
        z = F.relu(z, inplace=True)
        z = self.fc2(z)
        z = F.normalize(z, dim=-1)         # InfoNCE 표준
        return z


class ContrastiveModel(nn.Module):
    """
    Encoder + ProjectionHead 묶음.

    - 학습: forward(x) → z (B, proj_out)
    - 다운스트림: encode(x) → h (B, repr_dim)  ← W3 MMR 가 사용
    """

    def __init__(
        self,
        in_channels: int = DEFAULT_INPUT_CHANNELS,
        repr_dim:    int = DEFAULT_REPR_DIM,
        proj_hidden: int = DEFAULT_PROJ_HIDDEN,
        proj_out:    int = DEFAULT_PROJ_OUT,
    ) -> None:
        super().__init__()
        self.encoder = Encoder1DCNN(in_channels=in_channels, repr_dim=repr_dim)
        self.head    = ProjectionHead(repr_dim=repr_dim, hidden=proj_hidden, out_dim=proj_out)
        self.proj_out = proj_out
        self.repr_dim = repr_dim

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """다운스트림용 h (학습 후 임베딩 추출 시 사용)."""
        return self.encoder(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.encoder(x)
        z = self.head(h)
        return z
