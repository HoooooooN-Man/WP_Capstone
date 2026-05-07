"""
api/_security.py
================
Tier 1B 4.4 (PRD §1.7) — 검색·인증 등 입력 검증 공용 헬퍼.

`escape_like(text)`
  SQL LIKE/ILIKE 패턴에서 와일드카드(`%`, `_`)와 escape 문자(`\\`)를 안전하게
  중화한다. SQL injection 자체는 파라미터 바인딩(?)으로 막히지만, 와일드카드
  bypass(예: `%` 입력으로 전수 조회) 와 ReDoS 류 패턴은 별도 escape 가 필요.

  사용 예 (DuckDB / PostgreSQL 공통):

      pat = f"%{escape_like(user_input)}%"
      conn.execute("... WHERE col LIKE ? ESCAPE '\\\\'", [pat])

  → ESCAPE 절은 SQL 표준이므로 두 DB 모두 동작. 호출처에서 명시 권장.
"""

from __future__ import annotations


# 백슬래시를 escape 문자로 사용 (SQL 표준 LIKE ESCAPE '\\').
# 호출처에서는 반드시 LIKE ? ESCAPE '\\' 절을 함께 명시해야 한다.
LIKE_ESCAPE_CHAR = "\\"


def escape_like(text: str) -> str:
    """LIKE 패턴 메타문자(`%`, `_`, `\\`)를 백슬래시로 escape."""
    if not text:
        return ""
    # 백슬래시를 먼저 처리해야 다른 escape 가 이중 처리되지 않음.
    return (
        text.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
    )
