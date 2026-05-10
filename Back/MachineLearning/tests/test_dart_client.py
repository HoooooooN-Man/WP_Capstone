"""
test_dart_client.py
===================
차차기 W5 — dart_client + dart_ingest 의 *순수 함수* 단위 테스트.
HTTP 호출은 mock — 외부 네트워크·API key 의존 0.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dart_client import (
    DART_STATUS_NO_DATA,
    DART_STATUS_OK,
    DartConfig,
    DartError,
    PBLNTF_TY_CODES,
    _validate_status,
    iter_disclosures,
    list_disclosures,
)
from dart_ingest import filter_listed, normalize_row


# ── DartConfig ──────────────────────────────────────────────────────────────

def test_config_from_env_ok(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "abc123")
    cfg = DartConfig.from_env()
    assert cfg.api_key == "abc123"


def test_config_from_env_missing(monkeypatch):
    monkeypatch.delenv("DART_API_KEY", raising=False)
    with pytest.raises(DartError) as exc:
        DartConfig.from_env()
    assert "DART_API_KEY" in str(exc.value)


# ── _validate_status ───────────────────────────────────────────────────────

def test_validate_status_ok_passthrough():
    p = {"status": DART_STATUS_OK, "list": [{"a": 1}]}
    assert _validate_status(p) is p


def test_validate_status_no_data_normalizes_list():
    """013 → 빈 list 자동 부여. caller 분기 안 해도 됨."""
    p = {"status": DART_STATUS_NO_DATA, "message": "no data"}
    out = _validate_status(p)
    assert out["list"] == []


def test_validate_status_error_raises():
    for bad in ("010", "020", "100", "800"):
        with pytest.raises(DartError) as exc:
            _validate_status({"status": bad, "message": "fail"})
        assert exc.value.status == bad


# ── list_disclosures (mock HTTP) ────────────────────────────────────────────

def _mock_response(status_code=200, json_payload=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_payload or {"status": DART_STATUS_OK, "list": []}
    r.text = ""
    return r


def test_list_disclosures_passes_params(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "k")
    cfg = DartConfig(api_key="k", rate_limit_sec=0.0, timeout_sec=1, max_retries=1)
    sess = MagicMock()
    sess.get.return_value = _mock_response(json_payload={
        "status": DART_STATUS_OK, "list": [{"corp_code": "X"}]
    })
    out = list_disclosures(config=cfg, bgn_de="20260101", end_de="20260101",
                           corp_code="C", pblntf_ty="B", session=sess)
    args, kwargs = sess.get.call_args
    assert "list.json" in args[0]
    p = kwargs["params"]
    assert p["crtfc_key"] == "k"
    assert p["bgn_de"]    == "20260101"
    assert p["end_de"]    == "20260101"
    assert p["corp_code"] == "C"
    assert p["pblntf_ty"] == "B"
    # caller 가 pblntf_ty 명시 시 응답 row 에 자동 주입 (DART list.json 응답 자체엔 없음).
    assert out["list"] == [{"corp_code": "X", "pblntf_ty": "B"}]


def test_pblntf_ty_injection_does_not_overwrite():
    """이미 row 에 pblntf_ty 가 있으면 덮어쓰지 않음 (setdefault 동작)."""
    cfg = DartConfig(api_key="k", rate_limit_sec=0.0, timeout_sec=1, max_retries=1)
    sess = MagicMock()
    sess.get.return_value = _mock_response(json_payload={
        "status": DART_STATUS_OK, "list": [{"corp_code": "X", "pblntf_ty": "C"}]
    })
    out = list_disclosures(config=cfg, bgn_de="20260101", end_de="20260101",
                           pblntf_ty="B", session=sess)
    assert out["list"][0]["pblntf_ty"] == "C"


def test_list_disclosures_clamps_page_size(monkeypatch):
    cfg = DartConfig(api_key="k", rate_limit_sec=0.0, timeout_sec=1, max_retries=1)
    sess = MagicMock()
    sess.get.return_value = _mock_response()
    list_disclosures(config=cfg, bgn_de="20260101", end_de="20260101",
                     page_count=999, session=sess)
    p = sess.get.call_args.kwargs["params"]
    assert p["page_count"] == 100   # MAX clamp


def test_http_500_then_recovery(monkeypatch):
    cfg = DartConfig(api_key="k", rate_limit_sec=0.0, timeout_sec=1, max_retries=3)
    sess = MagicMock()
    sess.get.side_effect = [
        _mock_response(status_code=500),
        _mock_response(json_payload={"status": DART_STATUS_OK, "list": [{"x": 1}]}),
    ]
    out = list_disclosures(config=cfg, bgn_de="20260101", end_de="20260101",
                           session=sess)
    assert out["list"] == [{"x": 1}]
    assert sess.get.call_count == 2


def test_http_retries_exhausted(monkeypatch):
    cfg = DartConfig(api_key="k", rate_limit_sec=0.0, timeout_sec=1, max_retries=2)
    sess = MagicMock()
    sess.get.return_value = _mock_response(status_code=503)
    with pytest.raises(DartError):
        list_disclosures(config=cfg, bgn_de="20260101", end_de="20260101", session=sess)
    assert sess.get.call_count == 2


# ── iter_disclosures pagination ─────────────────────────────────────────────

def test_iter_paginates_until_empty(monkeypatch):
    cfg = DartConfig(api_key="k", rate_limit_sec=0.0, timeout_sec=1, max_retries=1)
    sess = MagicMock()
    sess.get.side_effect = [
        _mock_response(json_payload={"status": DART_STATUS_OK,
                                     "list": [{"r": 1}, {"r": 2}],
                                     "page_no": 1, "total_page": 2}),
        _mock_response(json_payload={"status": DART_STATUS_OK,
                                     "list": [{"r": 3}],
                                     "page_no": 2, "total_page": 2}),
    ]
    out = list(iter_disclosures(config=cfg, bgn_de="20260101", end_de="20260101",
                                 session=sess))
    assert [r["r"] for r in out] == [1, 2, 3]


def test_iter_stops_on_no_data(monkeypatch):
    """status=013 (NoData) → 빈 list → 종료."""
    cfg = DartConfig(api_key="k", rate_limit_sec=0.0, timeout_sec=1, max_retries=1)
    sess = MagicMock()
    sess.get.return_value = _mock_response(json_payload={
        "status": DART_STATUS_NO_DATA, "message": "no data",
    })
    out = list(iter_disclosures(config=cfg, bgn_de="20260101", end_de="20260101",
                                 session=sess))
    assert out == []


# ── PBLNTF_TY_CODES ─────────────────────────────────────────────────────────

def test_pblntf_ty_codes_complete():
    assert "A" in PBLNTF_TY_CODES
    assert PBLNTF_TY_CODES["A"] == "정기공시"
    assert PBLNTF_TY_CODES["B"] == "주요사항보고"
    assert len(PBLNTF_TY_CODES) == 10


# ── ingest: normalize_row ───────────────────────────────────────────────────

def test_normalize_row_strips_and_keeps_rcept_no():
    r = {
        "rcept_no": "  20260102000123  ",
        "corp_code": "00000001",
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "rcept_dt": "20260102",
        "report_nm": "주요사항보고서",
        "pblntf_ty": "B",
        "pblntf_detail_ty": "B001",
        "flr_nm": "",
        "rm": None,
    }
    out = normalize_row(r)
    assert out["rcept_no"]   == "20260102000123"
    assert out["stock_code"] == "005930"
    assert out["flr_nm"]     is None      # 공백 → None
    assert out["rm"]         is None


def test_normalize_row_skips_missing_rcept_no():
    assert normalize_row({"rcept_no": "  "}) is None
    assert normalize_row({}) is None


def test_normalize_row_handles_none_fields():
    out = normalize_row({"rcept_no": "X", "corp_name": None})
    assert out["corp_name"] is None


# ── ingest: filter_listed ───────────────────────────────────────────────────

def test_filter_listed_keeps_6_digit_codes():
    rows = [
        {"stock_code": "005930"},
        {"stock_code": "00059"},     # 5자리 — drop
        {"stock_code": "abcdef"},     # 비숫자 — drop
        {"stock_code": ""},           # 빈 — drop
        {"stock_code": "066570"},
        {},                            # key 없음 — drop
    ]
    out = list(filter_listed(rows))
    assert [r["stock_code"] for r in out] == ["005930", "066570"]
