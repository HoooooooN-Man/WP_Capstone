"""
test_core_resolve_version.py
============================
차차기 W1 — services/_core.resolve_version 의 DEFAULT_MODEL_VERSION 동작 검증.
실 DuckDB 연결은 conftest 의 fixture 활용. con() 와 _model_version_exists 만 mock.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from Back.FastAPI.services import _core


# ── helper ──────────────────────────────────────────────────────────────────

class FakeRow:
    def __init__(self, value): self._v = value
    def fetchone(self): return self._v


class FakeCon:
    """resolve_version 안의 두 SQL 호출 시퀀스를 흉내내는 fake connection."""
    def __init__(self, sequence):
        self._seq = list(sequence)
        self.calls = []
    def execute(self, sql, *args):
        self.calls.append(sql.strip())
        nxt = self._seq.pop(0) if self._seq else None
        return FakeRow(nxt)


# ── 1) 명시 버전 우회 ──────────────────────────────────────────────────────

def test_explicit_version_passthrough():
    assert _core.resolve_version("v9") == "v9"
    assert _core.resolve_version("v11a_prime") == "v11a_prime"


def test_explicit_strips_whitespace():
    assert _core.resolve_version("  v9  ") == "v9"


# ── 2) DEFAULT_MODEL_VERSION env var 우선 ──────────────────────────────────

def test_env_var_used_when_version_exists(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL_VERSION", "v11a_prime")
    with patch.object(_core, "_model_version_exists", return_value=True):
        assert _core.resolve_version("latest") == "v11a_prime"
    with patch.object(_core, "_model_version_exists", return_value=True):
        assert _core.resolve_version("") == "v11a_prime"
    with patch.object(_core, "_model_version_exists", return_value=True):
        assert _core.resolve_version(None) == "v11a_prime"  # type: ignore[arg-type]


def test_env_var_falls_back_when_version_missing(monkeypatch):
    """env var 값이 scores 에 부재 → inserted_at fallback (안전)."""
    monkeypatch.setenv("DEFAULT_MODEL_VERSION", "v15_typo")
    fake = FakeCon([("v9",)])  # 첫 SQL 응답 = v9
    with patch.object(_core, "_model_version_exists", return_value=False):
        with patch.object(_core, "con", return_value=fake):
            assert _core.resolve_version("latest") == "v9"


def test_env_var_unset_uses_inserted_at(monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL_VERSION", raising=False)
    fake = FakeCon([("v11a_prime",)])
    with patch.object(_core, "con", return_value=fake):
        assert _core.resolve_version("latest") == "v11a_prime"


def test_env_var_empty_string_treated_as_unset(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL_VERSION", "")
    fake = FakeCon([("v11a_prime",)])
    with patch.object(_core, "con", return_value=fake):
        assert _core.resolve_version("latest") == "v11a_prime"


def test_env_var_whitespace_treated_as_unset(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL_VERSION", "   ")
    fake = FakeCon([("v9",)])
    with patch.object(_core, "con", return_value=fake):
        assert _core.resolve_version("latest") == "v9"


# ── 3) 명시 버전이 env var 보다 우선 ─────────────────────────────────────

def test_explicit_overrides_env_var(monkeypatch):
    """호출자가 명시 → env var 무시."""
    monkeypatch.setenv("DEFAULT_MODEL_VERSION", "v11a_prime")
    # _model_version_exists 호출되면 안 됨 — 명시 버전이라 env 우회.
    with patch.object(_core, "_model_version_exists",
                      side_effect=AssertionError("호출되면 안 됨")):
        assert _core.resolve_version("v9") == "v9"


# ── 4) Fallback 폴백 (inserted_at NULL → date MAX) ─────────────────────────

def test_double_fallback_when_inserted_at_all_null(monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL_VERSION", raising=False)
    # 첫 SQL (inserted_at IS NOT NULL) → None. 두 번째 (date MAX) → v8.
    fake = FakeCon([None, ("v8",)])
    with patch.object(_core, "con", return_value=fake):
        assert _core.resolve_version("latest") == "v8"


def test_raises_when_scores_empty(monkeypatch):
    monkeypatch.delenv("DEFAULT_MODEL_VERSION", raising=False)
    fake = FakeCon([None, None])
    with patch.object(_core, "con", return_value=fake):
        with pytest.raises(RuntimeError):
            _core.resolve_version("latest")
