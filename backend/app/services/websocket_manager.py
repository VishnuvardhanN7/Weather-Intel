"""
WebSocket Connection Manager for PS-26069.

Manages active WebSocket connections and broadcasts verified weather events
to all connected dashboard clients in real time.
"""

import logging
from typing import Set, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket client connections and safe real-time event broadcasting."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Accept new client WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket client connected. Active clients count: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Safely remove a disconnected client WebSocket."""
        self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected. Remaining active clients count: %d", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message dictionary to all active connected WebSocket clients.
        If a client fails or disconnects during send, remove it safely without crashing processing.
        """
        if not self.active_connections:
            logger.debug("No WebSocket clients connected for broadcast.")
            return

        logger.info("Broadcasting event '%s' to %d active WebSocket client(s)",
                    message.get("event_id"), len(self.active_connections))

        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.warning("Failed to send message to WebSocket client (%s). Marking for removal.", exc)
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()
