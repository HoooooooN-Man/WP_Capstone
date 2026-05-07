"""
test_impression_outcomes.py
===========================
W1E — compute_impression_outcomes 의 *순수 함수* 단위 테스트.
DuckDB·PG 의존 부분은 통합 시연 (PG fixture 가용 환경) 으로 별도 검증.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ML_DIR = Path(__file__).resolve().parent.parent
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

from compute_impression_outcomes import compute_ticker_returns


# ── 정상 케이스 ──────────────────────────────────────────────────────────────

def test_returns_basic_positive_and_negative():
    shown = [
        {"ticker": "005930", "rank": 1},
        {"ticker": "000660", "rank": 2},
    ]
    base = {"005930": 100.0, "000660": 50.0}
    fwd  = {"005930": 110.0, "000660": 45.0}
    out = compute_ticker_returns(shown, fwd, base)
    assert out["005930"] == pytest.approx(0.10)
    assert out["000660"] == pytest.approx(-0.10)


def test_returns_round_to_six_decimals():
    shown = [{"ticker": "A", "rank": 1}]
    out = compute_ticker_returns(shown, {"A": 100.0}, {"A": 99.999})
    # (100/99.999 - 1) ≈ 0.0000100001 → 6자리 반올림.
    assert out["A"] == pytest.approx(0.00001, abs=1e-6)


# ── 누락·이상치 ────────────────────────────────────────────────────────────

def test_excludes_ticker_without_base():
    shown = [{"ticker": "A", "rank": 1}, {"ticker": "B", "rank": 2}]
    out = compute_ticker_returns(shown, {"A": 110.0, "B": 55.0}, {"A": 100.0})
    assert "A" in out and "B" not in out


def test_excludes_ticker_without_forward():
    """horizon 거래일이 아직 안 찼으면 forward None — 결과에서 제외."""
    shown = [{"ticker": "A", "rank": 1}, {"ticker": "B", "rank": 2}]
    fwd  = {"A": 110.0, "B": None}
    base = {"A": 100.0, "B": 50.0}
    out = compute_ticker_returns(shown, fwd, base)
    assert set(out.keys()) == {"A"}


def test_excludes_zero_or_negative_base():
    """상장폐지·이상치 — base ≤ 0 인 ticker 는 제외."""
    shown = [{"ticker": "A", "rank": 1}, {"ticker": "B", "rank": 2}]
    out = compute_ticker_returns(
        shown,
        {"A": 110.0, "B": 50.0},
        {"A": 0.0, "B": -1.0},
    )
    assert out == {}


def test_skips_entries_without_ticker_field():
    """방어적 — ticker 필드 누락 entry 는 무시."""
    shown = [{"rank": 1}, {"ticker": "A", "rank": 2}]
    out = compute_ticker_returns(shown, {"A": 110.0}, {"A": 100.0})
    assert out == {"A": pytest.approx(0.10)}


def test_empty_shown_tickers_returns_empty():
    assert compute_ticker_returns([], {}, {}) == {}


def test_no_overlap_returns_empty():
    """shown_tickers 와 가격 dict 의 ticker 가 전혀 안 겹침."""
    shown = [{"ticker": "A", "rank": 1}]
    out = compute_ticker_returns(shown, {"X": 100.0}, {"Y": 100.0})
    assert out == {}
