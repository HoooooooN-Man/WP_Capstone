"""
test_watchlist.py
=================
Tier 1.6 (PRD §2.1) — 관심종목 CRUD 단위 테스트.

DB 의존 케이스(POST·GET 플로우)는 PostgreSQL fixture 가 필요해 캡스톤 범위에서는
스킵하고, 헬퍼 함수와 라우터 OpenAPI 회귀만 검증한다.

import 주의: pytest 의 rootdir 자동탐색이 `Back/` 을 sys.path 앞에 두어
`db` 가 `Back/db/` 패키지로 잘못 해석되는 충돌이 발생한다. 이를 우회하기 위해
sys.path 에서 `...\\Back` 항목을 제거하고 `Back/db` 만 두는 방어 코드를 넣었다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Back/db 패키지 루트.
_DB_ROOT = Path(__file__).resolve().parents[1]
_BACK_ROOT = _DB_ROOT.parent

# pytest 가 self-inserted 한 Back/ 항목을 제거 (db 패키지 충돌 방지).
sys.path[:] = [p for p in sys.path if Path(p).resolve() != _BACK_ROOT]
if str(_DB_ROOT) not in sys.path:
    sys.path.insert(0, str(_DB_ROOT))


def _import_watchlist_or_skip():
    """db 환경 dep (psycopg2 등) 누락 시 우아하게 skip.

    pytest 가 자동으로 Back/ 을 sys.path 에 끼워 `db` 가 `Back/db/` 로 잘못
    해석되는 충돌을 매번 우회하기 위해 import 직전에 path 를 재정리한다.
    """
    # 매번 재정리 (pytest 가 collection 사이에 다시 끼워 넣을 수 있음).
    sys.path[:] = [p for p in sys.path if Path(p).resolve() != _BACK_ROOT]
    if str(_DB_ROOT) not in sys.path:
        sys.path.insert(0, str(_DB_ROOT))

    # 잘못 해석된 db 모듈 캐시 무효화 (Back/db/__init__.py 를 db 로 잡았다면 제거).
    if "db" in sys.modules:
        cached = sys.modules["db"]
        cached_path = getattr(cached, "__file__", None) or ""
        if not cached_path.endswith(("db\\db\\__init__.py", "db/db/__init__.py")):
            # 잘못된 db 캐시 삭제 — 하위 모듈도 같이.
            for k in list(sys.modules):
                if k == "db" or k.startswith("db."):
                    sys.modules.pop(k, None)

    try:
        from api.users.watchlist import _normalize_ticker, router
        return _normalize_ticker, router
    except (ModuleNotFoundError, ImportError) as e:
        pytest.skip(f"watchlist module deps missing in test env: {e}")


def test_normalize_ticker_pads_numeric_to_six():
    _normalize_ticker, _ = _import_watchlist_or_skip()
    assert _normalize_ticker("5930") == "005930"
    assert _normalize_ticker("000660") == "000660"
    assert _normalize_ticker(" 5930 ") == "005930"


def test_normalize_ticker_uppercases_alpha():
    _normalize_ticker, _ = _import_watchlist_or_skip()
    assert _normalize_ticker("aapl") == "AAPL"
    assert _normalize_ticker("Tsla") == "TSLA"


def test_normalize_ticker_rejects_empty():
    from fastapi import HTTPException
    _normalize_ticker, _ = _import_watchlist_or_skip()
    with pytest.raises(HTTPException) as exc:
        _normalize_ticker("")
    assert exc.value.status_code == 400


def test_router_paths_registered():
    """server.py 가 watchlist 라우터를 등록했는지 path/method 로 회귀 검증."""
    _, router = _import_watchlist_or_skip()
    routes = {(r.path, frozenset(r.methods)) for r in router.routes if hasattr(r, "methods")}
    expected = {
        ("/users/me/watchlist",          frozenset({"GET"})),
        ("/users/me/watchlist",          frozenset({"POST"})),
        ("/users/me/watchlist/{ticker}", frozenset({"DELETE"})),
        ("/users/me/watchlist/migrate",  frozenset({"POST"})),
    }
    missing = expected - routes
    assert not missing, f"Missing watchlist routes: {missing}\nGot: {routes}"
