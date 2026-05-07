"""슬라이스: 연도(year) — 캡스톤 holdout 은 2026년뿐이라 사실상 1개."""

from __future__ import annotations

import pandas as pd

from ._common import Slice


def slice_by_time(rows: pd.DataFrame, periods: pd.DataFrame, min_count: int = 100) -> list[Slice]:
    if rows.empty or "year" not in rows.columns:
        return []
    out: list[Slice] = []
    for k in sorted(rows["year"].dropna().unique()):
        sub = rows[rows["year"] == k]
        if len(sub) < min_count:
            continue
        out.append(Slice(dimension="time", key=str(k), rows=sub))
    return out
