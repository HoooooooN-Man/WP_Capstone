"""
test_meta.py
============
Tier 1.7 (PRD §1.2) — ML API meta 봉투 회귀 테스트.

검증 대상:
  - meta 가 부착된 응답에 {model_version, as_of_date, generated_at, cache_hit,
    is_stub, request_id} 필드가 모두 존재한다.
  - meta.request_id 가 응답 헤더 X-Request-ID 와 일치한다.
  - generated_at 이 ISO8601 형식이다.

DuckDB 데이터가 없는 환경에서도 동작하도록, 200 응답일 때만 검증한다.
404/503 응답은 ErrorResponse 스키마이므로 본 파일이 아닌 test_errors.py 가 다룸.
"""

from __future__ import annotations

import re
from datetime import datetime


ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)?$")


def _assert_meta_shape(meta: dict, expected_request_id: str | None = None):
    assert isinstance(meta, dict), meta
    # 캡스톤 6 + 차기 사이클 6 = 12 필드 셋 모두 존재.
    assert set(meta.keys()) >= {
        "model_version", "as_of_date", "generated_at",
        "cache_hit", "is_stub", "request_id",
        "impression_id", "is_advice",
        "embedding_version", "cohort", "target_label", "diversify",
    }, meta
    # 차기 사이클 컴플라이언스 — 항상 false.
    assert meta["is_advice"] is False
    # generated_at 은 항상 채워져야 한다.
    assert isinstance(meta["generated_at"], str)
    assert ISO8601_RE.match(meta["generated_at"]), meta["generated_at"]
    # 파서로도 한 번 더 확인.
    datetime.fromisoformat(meta["generated_at"].replace("Z", "+00:00"))
    # 불리언 보장.
    assert isinstance(meta["cache_hit"], bool)
    assert isinstance(meta["is_stub"], bool)
    if expected_request_id is not None:
        assert meta["request_id"] == expected_request_id, meta


def test_recommendations_has_meta(client):
    rid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    r = client.get(
        "/api/v1/stocks/recommendations?top_k=5",
        headers={"X-Request-ID": rid},
    )
    if r.status_code != 200:
        # 데이터 없는 환경에서는 404/503 — meta 회귀는 다른 케이스에서 다뤄짐.
        return
    body = r.json()
    assert "meta" in body, body
    _assert_meta_shape(body["meta"], expected_request_id=rid)
    assert r.headers.get("X-Request-ID") == rid


def test_history_has_meta(client):
    r = client.get("/api/v1/stocks/005930/history")
    if r.status_code != 200:
        return
    body = r.json()
    assert "meta" in body, body
    _assert_meta_shape(body["meta"])


def test_sector_summary_has_meta(client):
    r = client.get("/api/v1/stocks/sectors/summary")
    if r.status_code != 200:
        return
    body = r.json()
    assert "meta" in body, body
    _assert_meta_shape(body["meta"])


def test_recommendations_has_impression_id_uuid(client):
    """W1C — 추천 목록은 노출 인스턴스. impression_id UUID 자동 부여."""
    import re as _re
    UUID_RE = _re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        _re.IGNORECASE,
    )
    r = client.get("/api/v1/stocks/recommendations?top_k=3")
    if r.status_code != 200:
        return
    meta = r.json()["meta"]
    assert meta["impression_id"] is not None
    assert UUID_RE.match(meta["impression_id"]), meta["impression_id"]
    # 두 번 호출하면 두 다른 UUID — 매 노출이 새 인스턴스.
    r2 = client.get("/api/v1/stocks/recommendations?top_k=3")
    if r2.status_code == 200:
        assert r2.json()["meta"]["impression_id"] != meta["impression_id"]


def test_history_has_no_impression_id(client):
    """history 는 노출 인스턴스가 아님 — impression_id NULL."""
    r = client.get("/api/v1/stocks/005930/history")
    if r.status_code != 200:
        return
    meta = r.json()["meta"]
    assert meta.get("impression_id") is None


def test_meta_fields_optional_remain_backward_compatible(client):
    """기존 top-level 필드 (date, model_version, total, items) 가 깨지지 않았는지."""
    r = client.get("/api/v1/stocks/recommendations?top_k=3")
    if r.status_code != 200:
        return
    body = r.json()
    # 기존 필드 그대로.
    assert "date" in body
    assert "model_version" in body
    assert "total" in body
    assert "items" in body
    assert isinstance(body["items"], list)
