"""슬라이스: 시총 4분위 (data_loader 가 cap_quartile 컬럼을 미리 부착)."""

from __future__ import annotations

import pandas as pd

from ._common import Slice


_ORDER = ["Q1_small", "Q2", "Q3", "Q4_large", "Unknown"]


def slice_by_cap_quartile(rows: pd.DataFrame, periods: pd.DataFrame, min_count: int = 200) -> list[Slice]:
    if rows.empty or "cap_quartile" not in rows.columns:
        return []
    out: list[Slice] = []
    seen = set(rows["cap_quartile"].dropna().unique())
    # 정렬: 정의된 순서 → 미지의 키는 마지막.
    keys = [k for k in _ORDER if k in seen] + sorted(seen - set(_ORDER))
    for k in keys:
        sub = rows[rows["cap_quartile"] == k]
        if len(sub) < min_count:
            continue
        out.append(Slice(dimension="cap_size", key=str(k), rows=sub))
    return out
