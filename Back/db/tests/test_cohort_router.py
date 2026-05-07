"""
test_cohort_router.py
=====================
W2C — cohort 라우터 회귀.

단위: path 등록·Pydantic 검증 (PG 무관).
통합: GET·PUT round-trip + 잘못된 cohort 400 (PG fixture 가용 시).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_DB_ROOT = Path(__file__).resolve().parents[1]
_BACK_ROOT = _DB_ROOT.parent

sys.path[:] = [p for p in sys.path if Path(p).resolve() != _BACK_ROOT]
if str(_DB_ROOT) not in sys.path:
    sys.path.insert(0, str(_DB_ROOT))


def _import_or_skip():
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
        from api.users.cohort import router, VALID_LABELS, get_cohort, update_cohort, CohortUpdate
        return router, VALID_LABELS, get_cohort, update_cohort, CohortUpdate
    except (ModuleNotFoundError, ImportError) as e:
        pytest.skip(f"cohort router deps missing: {e}")


# ── 단위 ────────────────────────────────────────────────────────────────────

def test_router_paths_registered():
    router, *_ = _import_or_skip()
    routes = {(r.path, frozenset(r.methods)) for r in router.routes if hasattr(r, "methods")}
    assert ("/users/me/cohort", frozenset({"GET"})) in routes
    assert ("/users/me/cohort", frozenset({"PUT"})) in routes


def test_valid_labels_set():
    _, VALID_LABELS, *_ = _import_or_skip()
    assert VALID_LABELS == {"conservative", "balanced", "growth", "dividend", "value"}


def test_cohort_update_pydantic_accepts_null():
    *_, CohortUpdate = _import_or_skip()
    body = CohortUpdate(cohort=None)
    assert body.cohort is None


def test_cohort_update_truncates_oversized_label():
    *_, CohortUpdate = _import_or_skip()
    # max_length=20 위반.
    with pytest.raises(Exception):
        CohortUpdate(cohort="a" * 21)


# ── 통합 (PG 가용 시) ──────────────────────────────────────────────────────

def test_get_cohort_default_none(db_session, sample_user):
    _, _, get_cohort, _, _ = _import_or_skip()
    res = get_cohort(current_user=sample_user)
    assert res.cohort is None
    assert res.is_advice is False


def test_put_cohort_round_trip(db_session, sample_user):
    _, _, get_cohort, update_cohort, CohortUpdate = _import_or_skip()
    res = update_cohort(
        payload=CohortUpdate(cohort="conservative"),
        current_user=sample_user, db=db_session,
    )
    assert res.cohort == "conservative"
    # round-trip — 바로 다음 GET 도 같은 값.
    res2 = get_cohort(current_user=sample_user)
    assert res2.cohort == "conservative"


def test_put_cohort_uppercase_normalized_to_lower(db_session, sample_user):
    _, _, _, update_cohort, CohortUpdate = _import_or_skip()
    res = update_cohort(
        payload=CohortUpdate(cohort="DIVIDEND"),
        current_user=sample_user, db=db_session,
    )
    assert res.cohort == "dividend"


def test_put_cohort_invalid_returns_400(db_session, sample_user):
    from fastapi import HTTPException
    _, _, _, update_cohort, CohortUpdate = _import_or_skip()
    with pytest.raises(HTTPException) as exc:
        update_cohort(
            payload=CohortUpdate(cohort="aggressive"),
            current_user=sample_user, db=db_session,
        )
    assert exc.value.status_code == 400


def test_put_cohort_null_resets(db_session, sample_user):
    _, _, _, update_cohort, CohortUpdate = _import_or_skip()
    update_cohort(
        payload=CohortUpdate(cohort="growth"),
        current_user=sample_user, db=db_session,
    )
    res = update_cohort(
        payload=CohortUpdate(cohort=None),
        current_user=sample_user, db=db_session,
    )
    assert res.cohort is None
