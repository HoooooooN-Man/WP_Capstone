"""
test_ab_split.py
================
W7B Step 1 — services/ab_split 의 *순수 함수* 단위 테스트.
"""

from __future__ import annotations

import pytest

from Back.FastAPI.services.ab_split import (
    DEFAULT_SPLIT,
    SplitResult,
    hash_bucket,
    parse_split,
    resolve_variant,
)


# ── parse_split ─────────────────────────────────────────────────────────────

def test_parse_split_basic():
    assert parse_split("v9:50,v11a_prime:50") == (("v9", 50), ("v11a_prime", 50))


def test_parse_split_default_for_empty():
    assert parse_split("") == parse_split(DEFAULT_SPLIT)


def test_parse_split_three_way():
    assert parse_split("a:50,b:30,c:20") == (("a", 50), ("b", 30), ("c", 20))


@pytest.mark.parametrize("bad", ["v9:50,v11:60", "v9:50", "v9:abc,v11:50",
                                  "v9:50,v11:-50,extra:100", ":50,v9:50"])
def test_parse_split_rejects_invalid(bad):
    with pytest.raises(ValueError):
        parse_split(bad)


# ── hash_bucket ────────────────────────────────────────────────────────────

def test_hash_bucket_deterministic():
    assert hash_bucket("u:42") == hash_bucket("u:42")


def test_hash_bucket_in_range():
    for k in ["u:1", "u:9999", "s:abc-def", ""]:
        b = hash_bucket(k)
        assert 0 <= b <= 99


def test_hash_bucket_distribution_is_roughly_uniform():
    """1000 user → 50/50 split bucket 카운트 ±10% 안."""
    counts = {"v9": 0, "v11": 0}
    for i in range(1000):
        b = hash_bucket(f"u:{i}")
        counts["v9" if b < 50 else "v11"] += 1
    # 50/50 ±10%.
    assert 400 <= counts["v9"]  <= 600
    assert 400 <= counts["v11"] <= 600


# ── resolve_variant ────────────────────────────────────────────────────────

def test_override_takes_precedence_over_hash():
    r = resolve_variant(user_id=1, override="v9", split_spec="a:50,b:50")
    assert r.variant == "v9"
    assert r.via == "override"


def test_latest_with_user_id_uses_hash():
    r = resolve_variant(user_id=42, override="latest", split_spec="a:100")
    assert r.variant == "a"
    assert r.via == "hash"
    assert 0 <= r.bucket <= 99


def test_latest_falls_back_to_session_id():
    r = resolve_variant(user_id=None, session_id="abc", override="latest",
                        split_spec="a:100")
    assert r.via == "hash"


def test_anonymous_fallback_picks_first_variant():
    r = resolve_variant(override="latest", split_spec="b:50,a:50")
    assert r.variant == "b"
    assert r.via == "fallback"


def test_same_user_always_same_variant():
    r1 = resolve_variant(user_id=42, override="latest",
                         split_spec="a:50,b:50")
    r2 = resolve_variant(user_id=42, override="latest",
                         split_spec="a:50,b:50")
    assert r1.variant == r2.variant


def test_split_distribution_50_50_for_1000_users():
    counts = {}
    for i in range(1000):
        r = resolve_variant(user_id=i, override="latest",
                            split_spec="v9:50,v11:50")
        counts[r.variant] = counts.get(r.variant, 0) + 1
    assert 400 <= counts.get("v9",  0) <= 600
    assert 400 <= counts.get("v11", 0) <= 600


def test_canary_10_percent():
    counts = {}
    for i in range(1000):
        r = resolve_variant(user_id=i, override="latest",
                            split_spec="v9:90,v11:10")
        counts[r.variant] = counts.get(r.variant, 0) + 1
    # canary 10% ±5%.
    assert 50  <= counts.get("v11", 0) <= 150
    assert 850 <= counts.get("v9",  0) <= 950


def test_default_split_is_latest_only():
    """env 미설정 시 'latest:100' — 인프라만 깔고 분배 OFF, 기존 svc 동작 유지."""
    counts = {}
    for i in range(200):
        r = resolve_variant(user_id=i, override="latest", split_spec=None)
        counts[r.variant] = counts.get(r.variant, 0) + 1
    import os
    if not os.getenv("AB_SPLIT"):
        assert set(counts.keys()) == {"latest"}


def test_user_id_takes_precedence_over_session_id():
    """user_id 와 session_id 둘 다 있으면 user_id 만 사용 (다른 session 으로 같은 user 면 동일 variant)."""
    r1 = resolve_variant(user_id=42, session_id="s1", override="latest",
                         split_spec="a:50,b:50")
    r2 = resolve_variant(user_id=42, session_id="s2", override="latest",
                         split_spec="a:50,b:50")
    assert r1.variant == r2.variant
