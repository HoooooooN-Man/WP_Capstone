"""
embeddings/dataset.py
=====================
W3.5C — 시계열 윈도우 PyTorch Dataset + two-view collate.

Dataset 단위 = (ticker, window) 한 쌍. collate_fn 이 배치마다 augment_series 를
*두 번* 호출해 (B, T, C) view-A·view-B 를 동시 반환 — InfoNCE 학습 입력.

차기_사이클.md §W3.5: 배치 256, negative samples 511 (= 2B − 2 자기·짝 제외).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import torch
from torch.utils.data import Dataset

from .data import AugmentParams, augment_series


@dataclass
class WindowEntry:
    ticker: str
    window: np.ndarray   # (T, C) float32


class TickerWindowDataset(Dataset):
    """
    in-memory list[WindowEntry] 기반 Dataset.

    각 __getitem__ 은 *원본* 윈도우만 반환. collate 가 augmentation 을 적용.
    """

    def __init__(self, entries: list[WindowEntry]) -> None:
        if len(entries) == 0:
            raise ValueError("entries 가 비어있습니다.")
        self._entries = entries

    def __len__(self) -> int:
        return len(self._entries)

    def __getitem__(self, idx: int) -> WindowEntry:
        return self._entries[idx]


def two_view_collate(
    batch: list[WindowEntry],
    params: Optional[AugmentParams] = None,
    rng: Optional[np.random.Generator] = None,
) -> tuple[torch.Tensor, torch.Tensor, list[str]]:
    """
    배치를 받아 (view_a, view_b, tickers) 를 반환.

    view_a, view_b : (B, T, C) float32 — InfoNCE 입력. 같은 idx 의 두 view 는
    *같은 ticker·같은 시작 위치* 의 두 augmentation.
    """
    params = params or AugmentParams()
    rng    = rng    or np.random.default_rng()

    a_list, b_list, tickers = [], [], []
    for e in batch:
        a_list.append(augment_series(e.window, params, rng=rng))
        b_list.append(augment_series(e.window, params, rng=rng))
        tickers.append(e.ticker)

    a = torch.from_numpy(np.stack(a_list, axis=0))   # (B, T, C)
    b = torch.from_numpy(np.stack(b_list, axis=0))
    return a, b, tickers


def make_collate_fn(
    params: Optional[AugmentParams] = None,
    seed: Optional[int] = None,
):
    """DataLoader 에 전달할 collate_fn factory. seed 지정 시 결정성 보장."""
    rng = np.random.default_rng(seed)
    p = params or AugmentParams()
    def _fn(batch: list[WindowEntry]):
        return two_view_collate(batch, p, rng)
    return _fn
