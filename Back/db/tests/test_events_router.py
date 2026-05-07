"""
test_events_router.py
=====================
W1B Step 2 — events 라우터 회귀 테스트.

레이어:
  - 단위: 라우터 path 등록·Pydantic 스키마 검증 (PG 무관, 항상 실행).
  - 통합: 적재→조회·권한 검증·CASCADE (db_session fixture, PG 가용 시만).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_DB_ROOT = Path(__file__).resolve().parents[1]
_BACK_ROOT = _DB_ROOT.parent

sys.path[:] = [p for p in sys.path if Path(p).resolve() != _BACK_ROOT]
if str(_DB_ROOT) not in sys.path:
    sys.path.insert(0, str(_DB_ROOT))


def _import_router_or_skip():
    sys.path[:] = [p for p in sys.path if Path(p).resolve() != _BACK_ROOT]
    if str(_DB_ROOT) not in sys.path:
        sys.path.insert(0, str(_DB_ROOT))
    if "db" in sys.modules:
        cached_path = getattr(sys.modules["db"], "__file__", None) or ""
        if not cached_path.endswith(("db\\db\\__init__.py", "db/db/__init__.py")):
            for k in list(sys.modules):
                if k == "db" or k.startswith("db."):
                    sys.modules.pop(k, None)
    try:
        from api.events.events import router, _is_same_origin
        return router, _is_same_origin
    except (ModuleNotFoundError, ImportError) as e:
        pytest.skip(f"events router deps missing: {e}")


# ── 단위: path 등록 ─────────────────────────────────────────────────────────

def test_router_paths_registered():
    router, _ = _import_router_or_skip()
    routes = {(r.path, frozenset(r.methods)) for r in router.routes if hasattr(r, "methods")}
    expected = {
        ("/events/impressions",        frozenset({"POST"})),
        ("/events/clicks",             frozenset({"POST"})),
        ("/events/clicks/{click_id}",  frozenset({"PATCH"})),
        ("/events/health",             frozenset({"GET"})),
    }
    missing = expected - routes
    assert not missing, f"missing: {missing}\nGot: {routes}"


def test_router_prefix_and_tag():
    router, _ = _import_router_or_skip()
    assert router.prefix == "/events"
    assert "events" in router.tags


# ── 단위: Pydantic 스키마 ──────────────────────────────────────────────────

def test_impression_in_requires_shown_tickers_nonempty():
    _import_router_or_skip()  # path setup
    from api.events.events import ImpressionIn
    with pytest.raises(Exception):  # pydantic ValidationError
        ImpressionIn(model_version="v9", shown_tickers=[])


def test_impression_in_rejects_oversized_batch():
    _import_router_or_skip()
    from api.events.events import ImpressionsBatchRequest, ImpressionIn, ShownTickerEntry
    item = ImpressionIn(
        model_version="v9",
        shown_tickers=[ShownTickerEntry(ticker="005930", rank=1)],
    )
    with pytest.raises(Exception):
        ImpressionsBatchRequest(items=[item] * 200)


def test_shown_ticker_entry_validates_rank_positive():
    _import_router_or_skip()
    from api.events.events import ShownTickerEntry
    with pytest.raises(Exception):
        ShownTickerEntry(ticker="005930", rank=0)


def test_click_patch_dwell_must_be_nonneg():
    _import_router_or_skip()
    from api.events.events import ClickPatch
    with pytest.raises(Exception):
        ClickPatch(dwell_ms=-1)


# ── 단위: _is_same_origin 권한 헬퍼 ────────────────────────────────────────

def test_is_same_origin_user_match():
    _, _is_same_origin = _import_router_or_skip()
    imp = MagicMock(user_id=42, session_id=None)
    user = MagicMock(user_id=42)
    assert _is_same_origin(imp, user, None) is True


def test_is_same_origin_user_mismatch_returns_false():
    _, _is_same_origin = _import_router_or_skip()
    imp = MagicMock(user_id=42, session_id=None)
    user = MagicMock(user_id=99)
    assert _is_same_origin(imp, user, None) is False


def test_is_same_origin_session_match_anonymous():
    _, _is_same_origin = _import_router_or_skip()
    imp = MagicMock(user_id=None, session_id="anon123")
    assert _is_same_origin(imp, None, "anon123") is True


def test_is_same_origin_session_mismatch():
    _, _is_same_origin = _import_router_or_skip()
    imp = MagicMock(user_id=None, session_id="anon123")
    assert _is_same_origin(imp, None, "anon999") is False


def test_is_same_origin_both_none_returns_false():
    """양쪽 정체성 모두 비어있으면 비허용 (서버 운영자 케이스 등)."""
    _, _is_same_origin = _import_router_or_skip()
    imp = MagicMock(user_id=None, session_id=None)
    assert _is_same_origin(imp, None, None) is False


# ── 통합: PG 가용 시 ──────────────────────────────────────────────────────

def test_record_impression_anonymous_via_session(db_session):
    """비로그인 적재 — session_id 로 식별, 적재 후 조회."""
    from api.events.events import record_impressions, ImpressionsBatchRequest, ImpressionIn, ShownTickerEntry
    from db.models import RecommendationImpression

    payload = ImpressionsBatchRequest(items=[
        ImpressionIn(
            session_id="anon_test_router",
            model_version="v9",
            page_context="home",
            shown_tickers=[
                ShownTickerEntry(ticker="005930", rank=1, score=73.0, tier="A"),
                ShownTickerEntry(ticker="000660", rank=2, score=71.0, tier="A"),
            ],
        ),
    ])
    res = record_impressions(payload=payload, current_user=None, db=db_session)
    assert res.accepted == 1
    assert res.is_advice is False

    row = db_session.query(RecommendationImpression).filter_by(
        impression_id=res.items[0].impression_id
    ).first()
    assert row is not None
    assert row.user_id is None
    assert row.session_id == "anon_test_router"
    assert len(row.shown_tickers) == 2


def test_record_impression_rejects_no_identity(db_session):
    """비로그인이고 session_id 도 없으면 400."""
    from fastapi import HTTPException
    from api.events.events import record_impressions, ImpressionsBatchRequest, ImpressionIn, ShownTickerEntry

    payload = ImpressionsBatchRequest(items=[
        ImpressionIn(
            model_version="v9",
            shown_tickers=[ShownTickerEntry(ticker="005930", rank=1)],
        ),
    ])
    with pytest.raises(HTTPException) as exc:
        record_impressions(payload=payload, current_user=None, db=db_session)
    assert exc.value.status_code == 400


def test_record_click_then_patch_dwell(db_session):
    """impression 적재 → click 적재 → PATCH 로 dwell_ms 채움."""
    from api.events.events import (
        record_impressions, record_click, patch_click,
        ImpressionsBatchRequest, ImpressionIn, ShownTickerEntry,
        ClickIn, ClickPatch,
    )
    from db.models import RecommendationClick

    sid = "anon_click_test"
    imp_resp = record_impressions(
        payload=ImpressionsBatchRequest(items=[
            ImpressionIn(
                session_id=sid, model_version="v9",
                shown_tickers=[ShownTickerEntry(ticker="005930", rank=1)],
            ),
        ]),
        current_user=None,
        db=db_session,
    )
    imp_id = imp_resp.items[0].impression_id

    click_resp = record_click(
        payload=ClickIn(
            impression_id=imp_id, ticker="005930",
            rank_clicked=1, session_id=sid,
        ),
        current_user=None,
        db=db_session,
    )
    assert click_resp.is_advice is False
    click_id = click_resp.click_id

    # 이탈 시 dwell_ms 갱신.
    patched = patch_click(
        click_id=click_id,
        payload=ClickPatch(dwell_ms=4500, followup_action="watchlist_add", session_id=sid),
        current_user=None,
        db=db_session,
    )
    assert patched.click_id == click_id
    db_row = db_session.query(RecommendationClick).filter_by(click_id=click_id).first()
    assert db_row.dwell_ms == 4500
    assert db_row.followup_action == "watchlist_add"


def test_click_patch_rejects_other_session(db_session):
    """다른 session 의 click 을 수정하려 하면 403."""
    from fastapi import HTTPException
    from api.events.events import (
        record_impressions, record_click, patch_click,
        ImpressionsBatchRequest, ImpressionIn, ShownTickerEntry,
        ClickIn, ClickPatch,
    )

    sid_a = "anon_a"
    imp_resp = record_impressions(
        payload=ImpressionsBatchRequest(items=[
            ImpressionIn(
                session_id=sid_a, model_version="v9",
                shown_tickers=[ShownTickerEntry(ticker="005930", rank=1)],
            ),
        ]),
        current_user=None, db=db_session,
    )
    click_resp = record_click(
        payload=ClickIn(
            impression_id=imp_resp.items[0].impression_id,
            ticker="005930", rank_clicked=1, session_id=sid_a,
        ),
        current_user=None, db=db_session,
    )

    with pytest.raises(HTTPException) as exc:
        patch_click(
            click_id=click_resp.click_id,
            payload=ClickPatch(dwell_ms=1000, session_id="anon_b"),  # 다른 session
            current_user=None, db=db_session,
        )
    assert exc.value.status_code == 403


def test_click_on_missing_impression_404(db_session):
    """없는 impression_id 로 click 적재 시 404."""
    import uuid
    from fastapi import HTTPException
    from api.events.events import record_click, ClickIn

    with pytest.raises(HTTPException) as exc:
        record_click(
            payload=ClickIn(
                impression_id=uuid.uuid4(),
                ticker="005930", rank_clicked=1, session_id="anon_x",
            ),
            current_user=None, db=db_session,
        )
    assert exc.value.status_code == 404


def test_health_endpoint_returns_v1(db_session):
    from api.events.events import events_health
    res = events_health(db=db_session)
    assert res["schema_version"] == "v1"
    assert res["is_advice"] is False
