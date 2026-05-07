"""
embeddings/data.py
==================
W3.5A — 시계열 입력 + augmentation 순수 함수 (numpy 만, PyTorch 의존 없음).

설계:
  - 한 ticker 의 가격·거래량 → (T, 2) ndarray:
      채널 0 : log return    = log(close[t] / close[t-1])
      채널 1 : volume change = log(volume[t] / volume[t-1])
  - 윈도우: 60거래일. 시작 위치를 stride 만큼 이동시키며 다수 윈도우 추출.
  - Augmentation 3종 (08·차기_사이클.md §W3.5):
      mask_random(pct)       : 10~30% 위치를 0 으로 마스크
      add_gaussian_noise(σ)  : 채널별 정규분포 σ=0.01
      time_jitter(max_shift) : ±2일 시간축 shift (zero-pad)

  - augment_series(series, params, rng) : 위 3 종을 모두 적용해 view 한 개 생성.
    SimCLR 스타일 — 같은 서브시계열에 *두 번* 호출하면 두 view 가 됨.

본 모듈은 *순수 함수* — 단위 테스트 가능. DuckDB·PG·PyTorch 의존 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


# ── 시계열 변환 ──────────────────────────────────────────────────────────────

def series_from_prices(
    close: np.ndarray,
    volume: np.ndarray,
    *,
    eps: float = 1e-6,
) -> np.ndarray:
    """
    (T+1,) close·volume 배열 → (T, 2) log-diff 시계열.

    채널 0: log return       — close[t]/close[t-1] 의 로그.
    채널 1: log volume diff  — volume[t]/volume[t-1] 의 로그. 0 거래일은 eps 로 보정.

    NaN/Inf 는 0 으로 정규화. 시계열 길이가 < 2 면 빈 (0, 2) 반환.
    """
    close  = np.asarray(close,  dtype=float).flatten()
    volume = np.asarray(volume, dtype=float).flatten()
    if len(close) != len(volume):
        raise ValueError("close 와 volume 길이 불일치")
    if len(close) < 2:
        return np.zeros((0, 2), dtype=np.float32)

    c_safe = np.where(close  > 0, close,  eps)
    v_safe = np.where(volume > 0, volume, eps)

    log_ret = np.log(c_safe[1:] / c_safe[:-1])
    log_vol = np.log(v_safe[1:] / v_safe[:-1])

    out = np.stack([log_ret, log_vol], axis=1).astype(np.float32)
    out[~np.isfinite(out)] = 0.0
    return out


def extract_windows(
    series: np.ndarray,
    window: int = 60,
    stride: int = 5,
) -> np.ndarray:
    """
    (T, C) 시계열 → (N_windows, window, C). T < window 이면 빈 배열.
    """
    series = np.asarray(series, dtype=np.float32)
    if series.ndim != 2:
        raise ValueError(f"series 는 (T, C) 2D 여야 함. shape={series.shape}")
    T, C = series.shape
    if T < window or window <= 0 or stride <= 0:
        return np.zeros((0, window, C), dtype=np.float32)

    starts = list(range(0, T - window + 1, stride))
    if not starts:
        return np.zeros((0, window, C), dtype=np.float32)
    out = np.empty((len(starts), window, C), dtype=np.float32)
    for i, s in enumerate(starts):
        out[i] = series[s : s + window]
    return out


# ── Augmentation 3 종 ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class AugmentParams:
    """SimCLR 스타일 augmentation 파라미터. 한 view 생성에 사용.

    1차 (mask 0.10~0.30, σ=0.01): rank 40, chaebol 2.6× — 채택.
    강화 (mask 0.30~0.50, σ=0.05): rank 27, chaebol 3.3× — *rank collapse 악화*.
    데이터 반증 → 1차 설정 유지 (강한 aug 는 trivial solution 유도).
    """
    mask_pct_low:    float = 0.10
    mask_pct_high:   float = 0.30
    noise_sigma:     float = 0.01
    jitter_max_shift: int  = 2

    def __post_init__(self) -> None:
        assert 0.0 <= self.mask_pct_low <= self.mask_pct_high < 1.0
        assert self.noise_sigma >= 0.0
        assert self.jitter_max_shift >= 0


def mask_random(
    window: np.ndarray,
    *,
    mask_pct: float = 0.20,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """
    윈도우 (W, C) 의 mask_pct 비율 시점을 *모든 채널* 0 으로 마스크.
    원본 변경 없음 — 새 배열 반환.
    """
    rng = rng or np.random.default_rng()
    out = np.array(window, copy=True, dtype=np.float32)
    if out.ndim != 2:
        raise ValueError("window 는 (W, C) 2D")
    W = out.shape[0]
    n_mask = int(round(W * float(mask_pct)))
    if n_mask <= 0 or W == 0:
        return out
    idx = rng.choice(W, size=min(n_mask, W), replace=False)
    out[idx, :] = 0.0
    return out


def add_gaussian_noise(
    window: np.ndarray,
    *,
    sigma: float = 0.01,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """채널·시점별 i.i.d. N(0, σ²) 노이즈."""
    rng = rng or np.random.default_rng()
    if sigma <= 0:
        return np.array(window, copy=True, dtype=np.float32)
    out = np.array(window, copy=True, dtype=np.float32)
    out += rng.normal(0.0, sigma, size=out.shape).astype(np.float32)
    return out


def time_jitter(
    window: np.ndarray,
    *,
    max_shift: int = 2,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """
    시간축 shift ±max_shift. 양수 shift = 미래 방향, 음수 = 과거.
    빈 자리는 zero-pad.
    """
    rng = rng or np.random.default_rng()
    if max_shift <= 0:
        return np.array(window, copy=True, dtype=np.float32)
    shift = int(rng.integers(-max_shift, max_shift + 1))
    out = np.zeros_like(window, dtype=np.float32)
    if shift == 0:
        out[:] = window
        return out
    if shift > 0:
        out[shift:] = window[:-shift]
    else:
        out[:shift] = window[-shift:]
    return out


def augment_series(
    window: np.ndarray,
    params: Optional[AugmentParams] = None,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """SimCLR view 1 개 생성 — 3종 augmentation 모두 적용."""
    params = params or AugmentParams()
    rng    = rng    or np.random.default_rng()
    pct = float(rng.uniform(params.mask_pct_low, params.mask_pct_high))
    out = mask_random(window,        mask_pct=pct,                          rng=rng)
    out = add_gaussian_noise(out,    sigma=params.noise_sigma,              rng=rng)
    out = time_jitter(out,           max_shift=params.jitter_max_shift,     rng=rng)
    return out
