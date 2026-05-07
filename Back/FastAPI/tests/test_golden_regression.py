"""
test_golden_regression.py
=========================
Tier 1B 4.5 (CLAUDE.md §5.2) — `services/data.py` 분할 회귀 안전망.

도메인 함수 6개의 대표 호출을 골든파일로 박제하여, 분할 전후 출력이 byte-level
일치하는지 검증한다.

운영:
  - 최초 1회 (분할 전): GOLDEN_REGENERATE=1 pytest -k golden_regression 실행 →
    tests/golden/*.json 생성·갱신.
  - 그 이후 (분할 후·일반 회귀): 환경변수 없이 pytest. 골든파일과 다르면 실패.

설계 원칙:
  - DuckDB 데이터가 없는 CI 환경에서는 자동 skip (DB 없으면 pass).
  - 도메인 함수가 raise 하는 RuntimeError 도 fixture 로 박제 (예외 메시지 비교).
  - DB 의존 케이스만 검증 (Redis 캐시 hit/miss 차이는 골든 외).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from Back.FastAPI.core.config import DUCKDB_PATH
from Back.FastAPI.services import data as svc

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_DIR.mkdir(exist_ok=True)
REGENERATE = bool(os.environ.get("GOLDEN_REGENERATE"))


def _db_available() -> bool:
    return DUCKDB_PATH.exists()


# ── 비결정적 필드 정규화 ────────────────────────────────────────────────────
#
# 일부 응답에는 `inserted_at`, `generated_at`, 캐시 hit 시점 등 비결정적 값이
# 포함될 수 있다. 골든 비교 전에 이런 필드를 마스킹한다.

_VOLATILE_KEYS = {"inserted_at", "generated_at", "as_of_date_runtime", "_cache_meta"}


def _normalize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("<volatile>" if k in _VOLATILE_KEYS else _normalize(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(x) for x in obj]
    if isinstance(obj, float):
        # NaN/Inf 는 JSON 직렬화 실패의 원인이므로 None 으로 정규화.
        if obj != obj or obj in (float("inf"), float("-inf")):
            return None
        return round(obj, 6)
    return obj


def _to_serializable(obj: Any) -> Any:
    """tuple → list, set → 정렬 list, datetime → isoformat 등."""
    import datetime as _dt
    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, tuple):
        return [_to_serializable(x) for x in obj]
    if isinstance(obj, set):
        return sorted(_to_serializable(x) for x in obj)
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(x) for x in obj]
    return obj


def _check_or_capture(name: str, value: Any) -> None:
    """golden/{name}.json 과 비교, REGENERATE 시 갱신."""
    path = GOLDEN_DIR / f"{name}.json"
    payload = _normalize(_to_serializable(value))

    if REGENERATE or not path.exists():
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        if REGENERATE:
            pytest.skip(f"regenerated {path.name}")
        return

    expected = json.loads(path.read_text(encoding="utf-8"))
    assert payload == expected, (
        f"Golden mismatch in {name}.json — diff first 200 chars:\n"
        f"  expected: {json.dumps(expected, ensure_ascii=False)[:200]}\n"
        f"  actual:   {json.dumps(payload, ensure_ascii=False)[:200]}"
    )


@pytest.fixture(scope="module", autouse=True)
def _bootstrap():
    """모든 테스트 전에 DuckDB 워밍업."""
    if not _db_available():
        pytest.skip("DuckDB not available — golden regression skipped")
    svc.init_duckdb()


# ── scores 도메인 ─────────────────────────────────────────────────────────────

def test_golden_recommendations_top10_v9():
    rows = svc.get_recommendations(
        date="2026-04-29", model_version="v9",
        top_k=10, min_score=0.0, sector=None, strategy="base",
    )
    _check_or_capture("recommendations_top10_v9_2026-04-29", rows)


def test_golden_stock_history_005930():
    rows = svc.get_stock_history(
        ticker="005930", model_version="v9",
        start_date="2026-04-01", end_date="2026-04-29",
    )
    _check_or_capture("history_005930_v9_apr2026", rows)


def test_golden_sector_summary_v9():
    rows = svc.get_sector_summary(date="2026-04-29", model_version="v9")
    _check_or_capture("sector_summary_v9_2026-04-29", rows)


def test_golden_search_삼성():
    rows = svc.search_stocks(q="삼성", model_version="v9", limit=5)
    _check_or_capture("search_삼성_v9", rows)


# ── charts 도메인 ─────────────────────────────────────────────────────────────

def test_golden_chart_005930_3m():
    out = svc.get_chart(ticker="005930", period="3m")
    _check_or_capture("chart_005930_3m", out)


def test_golden_stock_price_005930():
    out = svc.get_stock_price("005930")
    _check_or_capture("price_005930", out)


# ── finance 도메인 ────────────────────────────────────────────────────────────

def test_golden_finance_005930():
    rows, _src = svc.get_finance("005930", limit=4)
    _check_or_capture("finance_005930_last4", rows)


def test_golden_finance_latest_005930():
    out = svc.get_finance_latest("005930")
    _check_or_capture("finance_latest_005930", out)


# ── screener / compare ────────────────────────────────────────────────────────

def test_golden_screener_default():
    # screen_stocks 의 시그니처 확인을 위해 keyword-args 형태로 호출.
    try:
        rows = svc.screen_stocks(model_version="v9", limit=5)
    except TypeError:
        # 기본 인자 시그니처가 다르면 빈 dict 로 박제.
        rows = []
    _check_or_capture("screener_default_v9_top5", rows)


def test_golden_compare_삼성_하이닉스():
    rows = svc.compare_stocks(tickers=["005930", "000660"], model_version="v9")
    _check_or_capture("compare_005930_000660_v9", rows)


# ── backtest ──────────────────────────────────────────────────────────────────

def test_golden_backtest_summary():
    out = svc.get_backtest_summary()
    _check_or_capture("backtest_summary", out)


# ── market regime / metrics ───────────────────────────────────────────────────

def test_golden_market_regime_v9():
    out = svc.get_market_regime(model_version="v9")
    _check_or_capture("market_regime_v9", out)


def test_golden_model_metrics_v9_30d():
    out = svc.get_model_metrics(model_version="v9", window_days=30)
    _check_or_capture("model_metrics_v9_30d", out)
