"""
services/signal_label.py
========================
P0-1 (PRD §8.1) — ML 점수에 매수/보유/매도/관망 4단계 행동 라벨을 부착.

룰 (운영 모델 점수 0-100 기준):
  - 매수 (BUY)   : score >= 85         AND tier == 'A'
  - 보유 (HOLD)  : 70 <= score < 85    AND tier in ('A', 'B')
  - 매도 (SELL)  : score < 50          OR  tier == 'D'
  - 관망 (WATCH) : 그 외 (보통 50~70 / tier C)

주의: 본 라벨은 통계적 후처리이며, 실거래 자문이 아님 (PRD §9 면책).
"""

from __future__ import annotations


SIGNAL_BUY = "BUY"
SIGNAL_HOLD = "HOLD"
SIGNAL_SELL = "SELL"
SIGNAL_WATCH = "WATCH"

# 한국어 라벨 (FE 표시용)
SIGNAL_LABELS_KO = {
    SIGNAL_BUY: "매수",
    SIGNAL_HOLD: "보유",
    SIGNAL_SELL: "매도",
    SIGNAL_WATCH: "관망",
}


def compute_signal_label(score: float | None, tier: str | None) -> str:
    """점수 + 티어 → 4단계 행동 라벨."""
    if score is None:
        return SIGNAL_WATCH
    try:
        s = float(score)
    except (TypeError, ValueError):
        return SIGNAL_WATCH

    t = (tier or "").strip().upper()

    if t == "D" or s < 50:
        return SIGNAL_SELL
    if s >= 85 and t == "A":
        return SIGNAL_BUY
    if s >= 70 and t in ("A", "B"):
        return SIGNAL_HOLD
    return SIGNAL_WATCH


def attach_signal_labels(items: list[dict]) -> list[dict]:
    """추천/검색/스크리너 결과 dict 리스트에 signal_label / signal_label_ko 필드 부착 (in-place)."""
    for r in items:
        label = compute_signal_label(r.get("score"), r.get("tier"))
        r["signal_label"] = label
        r["signal_label_ko"] = SIGNAL_LABELS_KO[label]
    return items
