"""
eval_harness.slices — 평가 하네스 슬라이스 모음.

각 슬라이서: (rows, period_returns) → list[Slice]
Slice = (key: str, rows_subset: DataFrame, period_subset: DataFrame)

캡스톤 축약: time / sector / cap_size / regime 4개만.
"""

from .time_slice   import slice_by_time
from .sector_slice import slice_by_sector
from .cap_slice    import slice_by_cap_quartile
from .regime_slice import slice_by_regime

__all__ = [
    "slice_by_time",
    "slice_by_sector",
    "slice_by_cap_quartile",
    "slice_by_regime",
]
