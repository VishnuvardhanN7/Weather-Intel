"""
WebSocket API Endpoint for PS-26069.

Provides /ws/weather WebSocket route for live client subscriptions to sink-accepted weather events.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/weather")
async def websocket_weather_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time verified weather event broadcasts.
    Clients connect to /ws/weather to receive events matching alertness_score > 0.90.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and accept incoming messages/pings
            data = await websocket.receive_text()
            logger.debug("Received WebSocket text from client: %s", data[:50])
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket error for client connection: %s", exc)
        manager.disconnect(websocket)
