"""
services/market_events.py
=========================
W8 축소 — 시장 레짐 감지 (1개만). KOSPI 직전 거래일 종가 대비 변화율 ≤ −3% → extreme_volatility.

설계:
  - *as_of_date 메타* (Tier 1.7) 가 이미 깔려있어 운영 정보 1개만 추가.
  - 어닝 D-day 는 DART API 통합 필요 → 컷 (외부 데이터 통합은 차차기).
  - regime 값: "normal" | "extreme_volatility".
  - KOSPI 프록시: data_pipeline/raw_index_fx.parquet 의 kospi_close 우선,
    부재 시 DuckDB prices 의 005930 (삼성전자) 캡스톤 프록시.

본 모듈의 *판단 함수* 는 순수. 데이터 어댑터만 외부 의존.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

EXTREME_THRESHOLD = -0.03   # -3% (사용자 명세)


def classify_regime(daily_change: float, *, threshold: float = EXTREME_THRESHOLD) -> str:
    """직전 거래일 대비 KOSPI 변화율 → regime 라벨.

    daily_change ≤ threshold (예: -3%) → 'extreme_volatility', 아니면 'normal'.
    NaN/inf → 'normal' (보수적 — 데이터 의심 시 정상 판정).
    """
    try:
        v = float(daily_change)
    except (TypeError, ValueError):
        return "normal"
    if v != v:   # NaN
        return "normal"
    if v <= threshold:
        return "extreme_volatility"
    return "normal"


# P0-4 (PRD §8.1) — 마켓스코어 5단계 + 0~100 점수
# Tier A 비율 (0~100%) 과 KOSPI 일일 변화율 (-5%~+5%) 을 결합해 0~100 점수 산출.
MARKET_LEVELS = [
    ("panic",     "패닉",   "비",   "공포",      0,  20),
    ("pessimism", "비관",   "흐림", "경계",     20,  40),
    ("neutral",   "중립",   "흐림", "관망",     40,  60),
    ("optimism",  "낙관",   "맑음", "긍정",     60,  80),
    ("greed",     "과욕",   "맑음", "주의(과열)", 80, 101),
]


def compute_market_score(
    tier_a_ratio_pct: float | None = None,
    daily_change:     float | None = None,
    *,
    weekly_change:    float | None = None,
    avg_prob:         float | None = None,
) -> float:
    """0~100 마켓스코어.

    B21 fix: 이전 base = `tier_a_ratio × 5` 는 ML 점수가 백분위라 ratio ≈ 20% 고정이라
    구조적으로 base = 80 saturated → score < 60 절대 불가. 패닉 단계 출현 불능.

    새 공식 (중립 50 기준 가산):
      score = 50
            + clamp(daily_change  × 800, -25, +25)   # 단기 모멘텀 (1일 ±3% 가 ±24)
            + clamp(weekly_change × 300, -15, +15)   # 추세 (5일 ±5% 가 ±15)
            + clamp((avg_prob - 0.5) × 100, -10, +10)  # 모델 낙관도
      → clamp 0~100

    `avg_prob` 은 당일 prob_ensemble 의 평균 (모델의 시장 전반 낙관도).
    `weekly_change` 미제공 시 daily 가중치만 사용. 모두 None 이면 50 반환 (중립).

    Legacy: 첫 positional 인자 (tier_a_ratio_pct) 는 backward-compat 용이며 무시.
    """
    score = 50.0

    if daily_change is not None:
        try:
            dc = float(daily_change)
            if dc == dc:   # not NaN
                score += max(-25.0, min(25.0, dc * 800.0))
        except (TypeError, ValueError):
            pass

    if weekly_change is not None:
        try:
            wc = float(weekly_change)
            if wc == wc:
                score += max(-15.0, min(15.0, wc * 300.0))
        except (TypeError, ValueError):
            pass

    if avg_prob is not None:
        try:
            ap = float(avg_prob)
            if ap == ap:
                score += max(-10.0, min(10.0, (ap - 0.5) * 100.0))
        except (TypeError, ValueError):
            pass

    return round(max(0.0, min(100.0, score)), 1)


def load_kospi_weekly_change(
    *,
    raw_index_parquet: Optional[str | Path] = None,
    duckdb_path:       Optional[str | Path] = None,
    as_of_date:        Optional[str]        = None,
) -> Optional[float]:
    """as_of_date 의 KOSPI 종가 / 5 거래일 전 종가 − 1.

    daily_change 와 동일한 어댑터 우선순위. 데이터 5일치 미만이면 None.
    """
    if raw_index_parquet is None:
        raw_index_parquet = os.getenv(
            "RAW_INDEX_PARQUET",
            r"E:\Capstone Data\data_pipeline\raw_index_fx.parquet",
        )
    parquet_path = Path(raw_index_parquet)
    if parquet_path.exists():
        try:
            import pandas as pd
            df = pd.read_parquet(parquet_path)
            df["date"] = pd.to_datetime(df["date"])
            df = df.dropna(subset=["kospi_close"]).sort_values("date").reset_index(drop=True)
            if as_of_date:
                df = df[df["date"] <= as_of_date]
            if len(df) >= 6:
                last  = float(df["kospi_close"].iloc[-1])
                prev5 = float(df["kospi_close"].iloc[-6])
                if prev5 > 0:
                    return last / prev5 - 1.0
        except Exception:
            pass

    if duckdb_path is None:
        duckdb_path = os.getenv("DUCKDB_PATH")
    if duckdb_path:
        try:
            import duckdb
            con = duckdb.connect(str(duckdb_path), read_only=True)
            try:
                where = ["ticker = '005930'"]
                if as_of_date:
                    cutoff_int = int(str(as_of_date).replace("-", ""))
                    where.append(f"date <= {cutoff_int}")
                rows = con.execute(f"""
                    SELECT close FROM prices WHERE {' AND '.join(where)}
                    ORDER BY date DESC LIMIT 6
                """).fetchall()
            finally:
                con.close()
            if len(rows) >= 6:
                last, prev5 = float(rows[0][0]), float(rows[5][0])
                if prev5 > 0:
                    return last / prev5 - 1.0
        except Exception:
            pass

    return None


def classify_market_level(score: float) -> dict:
    """0~100 마켓스코어 → 5단계 라벨 dict.

    Returns: {status, status_ko, weather, mood, score, range}.
    """
    s = max(0.0, min(100.0, float(score)))
    for status, ko, weather, mood, lo, hi in MARKET_LEVELS:
        if lo <= s < hi:
            return {
                "status":     status,
                "status_ko":  ko,
                "weather":    weather,
                "mood":       mood,
                "score":      round(s, 1),
                "score_range": f"{lo}-{hi - 1}",
            }
    # fallback (s == 100 일 때 greed)
    return {"status": "greed", "status_ko": "과욕", "weather": "맑음",
            "mood": "주의(과열)", "score": 100.0, "score_range": "80-100"}


# ── 데이터 어댑터 ──────────────────────────────────────────────────────────

def load_kospi_daily_change(
    *,
    raw_index_parquet: Optional[str | Path] = None,
    duckdb_path:       Optional[str | Path] = None,
    as_of_date:        Optional[str]        = None,
) -> Optional[float]:
    """as_of_date 의 KOSPI 종가 / 직전 거래일 종가 − 1.

    1) raw_index_fx.parquet 우선 (운영 환경 최신).
    2) 부재·범위 외 → DuckDB prices 005930 프록시 (캡스톤 패턴).
    3) 둘 다 실패 → None.
    """
    # 1) raw_index_fx.parquet
    if raw_index_parquet is None:
        raw_index_parquet = os.getenv(
            "RAW_INDEX_PARQUET",
            r"E:\Capstone Data\data_pipeline\raw_index_fx.parquet",
        )
    parquet_path = Path(raw_index_parquet)
    if parquet_path.exists():
        try:
            import pandas as pd
            df = pd.read_parquet(parquet_path)
            df["date"] = pd.to_datetime(df["date"])
            df = df.dropna(subset=["kospi_close"]).sort_values("date").reset_index(drop=True)
            if as_of_date:
                df = df[df["date"] <= as_of_date]
            if len(df) >= 2:
                last  = float(df["kospi_close"].iloc[-1])
                prev  = float(df["kospi_close"].iloc[-2])
                if prev > 0:
                    return last / prev - 1.0
        except Exception:
            pass

    # 2) DuckDB prices 005930 프록시.
    if duckdb_path is None:
        duckdb_path = os.getenv("DUCKDB_PATH")
    if duckdb_path:
        try:
            import duckdb
            con = duckdb.connect(str(duckdb_path), read_only=True)
            try:
                where = ["ticker = '005930'"]
                if as_of_date:
                    cutoff_int = int(str(as_of_date).replace("-", ""))
                    where.append(f"date <= {cutoff_int}")
                rows = con.execute(f"""
                    SELECT close FROM prices WHERE {' AND '.join(where)}
                    ORDER BY date DESC LIMIT 2
                """).fetchall()
            finally:
                con.close()
            if len(rows) >= 2:
                last, prev = float(rows[0][0]), float(rows[1][0])
                if prev > 0:
                    return last / prev - 1.0
        except Exception:
            pass

    return None


def detect_market_regime(
    *,
    raw_index_parquet: Optional[str | Path] = None,
    duckdb_path:       Optional[str | Path] = None,
    as_of_date:        Optional[str]        = None,
) -> str:
    """편의 함수 — load + classify."""
    change = load_kospi_daily_change(
        raw_index_parquet=raw_index_parquet,
        duckdb_path=duckdb_path,
        as_of_date=as_of_date,
    )
    if change is None:
        return "normal"     # 데이터 부재 — 보수적 default
    return classify_regime(change)
