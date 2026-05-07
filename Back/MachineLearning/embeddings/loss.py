"""
embeddings/loss.py
==================
W3.5B — InfoNCE 손실 (NT-Xent, SimCLR 표준).

차기_사이클.md §W3.5: temperature 0.1, 같은 종목의 두 view 가깝게,
배치 내 다른 종목 view 멀게.

배치 구조:
  z1 : (B, D) view-A 의 z 표현
  z2 : (B, D) view-B 의 z 표현 (같은 ticker 의 두 번째 augmentation)
  → 2B 개를 concat 해서 NT-Xent 적용. 같은 ticker pair 만 positive.

본 구현은 *순수 함수 + 입력 검증*. 학습 루프는 W3.5C.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F


def nt_xent_loss(
    z1: torch.Tensor,
    z2: torch.Tensor,
    temperature: float = 0.1,
) -> torch.Tensor:
    """
    SimCLR NT-Xent (Normalized Temperature-scaled Cross-Entropy).

    Parameters
    ----------
    z1, z2 : (B, D) — 둘 다 *L2 정규화된* 표현 (ProjectionHead 가 normalize 함).
    temperature : 0 < τ ≤ 1, 작을수록 hard negative 강조 (기본 0.1).

    Returns
    -------
    scalar tensor — 평균 손실. 항상 ≥ 0.

    배치 크기 B 일 때:
      total = concat(z1, z2)  shape (2B, D)
      sim   = total @ total.T  shape (2B, 2B)  (이미 정규화돼 cosine = dot product)
      logits = sim / τ
      대각선 (자기 자신) 은 −inf 마스크
      각 row 의 *positive* index = (i + B) % (2B)
    """
    if z1.shape != z2.shape:
        raise ValueError(f"z1·z2 shape 불일치: {z1.shape} vs {z2.shape}")
    if z1.ndim != 2:
        raise ValueError(f"(B, D) 2D 텐서 필요 — got {z1.shape}")
    if temperature <= 0 or temperature > 1:
        raise ValueError(f"temperature 는 (0, 1] — got {temperature}")

    B, D = z1.shape
    if B < 2:
        # negative pair 가 없어 손실 정의 불가 — 0 반환 (학습 코드가 skip).
        return torch.zeros((), device=z1.device, dtype=z1.dtype)

    total = torch.cat([z1, z2], dim=0)            # (2B, D)
    sim = total @ total.t()                        # (2B, 2B), cosine
    logits = sim / temperature

    # 자기 자신 마스크 (대각선) — −inf 로 logit 만들어 softmax 에서 0.
    mask_self = torch.eye(2 * B, device=logits.device, dtype=torch.bool)
    logits = logits.masked_fill(mask_self, float("-inf"))

    # positive index: i 의 짝은 (i + B) mod 2B.
    targets = torch.arange(2 * B, device=logits.device)
    targets = (targets + B) % (2 * B)

    # CrossEntropyLoss: −log softmax(positive) of each row.
    loss = F.cross_entropy(logits, targets)
    return loss


def alignment_uniformity(
    z1: torch.Tensor,
    z2: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Wang & Isola (2020) — alignment + uniformity. 학습 진단용.

    alignment   = E[‖z1 − z2‖²]                낮을수록 같은 ticker view 가 가까움
    uniformity  = log E[exp(−2‖zi − zj‖²)]    낮을수록 표현이 hypersphere 에 균등
    """
    if z1.shape != z2.shape:
        raise ValueError("z1·z2 shape 불일치")
    align = (z1 - z2).pow(2).sum(dim=1).mean()

    z = torch.cat([z1, z2], dim=0)
    pdist = torch.pdist(z, p=2).pow(2)
    uniform = pdist.mul(-2.0).exp().mean().log()
    return align, uniform
