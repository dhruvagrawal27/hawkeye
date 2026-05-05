"""WebSocket broadcaster for live alerts."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = structlog.get_logger()
router = APIRouter()

_connections: set[WebSocket] = set()


class AlertBroadcaster:
    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        _connections.add(ws)
        log.info("ws_connected", total=len(_connections))

    def disconnect(self, ws: WebSocket) -> None:
        _connections.discard(ws)
        log.info("ws_disconnected", total=len(_connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: set[WebSocket] = set()
        payload = json.dumps(message, default=str)
        for ws in list(_connections):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            _connections.discard(ws)


alert_broadcaster = AlertBroadcaster()


@router.websocket("/alerts")
async def ws_alerts(websocket: WebSocket):
    await alert_broadcaster.connect(websocket)
    try:
        while True:
            # Keep connection alive; client doesn't need to send anything
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        alert_broadcaster.disconnect(websocket)
    except Exception as exc:
        log.warning("ws_error", error=str(exc))
        alert_broadcaster.disconnect(websocket)
