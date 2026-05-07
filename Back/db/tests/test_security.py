"""
test_security.py (Back/db)
==========================
Tier 1B 4.4 — `Back/db/api/_security.escape_like` 와 ML 서버
`Back/FastAPI/core/security.escape_like` 가 동일 동작을 보장.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Back/db 패키지 루트를 sys.path 에 추가 (api/_security 가 직접 import 가능하도록).
_DB_ROOT = Path(__file__).resolve().parents[1]
if str(_DB_ROOT) not in sys.path:
    sys.path.insert(0, str(_DB_ROOT))

from api._security import escape_like


def test_basic_escape():
    assert escape_like("") == ""
    assert escape_like("plain") == "plain"
    assert escape_like("%") == "\\%"
    assert escape_like("_") == "\\_"
    assert escape_like("\\") == "\\\\"


def test_combined():
    assert escape_like("%a_b\\c%") == "\\%a\\_b\\\\c\\%"


def test_korean_text_unchanged():
    assert escape_like("삼성전자") == "삼성전자"
    assert escape_like("SK하이닉스") == "SK하이닉스"
