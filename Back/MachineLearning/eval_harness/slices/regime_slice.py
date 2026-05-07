"""
슬라이스: 시장 국면 regime (Up / Down).

regime 슬라이스는 *period 시계열* 도 함께 분할한다 — 운용 메트릭(Sharpe·MDD·alpha)
이 그 슬라이스의 부분으로 측정되어야 의미가 있기 때문.
"""

from __future__ import annotations

import pandas as pd

from ._common import Slice


def slice_by_regime(rows: pd.DataFrame, periods: pd.DataFrame, min_count: int = 200) -> list[Slice]:
    if rows.empty or "regime" not in rows.columns:
        return []

    # regime 별로 rows 와 periods 모두 분할.
    # periods 는 date_int 키를 갖고, rows 의 (date_int, regime) 매핑으로 채워줌.
    if not periods.empty and "date_int" in periods.columns:
        date_to_regime = (
            rows.dropna(subset=["regime"])
            .groupby("date_int")["regime"]
            .agg(lambda s: s.mode().iat[0] if not s.mode().empty else "Unknown")
            .to_dict()
        )
        periods = periods.copy()
        periods["regime"] = periods["date_int"].map(date_to_regime).fillna("Unknown")
    else:
        periods = periods.copy()
        periods["regime"] = []

    out: list[Slice] = []
    for k in sorted(rows["regime"].dropna().unique()):
        sub_rows = rows[rows["regime"] == k]
        if len(sub_rows) < min_count:
            continue
        sub_periods = periods[periods["regime"] == k] if not periods.empty else pd.DataFrame()
        out.append(Slice(
            dimension="regime",
            key=str(k),
            rows=sub_rows,
            periods=sub_periods if not sub_periods.empty else None,
        ))
    return out
