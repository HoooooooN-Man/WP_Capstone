"""
multi_labels.py
===============
W4 — 5 멀티 라벨 raw 값 계산 (순수 함수, numpy 만 의존).

차기_사이클.md §W4 명세 5 라벨 → 연속값으로 일괄 적재. W6 가 threshold 적용해
이진 라벨로 변환:

  y_abs_20d     ← fwd_return_20d ≥ 0.05
  y_alpha_20d   ← alpha_20d      ≥ 0.0
  y_riskadj_20d ← sharpe_20d     ≥ 0.5
  y_alpha_5d    ← alpha_5d       ≥ 0.0
  y_alpha_60d   ← alpha_60d      ≥ 0.0

본 모듈은 raw 만 산출 — 이진 변환·threshold 결정은 W6 모델 학습에서.

설계 원칙:
  - I/O 0. ndarray 입출력만.
  - 시계열 끝 부분(forward 데이터 부족) 은 NaN 반환 — caller 가 dropna.
  - alpha = stock_return − benchmark_return (KOSPI 프록시).
  - sharpe = mean / std (forward 윈도우 일별 수익률).
"""

from __future__ import annotations

import numpy as np


def forward_return(close: np.ndarray, horizon: int) -> np.ndarray:
    """
    `close[t+horizon] / close[t] − 1`. forward 미충족 시 NaN.

    close: (T,) 가격 시계열.
    Returns (T,) — 마지막 horizon 개는 NaN.
    """
    close = np.asarray(close, dtype=float).flatten()
    T = len(close)
    out = np.full(T, np.nan, dtype=np.float32)
    if T <= horizon or horizon < 1:
        return out
    base = close[:-horizon]
    fwd  = close[horizon:]
    valid = base > 0
    ret = np.full(T - horizon, np.nan, dtype=np.float32)
    ret[valid] = (fwd[valid] - base[valid]) / base[valid]
    out[:T - horizon] = ret
    return out


def alpha_vs_benchmark(
    close:     np.ndarray,
    benchmark: np.ndarray,
    horizon:   int,
) -> np.ndarray:
    """
    종목 forward return − 벤치마크 forward return. 길이 불일치 또는 forward 부족 시 NaN.
    `close` 와 `benchmark` 는 *같은 거래일 인덱스* 로 정렬돼 있다고 가정.
    """
    close     = np.asarray(close,     dtype=float).flatten()
    benchmark = np.asarray(benchmark, dtype=float).flatten()
    if close.shape != benchmark.shape:
        raise ValueError(f"close·benchmark 길이 불일치: {close.shape} vs {benchmark.shape}")
    return forward_return(close, horizon) - forward_return(benchmark, horizon)


def forward_sharpe(
    close:    np.ndarray,
    horizon:  int,
    *,
    eps:      float = 1e-9,
) -> np.ndarray:
    """
    `[t+1, t+horizon]` 일별 log return 의 평균 / 표준편차.

    벡터화 — sliding_window_view 로 O(T). Python loop 대비 50배 가속.
    """
    close = np.asarray(close, dtype=float).flatten()
    T = len(close)
    out = np.full(T, np.nan, dtype=np.float32)
    if T <= horizon + 1 or horizon < 2:
        return out
    safe = np.where(close > 0, close, eps)
    log_ret = np.diff(np.log(safe))                                # (T-1,)
    if len(log_ret) < horizon:
        return out

    from numpy.lib.stride_tricks import sliding_window_view
    windows = sliding_window_view(log_ret, horizon)                # (T-horizon, horizon)
    mu = windows.mean(axis=1)
    sd = windows.std(axis=1, ddof=1)
    sharpe = np.where(sd > eps, mu / sd, np.nan).astype(np.float32)
    out[: len(sharpe)] = sharpe
    return out


# ── 한 ticker 의 5 라벨 일괄 ────────────────────────────────────────────────

def compute_all_labels(
    close:     np.ndarray,
    benchmark: np.ndarray,
    *,
    horizons_alpha: tuple[int, int, int] = (5, 20, 60),
    horizon_sharpe:           int        = 20,
    horizons_abs:  tuple[int, ...]       = (5, 20, 60),
) -> dict[str, np.ndarray]:
    """
    한 ticker 의 *모든 라벨 raw* 값을 dict 로 반환.

    Returns
    -------
    {
      "fwd_return_5d":  (T,) np.float32,
      "fwd_return_20d": (T,) np.float32,
      "fwd_return_60d": (T,) np.float32,
      "alpha_5d":       (T,) np.float32,
      "alpha_20d":      (T,) np.float32,
      "alpha_60d":      (T,) np.float32,
      "sharpe_20d":     (T,) np.float32,
    }
    """
    out: dict[str, np.ndarray] = {}
    for h in horizons_abs:
        out[f"fwd_return_{h}d"] = forward_return(close, h)
    for h in horizons_alpha:
        out[f"alpha_{h}d"] = alpha_vs_benchmark(close, benchmark, h)
    out[f"sharpe_{horizon_sharpe}d"] = forward_sharpe(close, horizon_sharpe)
    return out
