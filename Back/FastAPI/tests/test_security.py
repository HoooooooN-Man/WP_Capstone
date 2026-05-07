"""
test_security.py
================
Tier 1B 4.4 (PRD §1.7) — LIKE escape 헬퍼 회귀 테스트.
"""

from __future__ import annotations

from Back.FastAPI.core.security import escape_like


def test_empty_string_returns_empty():
    assert escape_like("") == ""


def test_plain_text_unchanged():
    assert escape_like("samsung") == "samsung"
    assert escape_like("삼성전자") == "삼성전자"


def test_percent_is_escaped():
    # `%` 입력 → escape 되어 와일드카드 의미를 잃음.
    assert escape_like("%") == "\\%"
    assert escape_like("a%b") == "a\\%b"


def test_underscore_is_escaped():
    assert escape_like("_") == "\\_"
    assert escape_like("a_b") == "a\\_b"


def test_backslash_is_doubled_first():
    # 백슬래시 자체도 escape 되어야 한다 (이중 처리 방지).
    assert escape_like("\\") == "\\\\"
    assert escape_like("a\\%b") == "a\\\\\\%b"


def test_combined_metachars():
    raw = "%a_b\\c%"
    expected = "\\%a\\_b\\\\c\\%"
    assert escape_like(raw) == expected
