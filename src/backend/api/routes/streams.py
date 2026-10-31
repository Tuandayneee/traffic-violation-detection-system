"""Live Video Streaming (MJPEG) and Real-time WebSocket Alerting."""

import asyncio
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import cv2
import numpy as np

router = APIRouter(prefix="/api/stream", tags=["Streaming"])

# Active WebSocket subscriber clients
connected_clients: Set[WebSocket] = set()


@router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(websocket: WebSocket):
    """Pushes real-time violation notifications to connected dashboard clients."""
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            # Keep-alive ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)


async def broadcast_alert(alert_payload: dict):
    """Broadcasts a newly detected violation to all open dashboard WebSockets."""
    for client in list(connected_clients):
        try:
            await client.send_json(alert_payload)
        except Exception:
            connected_clients.remove(client)
