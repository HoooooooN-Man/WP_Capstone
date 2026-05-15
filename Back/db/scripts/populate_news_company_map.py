"""
populate_news_company_map.py
============================
news_normalized 의 기사 제목을 stocks 종목명과 매칭해 news_company_map 을 적재한다.

매칭 규칙 (false positive 억제):
  - 이름 길이 >= 4 : 단순 substring 매칭 (match_score=0.9, match_type='name_long')
  - 이름 길이 2~3 : 매칭 위치 앞뒤가 한글 음절이 아니어야 함(독립 토큰).
                    "정책대상"의 '대상', "나노기술"의 '나노' 같은 합성어 오탐 제거.
                    (match_score=0.7, match_type='name_short_boundary')
  - 이름 길이 1   : 제외 (오탐 과다)

사용:
  python -m Back.db.scripts.populate_news_company_map          # 적재
  python -m Back.db.scripts.populate_news_company_map --dry    # 미적재, 출력만

주의: DuckDB 쓰기는 배타적 락이 필요 — 실행 전 8001/8000 백엔드를 모두 중지해야 한다.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import duckdb

DB_PATH = os.getenv("DUCKDB_PATH", r"E:\Capstone Data\project_data\db\market_data.duckdb")


def _is_hangul(ch: str) -> bool:
    return "가" <= ch <= "힣"


def find_matches(title: str, stocks: list[tuple[str, str]]) -> list[tuple[str, str, str, float]]:
    """제목 1건 → [(ticker, company_name, match_type, match_score), ...]"""
    out: list[tuple[str, str, str, float]] = []
    seen_tickers: set[str] = set()
    title = title or ""
    for ticker, name in stocks:  # 긴 이름 우선 정렬돼 들어옴
        if not name or len(name) < 2 or ticker in seen_tickers:
            continue
        idx = title.find(name)
        if idx < 0:
            continue
        if len(name) >= 4:
            out.append((ticker, name, "name_long", 0.9))
            seen_tickers.add(ticker)
        else:
            before = title[idx - 1] if idx > 0 else ""
            after = title[idx + len(name)] if idx + len(name) < len(title) else ""
            if _is_hangul(before) or _is_hangul(after):
                continue  # 합성어 내부 — 오탐
            out.append((ticker, name, "name_short_boundary", 0.7))
            seen_tickers.add(ticker)
    return out


def main(dry: bool) -> int:
    if not Path(DB_PATH).exists():
        print(f"[ERR] DB 없음: {DB_PATH}")
        return 1

    con = duckdb.connect(DB_PATH, read_only=dry)

    stocks = con.execute(
        "SELECT ticker, name FROM stocks WHERE name IS NOT NULL"
    ).fetchall()
    stocks = sorted(
        [(t, n) for t, n in stocks if n and len(n) >= 2],
        key=lambda x: -len(x[1]),
    )
    news = con.execute("SELECT news_id, title FROM news_normalized").fetchall()

    rows: list[tuple[str, str, str, str, float]] = []
    for nid, title in news:
        for ticker, name, mtype, mscore in find_matches(title, stocks):
            rows.append((nid, ticker, name, mtype, mscore))

    print(f"기사 {len(news)}건 → 매칭 {len(rows)}건 "
          f"(기사 {len({r[0] for r in rows})}건에 매핑)")
    for nid, ticker, name, mtype, mscore in rows:
        print(f"  {ticker} {name:14s} [{mtype} {mscore}]  {nid[:12]}")

    if dry:
        print("\n[dry-run] 적재하지 않음.")
        return 0

    # 기존 news_company_map 은 전 컬럼이 INTEGER 로 잘못 생성돼 있음(빈 테이블).
    # news_id/ticker 는 VARCHAR 여야 news_normalized·stocks 와 JOIN 가능 → 재생성.
    con.execute("DROP TABLE IF EXISTS news_company_map")
    con.execute(
        """
        CREATE TABLE news_company_map (
            news_id      VARCHAR,
            ticker       VARCHAR,
            company_name VARCHAR,
            match_type   VARCHAR,
            match_score  DOUBLE
        )
        """
    )
    if rows:
        con.executemany(
            "INSERT INTO news_company_map "
            "(news_id, ticker, company_name, match_type, match_score) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
    total = con.execute("SELECT COUNT(*) FROM news_company_map").fetchone()[0]
    con.close()
    print(f"\n[done] news_company_map 적재 완료: {total}행")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry="--dry" in sys.argv))
