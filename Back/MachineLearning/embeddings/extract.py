"""
embeddings/extract.py
=====================
W3.5D — 학습된 인코더 → ticker 별 representative 임베딩 추출.

순수 함수 (PyTorch 의존):
  - compute_ticker_embedding(model, windows) → (D,) numpy float32, L2 정규화.
    한 ticker 의 모든 윈도우를 모델에 통과시킨 z 의 평균 → 다시 normalize.

I/O 진입점은 train_embeddings 와 별도 (extract_embeddings.py).
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


def compute_ticker_embedding(model, windows: np.ndarray, *, batch_size: int = 64):
    """
    한 ticker 의 윈도우들을 모델에 통과 → z 평균 → L2 정규화.

    Parameters
    ----------
    model : ContrastiveModel (eval 모드 권장).
    windows : (N, T, C) numpy float32. extract_windows 결과.
    batch_size : 메모리 보호용 미니배치.

    Returns
    -------
    (D,) numpy float32, ‖v‖₂ = 1. 윈도우 0개면 None.
    """
    import torch

    if windows is None or len(windows) == 0:
        return None
    if not isinstance(windows, np.ndarray):
        windows = np.asarray(windows, dtype=np.float32)
    if windows.ndim != 3:
        raise ValueError(f"windows 는 (N, T, C) 3D — got {windows.shape}")

    model.eval()
    with torch.no_grad():
        accum = None
        n_total = 0
        for i in range(0, len(windows), batch_size):
            chunk = windows[i : i + batch_size]                                  # (B, T, C)
            x = torch.from_numpy(chunk).permute(0, 2, 1).contiguous().float()    # (B, C, T)
            z = model(x)                                                          # (B, D), L2 norm.
            z_np = z.cpu().numpy()
            if accum is None:
                accum = z_np.sum(axis=0)
            else:
                accum += z_np.sum(axis=0)
            n_total += z_np.shape[0]

    if n_total == 0:
        return None
    mean = accum / n_total

    # 평균은 unit norm 이 아닐 수 있어 다시 L2 정규화 (cosine 거리 표준).
    nrm = float(np.linalg.norm(mean))
    if nrm <= 1e-12:
        return mean.astype(np.float32)
    return (mean / nrm).astype(np.float32)


def cosine_distance_matrix(vectors: np.ndarray) -> np.ndarray:
    """
    (N, D) 정규화된 벡터 → (N, N) 코사인 거리. d = 1 − cosine_sim.
    Sanity check (W3.5E) 가 사용. 본 모듈에 같이 두어 의존 단순화.
    """
    v = np.asarray(vectors, dtype=np.float32)
    if v.ndim != 2:
        raise ValueError("(N, D) 2D 필요")
    sim = v @ v.T
    np.clip(sim, -1.0, 1.0, out=sim)
    return 1.0 - sim
