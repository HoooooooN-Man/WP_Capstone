"""
test_events_schema.py
=====================
W1A — events_v1 스키마 단위 테스트.

본 세션은 *모델 import + 클래스 속성 검증* 만 다룬다. PostgreSQL 의존 통합 테스트
(FK CASCADE, 복합 PK 위반, JSONB roundtrip 등) 는 *W1B 첫 sub-step (PostgreSQL
pytest fixture 정비) 후* 진행 — W1A 명세 §4 후미 정책.

import 주의 (Back/db/tests/test_watchlist.py 패턴 그대로):
  - pytest 가 자동으로 Back/ 을 sys.path 에 끼워 `db` 패키지 충돌이 발생할 수 있다.
  - import 직전에 path 를 재정리하고, 필요 dep (sqlalchemy 등) 누락 시 skip.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_DB_ROOT = Path(__file__).resolve().parents[1]   # Back/db/
_BACK_ROOT = _DB_ROOT.parent

# pytest 가 self-inserted 한 Back/ 항목을 제거 (db 패키지 충돌 방지).
sys.path[:] = [p for p in sys.path if Path(p).resolve() != _BACK_ROOT]
if str(_DB_ROOT) not in sys.path:
    sys.path.insert(0, str(_DB_ROOT))


def _import_models_or_skip():
    """SQLAlchemy/psycopg2 등 dep 누락 시 skip — CI 환경 보호."""
    sys.path[:] = [p for p in sys.path if Path(p).resolve() != _BACK_ROOT]
    if str(_DB_ROOT) not in sys.path:
        sys.path.insert(0, str(_DB_ROOT))

    # 잘못 캐시된 db 모듈 무효화.
    if "db" in sys.modules:
        cached = sys.modules["db"]
        cached_path = getattr(cached, "__file__", None) or ""
        if not cached_path.endswith(("db\\db\\__init__.py", "db/db/__init__.py")):
            for k in list(sys.modules):
                if k == "db" or k.startswith("db."):
                    sys.modules.pop(k, None)

    try:
        from db import models  # noqa: F401
        return models
    except (ModuleNotFoundError, ImportError) as e:
        pytest.skip(f"events schema test deps missing: {e}")


# ── 모델 import 가능 여부 ───────────────────────────────────────────────────

def test_models_importable():
    models = _import_models_or_skip()
    assert hasattr(models, "RecommendationImpression")
    assert hasattr(models, "RecommendationClick")
    assert hasattr(models, "ImpressionOutcome")
    assert hasattr(models, "EventsV1Meta")


# ── RecommendationImpression 컬럼 검증 ─────────────────────────────────────

def test_impression_table_name_and_pk():
    models = _import_models_or_skip()
    M = models.RecommendationImpression
    assert M.__tablename__ == "recommendation_impressions"
    pk_cols = [c.name for c in M.__table__.primary_key.columns]
    assert pk_cols == ["impression_id"]


def test_impression_required_columns_present():
    models = _import_models_or_skip()
    cols = {c.name for c in models.RecommendationImpression.__table__.columns}
    expected = {
        "impression_id", "user_id", "session_id", "cohort",
        "shown_tickers", "model_version", "embedding_version",
        "shown_at", "page_context",
    }
    missing = expected - cols
    assert not missing, f"missing columns: {missing}"


def test_impression_user_id_fk_set_null():
    """결정 박제: user 삭제 시 SET NULL (분석 자산 보존)."""
    models = _import_models_or_skip()
    user_id_col = models.RecommendationImpression.__table__.c.user_id
    fks = list(user_id_col.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert fk.column.table.name == "users"
    assert fk.column.name == "user_id"
    assert fk.ondelete == "SET NULL"
    assert user_id_col.nullable is True


def test_impression_indexes_defined():
    models = _import_models_or_skip()
    idx_names = {ix.name for ix in models.RecommendationImpression.__table__.indexes}
    assert "idx_impressions_user_at"    in idx_names
    assert "idx_impressions_session_at" in idx_names
    assert "idx_impressions_at"         in idx_names


# ── RecommendationClick ────────────────────────────────────────────────────

def test_click_fk_cascade():
    """결정 박제: impression 삭제 시 click 자동 삭제."""
    models = _import_models_or_skip()
    fks = list(models.RecommendationClick.__table__.c.impression_id.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "recommendation_impressions"
    assert fks[0].ondelete == "CASCADE"


def test_click_dwell_and_followup_nullable():
    """dwell_ms 와 followup_action 은 클릭 시점에는 NULL (이탈 시 PATCH)."""
    models = _import_models_or_skip()
    cols = {c.name: c for c in models.RecommendationClick.__table__.columns}
    assert cols["dwell_ms"].nullable is True
    assert cols["followup_action"].nullable is True
    # 필수 컬럼은 NOT NULL.
    assert cols["impression_id"].nullable is False
    assert cols["ticker"].nullable is False
    assert cols["rank_clicked"].nullable is False


# ── ImpressionOutcome ──────────────────────────────────────────────────────

def test_outcome_composite_pk():
    """복합 PK (impression_id, outcome_horizon_days) — 같은 impression 이 5d/20d/60d 세 행."""
    models = _import_models_or_skip()
    pk_cols = [c.name for c in models.ImpressionOutcome.__table__.primary_key.columns]
    assert set(pk_cols) == {"impression_id", "outcome_horizon_days"}


def test_outcome_fk_cascade_on_impression_delete():
    models = _import_models_or_skip()
    fks = list(models.ImpressionOutcome.__table__.c.impression_id.foreign_keys)
    assert len(fks) == 1
    assert fks[0].ondelete == "CASCADE"


# ── EventsV1Meta ───────────────────────────────────────────────────────────

def test_events_v1_meta_pk_is_schema_version():
    models = _import_models_or_skip()
    M = models.EventsV1Meta
    assert M.__tablename__ == "events_v1_meta"
    pk_cols = [c.name for c in M.__table__.primary_key.columns]
    assert pk_cols == ["schema_version"]


# ── init_db.sql 박제 검증 ──────────────────────────────────────────────────

def test_init_db_sql_contains_events_v1():
    """init_db.sql 에 4 테이블 + pgcrypto + meta INSERT 가 모두 포함됐는지."""
    sql_path = _DB_ROOT / "init_db.sql"
    if not sql_path.exists():
        pytest.skip("init_db.sql not found in expected location")
    sql_text = sql_path.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in sql_text
    assert "recommendation_impressions" in sql_text
    assert "recommendation_clicks"      in sql_text
    assert "impression_outcomes"        in sql_text
    assert "events_v1_meta"             in sql_text
    assert "INSERT INTO events_v1_meta" in sql_text
    assert "ON DELETE SET NULL"         in sql_text   # impression.user_id 정책
    assert "ON DELETE CASCADE"          in sql_text   # click·outcome 정책
