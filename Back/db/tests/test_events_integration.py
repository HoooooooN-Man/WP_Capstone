"""
test_events_integration.py
==========================
W1B Step 1 — events_v1 PostgreSQL 통합 테스트.

W1A 의 11 속성 테스트(test_events_schema.py) 는 모델 정의만 검증.
본 파일은 *실제 PG 동작* 을 검증: FK CASCADE/SET NULL, 복합 PK 위반, JSONB roundtrip.

PostgreSQL 미가용 시 conftest 가 자동 skip.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError


def test_impression_creates_with_minimal_fields(db_session):
    """user_id·session_id 모두 NULL 이어도 INSERT 가능 (체크 제약 없음)."""
    from db.models import RecommendationImpression
    imp = RecommendationImpression(
        shown_tickers=[{"ticker": "005930", "rank": 1, "score": 73}],
        model_version="v9",
    )
    db_session.add(imp)
    db_session.commit()
    assert imp.impression_id is not None
    assert imp.shown_at is not None


def test_impression_with_session_id_only(db_session):
    """비로그인 사용자: session_id 만, user_id NULL."""
    from db.models import RecommendationImpression
    imp = RecommendationImpression(
        session_id="anon_" + uuid.uuid4().hex[:16],
        shown_tickers=[{"ticker": "000660", "rank": 1, "score": 65}],
        model_version="v9",
        page_context="home",
    )
    db_session.add(imp)
    db_session.commit()
    assert imp.user_id is None
    assert imp.session_id is not None


def test_impression_with_embedding_version(db_session):
    """W3.5 이후 embedding_version 채워짐."""
    from db.models import RecommendationImpression
    imp = RecommendationImpression(
        shown_tickers=[{"ticker": "035420", "rank": 1, "score": 80}],
        model_version="v11c",
        embedding_version="emb_v1",
    )
    db_session.add(imp)
    db_session.commit()
    assert imp.embedding_version == "emb_v1"


def test_click_requires_impression_fk(db_session):
    """존재하지 않는 impression_id 로 click 적재 시 외래키 위반."""
    from db.models import RecommendationClick
    bad = RecommendationClick(
        impression_id=uuid.uuid4(),  # 없는 ID
        ticker="005930",
        rank_clicked=1,
    )
    db_session.add(bad)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_click_cascades_on_impression_delete(db_session):
    """결정 박제: impression 삭제 시 click 자동 삭제 (CASCADE)."""
    from db.models import RecommendationImpression, RecommendationClick
    imp = RecommendationImpression(
        shown_tickers=[{"ticker": "005930", "rank": 1, "score": 73}],
        model_version="v9",
    )
    db_session.add(imp)
    db_session.flush()

    click = RecommendationClick(
        impression_id=imp.impression_id,
        ticker="005930",
        rank_clicked=1,
    )
    db_session.add(click)
    db_session.commit()

    click_id = click.click_id
    db_session.delete(imp)
    db_session.commit()

    assert db_session.query(RecommendationClick).filter_by(click_id=click_id).first() is None


def test_outcome_composite_pk_three_horizons(db_session):
    """같은 impression 이 5d/20d/60d 세 행 가능 (복합 PK)."""
    from db.models import RecommendationImpression, ImpressionOutcome
    imp = RecommendationImpression(
        shown_tickers=[{"ticker": "005930", "rank": 1, "score": 73}],
        model_version="v9",
    )
    db_session.add(imp)
    db_session.flush()

    for h in (5, 20, 60):
        db_session.add(ImpressionOutcome(
            impression_id=imp.impression_id,
            outcome_horizon_days=h,
            ticker_returns={"005930": 0.03},
        ))
    db_session.commit()

    rows = db_session.query(ImpressionOutcome).filter_by(impression_id=imp.impression_id).all()
    assert len(rows) == 3


def test_outcome_duplicate_horizon_violates_pk(db_session):
    """같은 (impression_id, horizon) 은 1행만 — 복합 PK 위반."""
    from db.models import RecommendationImpression, ImpressionOutcome
    imp = RecommendationImpression(
        shown_tickers=[{"ticker": "005930", "rank": 1, "score": 73}],
        model_version="v9",
    )
    db_session.add(imp)
    db_session.flush()

    db_session.add(ImpressionOutcome(
        impression_id=imp.impression_id,
        outcome_horizon_days=20,
        ticker_returns={"005930": 0.03},
    ))
    db_session.add(ImpressionOutcome(
        impression_id=imp.impression_id,
        outcome_horizon_days=20,  # 중복
        ticker_returns={"005930": 0.05},
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_events_v1_meta_has_v1_row(db_session):
    """init_db.sql 의 INSERT 가 events_v1_meta 에 'v1' 한 줄 박제."""
    from db.models import EventsV1Meta
    meta = db_session.query(EventsV1Meta).filter_by(schema_version="v1").first()
    assert meta is not None
    assert meta.applied_at is not None
    assert "W1 logging" in (meta.notes or "")


def test_user_delete_sets_impression_user_id_null(db_session, sample_user):
    """결정 박제: 분석 자산 보존 — ON DELETE SET NULL."""
    from db.models import RecommendationImpression
    imp = RecommendationImpression(
        user_id=sample_user.user_id,
        shown_tickers=[{"ticker": "005930", "rank": 1, "score": 73}],
        model_version="v9",
    )
    db_session.add(imp)
    db_session.commit()
    imp_id = imp.impression_id

    db_session.delete(sample_user)
    db_session.commit()

    refreshed = db_session.query(RecommendationImpression).filter_by(impression_id=imp_id).first()
    assert refreshed is not None, "impression 이 사용자 삭제와 함께 사라졌다 (CASCADE 가 잘못 적용됨)"
    assert refreshed.user_id is None, "user_id 가 NULL 로 익명화되지 않음"


def test_jsonb_shown_tickers_roundtrip(db_session):
    """JSONB 컬럼이 list[dict] 를 그대로 보존 (PG 의존)."""
    from db.models import RecommendationImpression
    payload = [
        {"ticker": "005930", "rank": 1, "score": 73, "tier": "A"},
        {"ticker": "000660", "rank": 2, "score": 71, "tier": "A"},
    ]
    imp = RecommendationImpression(
        shown_tickers=payload,
        model_version="v9",
    )
    db_session.add(imp)
    db_session.commit()
    db_session.expire(imp)
    assert imp.shown_tickers == payload
