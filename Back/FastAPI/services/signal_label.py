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


# B54 — fair_value 거품 신호.
# 종목 가치 평가가 명백히 거품 (very_overvalued) 일 때 ML 매수 신호 차단.
# 통합 신호 = ML score + fair_value 양쪽 모두 우호일 때만 BUY.
OVERVALUED_BANDS = frozenset({"very_overvalued"})
UNDERVALUED_BANDS = frozenset({"very_undervalued", "undervalued"})


# B65 (2026-05-19): 30거래일 모멘텀이 음수면 BUY → HOLD 강등.
# "떨어지는 종목을 계속 BUY 추천" 약점 차단. 임계값은 0%.
# 단, momentum 정보가 없으면 (cumulative_return_pct=None) 룰 미적용 (graceful).
MOMENTUM_BUY_FLOOR_PCT = 0.0


def compute_signal_label(
    score: float | None,
    tier: str | None,
    fair_band: str | None = None,
    momentum_pct: float | None = None,
) -> str:
    """점수 + 티어 + fair_value band + 모멘텀 → 4단계 행동 라벨 (multi-factor).

    B15 + B52 + B54 + B59 + B65: tier 절대 임계 + fair_value band + 30d 모멘텀.

      BUY   : tier=A AND score ≥ 80 AND fair_band ∉ {very_overvalued}
              AND (momentum_pct ≥ 0 OR momentum_pct is None)
      WATCH : fair_band='very_overvalued' (거품경고 — A티어라도 매수 아님)
              OR (tier=C 또는 점수 50~60 ambiguous)
      SELL  : tier=D AND score < 35  (ML 모두 약할 때만 — 보수)
      HOLD  : tier ∈ (A,B) AND score ≥ 60
              OR (BUY 조건이지만 momentum_pct < 0 — B65 강등)

    B59 (2026-05-17): 거품주는 WATCH(관망) 가 정직. SELL 은 ML 모두 약한 종목에 한정.
    B65 (2026-05-19): 모델은 월별 rebal 가정 학습 → 최근 30일 하락한 종목은 BUY 부적격.
    paper trade backfill α -33% (강세장 KOSPI 대비 underperform) 결과 반영.
    """
    if score is None:
        return SIGNAL_WATCH
    try:
        s = float(score)
    except (TypeError, ValueError):
        return SIGNAL_WATCH

    t = (tier or "").strip().upper()
    band = (fair_band or "").strip().lower() or None

    # 거품주 → WATCH (관망). A티어라도 매수 차단, but 매도까지 강하지 않음.
    if band in OVERVALUED_BANDS:
        return SIGNAL_WATCH

    # SELL — ML 모두 약함 (tier D + score 하위). 보수적.
    if t == "D" and s < 35:
        return SIGNAL_SELL

    # BUY 후보 — ML 강한 신호 + 거품 아님.
    buy_candidate = (t == "A" and s >= 80)
    if buy_candidate:
        # B65: 30일 모멘텀 음수면 BUY → HOLD 강등.
        # momentum_pct None 이면 정보 없음 = 적용 안 함 (기존 동작 보존).
        if momentum_pct is not None:
            try:
                m = float(momentum_pct)
                if m < MOMENTUM_BUY_FLOOR_PCT:
                    return SIGNAL_HOLD
            except (TypeError, ValueError):
                pass
        return SIGNAL_BUY

    # HOLD — 긍정 신호 (BUY 못 미치는 경우).
    if s >= 60 and t in ("A", "B"):
        return SIGNAL_HOLD

    return SIGNAL_WATCH


def attach_signal_labels(items: list[dict]) -> list[dict]:
    """signal_label / signal_label_ko 필드 부착 (in-place).
    row['fair_band'] 있으면 fair-value multi-factor, row['cumulative_return_pct'] 있으면
    30d 모멘텀 룰 (B65) 적용. 둘 다 없어도 graceful (기존 동작 보존).
    """
    for r in items:
        label = compute_signal_label(
            r.get("score"),
            r.get("tier"),
            r.get("fair_band"),
            r.get("cumulative_return_pct"),
        )
        r["signal_label"] = label
        r["signal_label_ko"] = SIGNAL_LABELS_KO[label]
    return items
