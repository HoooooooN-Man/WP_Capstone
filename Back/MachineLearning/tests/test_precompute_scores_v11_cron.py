"""
test_precompute_scores_v11_cron.py
==================================
차차기 W6C — precompute_scores_v11_cron 의 변화 감지 단위 테스트.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data_pipeline"))
from precompute_scores_v11_cron import detect_change


def _make_db(path: Path, prices_max: int | None, scores_max: int | None,
             model_version: str = "v11a_prime") -> None:
    con = duckdb.connect(str(path))
    try:
        con.execute("CREATE TABLE prices (date BIGINT)")
        con.execute(
            "CREATE TABLE scores (date BIGINT, model_version VARCHAR, score DOUBLE)"
        )
        if prices_max is not None:
            con.execute("INSERT INTO prices VALUES (?)", [prices_max])
        if scores_max is not None:
            con.execute(
                "INSERT INTO scores VALUES (?, ?, 100.0)",
                [scores_max, model_version],
            )
    finally:
        con.close()


def test_needs_update_when_prices_newer(tmp_path):
    db = tmp_path / "t.duckdb"
    _make_db(db, prices_max=20260501, scores_max=20260429)
    needs, pm, sm = detect_change(db, "v11a_prime")
    assert needs is True
    assert pm == 20260501 and sm == 20260429


def test_no_change_when_equal(tmp_path):
    db = tmp_path / "t.duckdb"
    _make_db(db, prices_max=20260429, scores_max=20260429)
    needs, pm, sm = detect_change(db, "v11a_prime")
    assert needs is False
    assert pm == sm == 20260429


def test_no_change_when_scores_newer(tmp_path):
    """방어적 — scores 가 더 미래여도 적재 안 함."""
    db = tmp_path / "t.duckdb"
    _make_db(db, prices_max=20260420, scores_max=20260429)
    needs, _, _ = detect_change(db, "v11a_prime")
    assert needs is False


def test_needs_update_when_no_scores_for_variant(tmp_path):
    """scores 에 해당 model_version 행 없음 → 적재 필요."""
    db = tmp_path / "t.duckdb"
    _make_db(db, prices_max=20260429, scores_max=20260429,
             model_version="v9")   # 다른 variant 만 있음
    needs, pm, sm = detect_change(db, "v11a_prime")
    assert needs is True
    assert pm == 20260429
    assert sm is None


def test_needs_update_when_db_missing(tmp_path):
    """DB 부재 — 보수적으로 적재 필요 판정 (caller 가 실제 적재 시 새로 생성)."""
    needs, pm, sm = detect_change(tmp_path / "no_such.duckdb", "v11a_prime")
    assert needs is True
    assert pm is None and sm is None


def test_needs_update_when_scores_table_missing(tmp_path):
    """prices 만 있고 scores 테이블 부재 → 적재 필요."""
    db = tmp_path / "t.duckdb"
    con = duckdb.connect(str(db))
    try:
        con.execute("CREATE TABLE prices (date BIGINT)")
        con.execute("INSERT INTO prices VALUES (20260429)")
    finally:
        con.close()
    needs, pm, sm = detect_change(db, "v11a_prime")
    assert needs is True
    assert pm == 20260429
    assert sm is None
