"""
core/security.py
================
Tier 1B 4.4 — 검색 입력 안전 헬퍼. `Back/db/api/_security.py` 와 동일 동작.

ML 서버(:8001) 와 인증 서버(:8000) 양쪽이 같은 escape 정책을 쓰도록 두 파일을
의도적으로 동기화한다 (서로의 import 가 어색하기 때문).
"""

from __future__ import annotations


LIKE_ESCAPE_CHAR = "\\"


def escape_like(text: str) -> str:
    """LIKE/ILIKE 패턴 메타문자(`%`, `_`, `\\`)를 백슬래시로 escape.

    호출처에서는 반드시 ``LIKE ? ESCAPE '\\\\'`` 절을 함께 명시한다.
    """
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
    )
