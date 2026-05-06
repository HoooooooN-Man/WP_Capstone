"""
routers/realtime.py
===================
WebSocket 실시간 시세 라우터.

엔드포인트::

    WS /ws/prices?ticker=005930[,000660]&interval=2

클라이언트 ↔ 서버 메시지 형식 (JSON)::

    server → client:
        { "ticker": "005930", "price": 78500, "ts": "2026-05-05T15:00:01" }
    client → server:
        { "type": "subscribe",   "tickers": ["005930", "000660"] }
        { "type": "unsubscribe", "tickers": ["000660"] }

기본 동작 (시뮬레이션):
    DuckDB prices 테이블의 마지막 종가를 시드로 매 N초마다 ±0.3% 의 무작위 변동을 적용.
    실제 증권사 OpenAPI 가 연결되면 `_price_provider` 만 교체하면 된다.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from datetime import datetime, timezone
from typing import Iterable

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ..services import data as svc

router = APIRouter(prefix="/ws", tags=["realtime"])


# ── Provider 인터페이스 (실시간 피드 교체용) ─────────────────────────────────

async def _seed_prices(tickers: Iterable[str]) -> dict[str, float]:
    """DuckDB prices 의 마지막 종가를 가져와 시드로 사용."""
    seed: dict[str, float] = {}
    for t in tickers:
        try:
            row = svc.get_stock_price(t)
            if row and row.get("close"):
                seed[t.zfill(6)] = float(row["close"])
        except Exception:
            pass
    return seed


async def _simulate_tick(seed: dict[str, float]) -> dict[str, float]:
    """±0.3% 무작위 변동. 실제 피드 도입 전 캡스톤 데모용."""
    out = {}
    for t, last in seed.items():
        delta = last * random.uniform(-0.003, 0.003)
        new_price = max(1.0, last + delta)
        out[t] = round(new_price, 2)
    return out


# ── Connection manager ───────────────────────────────────────────────────────

class _Hub:
    def __init__(self) -> None:
        self.subs: dict[WebSocket, set[str]] = {}

    def subscribe(self, ws: WebSocket, tickers: Iterable[str]) -> None:
        self.subs.setdefault(ws, set()).update(t.zfill(6) for t in tickers if t)

    def unsubscribe(self, ws: WebSocket, tickers: Iterable[str]) -> None:
        if ws in self.subs:
            for t in tickers:
                self.subs[ws].discard(t.zfill(6))

    def disconnect(self, ws: WebSocket) -> None:
        self.subs.pop(ws, None)

    def all_tickers(self) -> set[str]:
        out: set[str] = set()
        for s in self.subs.values():
            out |= s
        return out

    def subscribers_of(self, ticker: str) -> list[WebSocket]:
        return [ws for ws, s in self.subs.items() if ticker in s]


hub = _Hub()

# 환경변수
TICK_INTERVAL_SECONDS = float(os.getenv("WS_TICK_INTERVAL_SECONDS", "2.0"))
WS_MAX_TICKERS = int(os.getenv("WS_MAX_TICKERS", "20"))


# ── 백그라운드 브로드캐스터 ──────────────────────────────────────────────────

_broadcaster_task: asyncio.Task | None = None


async def _broadcaster_loop() -> None:
    """모든 구독 ticker 를 한 번에 시뮬레이트 후 구독자에게 분배."""
    seed: dict[str, float] = {}
    while True:
        try:
            tickers = hub.all_tickers()
            if not tickers:
                await asyncio.sleep(TICK_INTERVAL_SECONDS)
                continue

            # 새 ticker 가 들어왔으면 시드 업데이트
            new_ones = tickers - set(seed.keys())
            if new_ones:
                seed.update(await _seed_prices(new_ones))

            ticks = await _simulate_tick({t: seed[t] for t in tickers if t in seed})
            seed.update(ticks)

            ts = datetime.now(timezone.utc).isoformat()
            for ticker, price in ticks.items():
                payload = json.dumps({"ticker": ticker, "price": price, "ts": ts})
                for ws in list(hub.subscribers_of(ticker)):
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        hub.disconnect(ws)
        except asyncio.CancelledError:
            raise
        except Exception:
            # broadcaster 가 죽으면 안 되므로 silently 계속
            pass

        await asyncio.sleep(TICK_INTERVAL_SECONDS)


async def ensure_broadcaster_running() -> None:
    """첫 WS 연결 시 lazy 시작."""
    global _broadcaster_task
    if _broadcaster_task is None or _broadcaster_task.done():
        _broadcaster_task = asyncio.create_task(_broadcaster_loop())


# ── WebSocket 엔드포인트 ─────────────────────────────────────────────────────

@router.websocket("/prices")
async def ws_prices(
    websocket: WebSocket,
    ticker: str | None = Query(None, description="콤마 구분 티커 (예: 005930,000660)"),
):
    await websocket.accept()
    await ensure_broadcaster_running()

    initial: list[str] = []
    if ticker:
        initial = [t.strip() for t in ticker.split(",") if t.strip()][:WS_MAX_TICKERS]
        hub.subscribe(websocket, initial)
        # 초기 스냅샷 1회 전송
        seed = await _seed_prices(initial)
        ts = datetime.now(timezone.utc).isoformat()
        for t, p in seed.items():
            await websocket.send_text(json.dumps({
                "ticker": t, "price": p, "ts": ts, "snapshot": True,
            }))

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                payload = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "invalid json"}))
                continue

            mtype = payload.get("type")
            tickers = payload.get("tickers", []) or []
            if not isinstance(tickers, list):
                continue

            # 한 연결당 최대 구독 수 제한
            if mtype == "subscribe":
                current = hub.subs.get(websocket, set())
                allowed = list(tickers)[: max(0, WS_MAX_TICKERS - len(current))]
                hub.subscribe(websocket, allowed)
            elif mtype == "unsubscribe":
                hub.unsubscribe(websocket, tickers)
            else:
                await websocket.send_text(json.dumps({"error": "unknown type"}))

    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(websocket)
