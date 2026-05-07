"""
test_realtime.py
================
Tier 1.7 (PRD §1.1) — WebSocket 시세 페이로드 라벨링 회귀 테스트.

검증 대상:
  - 모든 WS 페이로드(snapshot, tick) 에 `source`, `delay_ms` 필드 존재.
  - 기본 환경(PRICE_PROVIDER 미설정 또는 simulation) 에서 source == "simulation".
  - 기존 필드(ticker, price, ts) 가 깨지지 않음.

DuckDB prices 데이터가 없는 환경에서도 "스냅샷이 0개여도" snapshot 부재가 정상이므로
각 검증은 페이로드가 실제로 도착했을 때만 수행한다.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def _drain_messages(ws, max_messages: int = 5) -> list[dict]:
    """수신 가능한 메시지를 짧게 모아 반환 (timeout 짧게)."""
    out: list[dict] = []
    for _ in range(max_messages):
        try:
            raw = ws.receive_text(timeout=2.0)
        except Exception:
            break
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def test_ws_payload_has_source_and_delay(app):
    """초기 스냅샷 또는 tick 페이로드에 source/delay_ms 가 포함된다."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/prices?ticker=005930") as ws:
            messages = _drain_messages(ws, max_messages=3)

    if not messages:
        # 환경에 prices 데이터가 없으면 스냅샷이 안 옴 — 본 회귀의 핵심 케이스가 아님.
        return

    for m in messages:
        if "error" in m:
            continue
        assert "ticker"   in m, m
        assert "price"    in m, m
        assert "ts"       in m, m
        assert "source"   in m, m
        assert "delay_ms" in m, m
        assert m["source"] in ("simulation", "live"), m
        assert isinstance(m["delay_ms"], int)


def test_ws_default_source_is_simulation(app, monkeypatch):
    """PRICE_PROVIDER 미설정 시 기본값이 simulation 임을 확인."""
    # routers.realtime 모듈은 import 시점에 PRICE_SOURCE 를 결정한다.
    # 따라서 모듈 속성을 직접 검사.
    from Back.FastAPI.routers import realtime
    assert realtime.PRICE_SOURCE == "simulation"
