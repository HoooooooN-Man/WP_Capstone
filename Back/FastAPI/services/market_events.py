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
