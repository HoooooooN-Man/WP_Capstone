"""
eval_harness.slices._common
============================
슬라이서 공통 자료구조.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class Slice:
    """단일 슬라이스 결과."""
    dimension: str           # "time" | "sector" | "cap_size" | "regime"
    key:       str           # 슬라이스 라벨 ("2026", "IT", "Q1_small", "Up", ...)
    rows:      pd.DataFrame  # 행 단위(date,ticker) 평가 데이터 부분집합
    periods:   Optional[pd.DataFrame] = None  # 해당 슬라이스의 period 시계열 (regime 슬라이스에서만 사용)
