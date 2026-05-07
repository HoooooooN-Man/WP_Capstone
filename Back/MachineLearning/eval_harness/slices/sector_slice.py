"""슬라이스: WICS 대분류 섹터."""

from __future__ import annotations

import pandas as pd

from ._common import Slice


def slice_by_sector(rows: pd.DataFrame, periods: pd.DataFrame, min_count: int = 200) -> list[Slice]:
    if rows.empty or "sector" not in rows.columns:
        return []
    out: list[Slice] = []
    for k in sorted(rows["sector"].dropna().unique()):
        sub = rows[rows["sector"] == k]
        if len(sub) < min_count:
            continue
        out.append(Slice(dimension="sector", key=str(k), rows=sub))
    return out
