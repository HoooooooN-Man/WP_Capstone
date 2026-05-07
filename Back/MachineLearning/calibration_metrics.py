"""
calibration_metrics.py
======================
Tier 1B 4.1 (캡스톤 §4.1) — 예측 확률의 캘리브레이션 분석.

ECE (Expected Calibration Error) 가 추천 시스템에서 왜 중요한가:
  - 본 프로젝트의 Tier A/B/C/D 컷오프는 *백분위 점수* 기준.
  - 사용자에게 "Tier A 는 모델이 매수 신호로 자신 있게 본 종목" 으로 설명한다.
  - prob_ensemble 이 캘리브레이션돼 있어야 그 "자신감" 이 실제 매수 적중률과
    일치한다. ECE > 0.05 면 컷오프 의미가 흔들린다.

핵심 함수 (모두 순수, I/O 분리):
  - reliability_diagram(y_true, y_prob, n_bins=10)
  - expected_calibration_error(y_true, y_prob, n_bins=10)
  - brier_score(y_true, y_prob)
  - calibration_bundle(y_true, y_prob, n_bins=10) → ReliabilityBundle

PRD §3.4 의 `/health/metrics.ece` 와 holdout 박제에서 동시 사용.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


# ── ECE ────────────────────────────────────────────────────────────────────

def expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """
    ECE — equal-width binning 으로 confidence vs accuracy 갭의 가중 평균.

    y_true: 실제 라벨 (0/1 이진).
    y_prob: 예측 확률 (0~1).
    n_bins: bin 개수 (보통 10 또는 15).

    수식:
        ECE = Σ_b (n_b/N) × |acc_b - conf_b|
    """
    y_true = np.asarray(y_true, dtype=int).flatten()
    y_prob = np.asarray(y_prob, dtype=float).flatten()
    if len(y_true) != len(y_prob):
        raise ValueError("y_true 와 y_prob 길이 불일치")
    if len(y_true) == 0:
        return 0.0
    if not np.all((y_prob >= 0) & (y_prob <= 1)):
        raise ValueError("y_prob 는 [0, 1] 구간이어야 합니다.")

    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    # right-exclusive 로 매핑하되, 마지막 bin 은 1.0 포함.
    idx = np.digitize(y_prob, bin_edges[1:-1], right=False)

    n = len(y_true)
    total_gap = 0.0
    for b in range(n_bins):
        mask = idx == b
        nb = int(mask.sum())
        if nb == 0:
            continue
        acc_b = float(y_true[mask].mean())
        conf_b = float(y_prob[mask].mean())
        total_gap += (nb / n) * abs(acc_b - conf_b)
    return total_gap


# ── Brier Score ────────────────────────────────────────────────────────────

def brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """평균 (y_prob - y_true)². 0 = 완벽, 0.25 = 무작위."""
    y_true = np.asarray(y_true, dtype=float).flatten()
    y_prob = np.asarray(y_prob, dtype=float).flatten()
    if len(y_true) != len(y_prob) or len(y_true) == 0:
        return 0.0
    return float(np.mean((y_prob - y_true) ** 2))


# ── Reliability Diagram ────────────────────────────────────────────────────

@dataclass
class ReliabilityBin:
    bin_lower:    float    # bin 의 낮은 경계 (포함)
    bin_upper:    float    # bin 의 높은 경계
    count:        int
    avg_confidence: float  # 해당 bin 의 평균 prob
    accuracy:     float    # 해당 bin 의 실제 양성 비율


@dataclass
class ReliabilityBundle:
    """Holdout 박제·API 응답·발표 슬라이드 reliability diagram 모두 본 dict 사용."""
    n_observations: int
    n_bins:         int
    ece:            float
    brier:          float
    bins:           list[ReliabilityBin] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "n_observations": self.n_observations,
            "n_bins":         self.n_bins,
            "ece":            round(self.ece, 4),
            "brier":          round(self.brier, 4),
            "bins": [
                {
                    "bin_lower":      round(b.bin_lower, 3),
                    "bin_upper":      round(b.bin_upper, 3),
                    "count":          b.count,
                    "avg_confidence": round(b.avg_confidence, 4),
                    "accuracy":       round(b.accuracy, 4),
                }
                for b in self.bins
            ],
        }


def reliability_diagram(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> list[ReliabilityBin]:
    """ECE 산출과 동일한 binning 으로 reliability bin 데이터 추출."""
    y_true = np.asarray(y_true, dtype=int).flatten()
    y_prob = np.asarray(y_prob, dtype=float).flatten()
    if len(y_true) == 0:
        return []
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.digitize(y_prob, bin_edges[1:-1], right=False)

    out: list[ReliabilityBin] = []
    for b in range(n_bins):
        mask = idx == b
        nb = int(mask.sum())
        if nb == 0:
            out.append(ReliabilityBin(
                bin_lower=float(bin_edges[b]),
                bin_upper=float(bin_edges[b + 1]),
                count=0,
                avg_confidence=0.0,
                accuracy=0.0,
            ))
            continue
        out.append(ReliabilityBin(
            bin_lower=float(bin_edges[b]),
            bin_upper=float(bin_edges[b + 1]),
            count=nb,
            avg_confidence=float(y_prob[mask].mean()),
            accuracy=float(y_true[mask].mean()),
        ))
    return out


def calibration_bundle(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> ReliabilityBundle:
    """ECE + Brier + per-bin reliability 한 번에."""
    return ReliabilityBundle(
        n_observations=int(len(y_true)),
        n_bins=n_bins,
        ece=expected_calibration_error(y_true, y_prob, n_bins),
        brier=brier_score(y_true, y_prob),
        bins=reliability_diagram(y_true, y_prob, n_bins),
    )


# ── 슬라이스별 ECE ─────────────────────────────────────────────────────────

def per_slice_ece(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    slice_keys: np.ndarray,
    n_bins: int = 10,
    min_count: int = 100,
) -> dict:
    """
    슬라이스(연도·섹터 등) 별 ECE.
    slice_keys: y_true 와 같은 길이의 분류 키.
    min_count: 슬라이스 행 수가 미만이면 skip (통계 신뢰도 부족).
    """
    y_true = np.asarray(y_true, dtype=int).flatten()
    y_prob = np.asarray(y_prob, dtype=float).flatten()
    keys = np.asarray(slice_keys).flatten()
    if not (len(y_true) == len(y_prob) == len(keys)):
        raise ValueError("입력 길이 불일치")

    out: dict[str, dict] = {}
    for k in np.unique(keys):
        mask = keys == k
        nb = int(mask.sum())
        if nb < min_count:
            continue
        out[str(k)] = {
            "n":     nb,
            "ece":   round(expected_calibration_error(y_true[mask], y_prob[mask], n_bins), 4),
            "brier": round(brier_score(y_true[mask], y_prob[mask]), 4),
        }
    return out
