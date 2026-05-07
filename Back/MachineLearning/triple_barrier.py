"""
triple_barrier.py
=================
Tier 1B 4.3 (PRD §5.1 / 캡스톤 §4.3) — Triple Barrier 라벨 (López de Prado, 2018).

설계 원칙:
  - 본 모듈은 *순수 함수* — 단위 테스트로 검증 가능.
  - 호출자는 가격 시계열을 ndarray 로 넘기고 라벨을 받는다.
  - DB·I/O 없음.

Triple Barrier Method:
  - Upper barrier (이익실현): close[t] × (1 + upper_pct)
  - Lower barrier (손절):     close[t] × (1 - lower_pct)
  - Time barrier (만료):      t + horizon (거래일)
  - 라벨 규칙:
      upper 먼저 닿음 → 1 (positive)
      lower 먼저 닿음 → 0 (negative)
      만료 시 미터치 → 만료일 종가의 부호 (수익률 ≥ 0 → 1, 그 외 0)

기본 파라미터: 캡스톤 §5.1 권고 — 상단 +7%, 하단 −4%, 시간 20거래일.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class TripleBarrierParams:
    upper_pct: float = 0.07     # +7%
    lower_pct: float = 0.04     # -4%
    horizon:   int   = 20       # 20 거래일

    def __post_init__(self) -> None:
        assert self.upper_pct > 0, "upper_pct must be positive"
        assert self.lower_pct > 0, "lower_pct must be positive (use absolute, sign auto)"
        assert self.horizon >= 1, "horizon must be ≥ 1 trading day"


def label_single(prices: np.ndarray, t: int, params: TripleBarrierParams) -> Optional[int]:
    """
    `prices[t]` 시점에서 Triple Barrier 라벨 산출.
    prices: 거래일 정렬된 close 시계열.
    t: 라벨링 대상 인덱스.

    Returns
    -------
    1 (positive) | 0 (negative) | None (horizon 끝이 시계열 밖이라 산출 불가)
    """
    n = len(prices)
    if t < 0 or t >= n:
        return None
    end_idx = t + params.horizon
    if end_idx >= n:
        return None

    p0 = float(prices[t])
    if p0 <= 0:
        return None

    upper = p0 * (1.0 + params.upper_pct)
    lower = p0 * (1.0 - params.lower_pct)

    # t+1 부터 t+horizon 까지 (포함) 스캔.
    window = prices[t + 1: end_idx + 1]
    upper_hit = np.where(window >= upper)[0]
    lower_hit = np.where(window <= lower)[0]

    first_upper = int(upper_hit[0]) if len(upper_hit) else int(1e9)
    first_lower = int(lower_hit[0]) if len(lower_hit) else int(1e9)

    if first_upper == int(1e9) and first_lower == int(1e9):
        # 만료 — 만료일 부호.
        return 1 if window[-1] >= p0 else 0
    if first_upper < first_lower:
        return 1
    if first_lower < first_upper:
        return 0
    # 동일 일자에 둘 다 닿음 (드물게 일중 변동) — 보수적으로 0.
    return 0


def label_series(
    prices: np.ndarray,
    params: Optional[TripleBarrierParams] = None,
) -> np.ndarray:
    """
    가격 시계열 전체에 대해 Triple Barrier 라벨.
    horizon 끝이 시계열 밖인 행은 -1 마스크 (호출자가 dropna 처리).
    """
    if params is None:
        params = TripleBarrierParams()
    out = np.full(len(prices), -1, dtype=np.int8)
    for t in range(len(prices)):
        v = label_single(prices, t, params)
        out[t] = v if v is not None else -1
    return out


def label_simple_binary(
    prices: np.ndarray,
    horizon: int = 20,
    threshold: float = 0.05,
) -> np.ndarray:
    """
    v9 의 기존 라벨: t+horizon 일 후 수익률 ≥ threshold 면 1.
    triple_barrier 와 비교용으로 동일 인터페이스 제공.
    """
    n = len(prices)
    out = np.full(n, -1, dtype=np.int8)
    for t in range(n - horizon):
        if prices[t] <= 0:
            continue
        ret = (float(prices[t + horizon]) - float(prices[t])) / float(prices[t])
        out[t] = 1 if ret >= threshold else 0
    return out
