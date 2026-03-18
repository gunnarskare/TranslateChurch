import asyncio
import logging
from typing import Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages to them.

    Clients can subscribe to one or more language channels (e.g. "en", "uk").
    A broadcast to a channel only reaches subscribers of that channel.

    An :class:`asyncio.Lock` serialises all mutations to ``_channels`` so
    that concurrent broadcasts cannot race when removing stale connections.
    """

    def __init__(self) -> None:
        # Map from language channel → set of connected WebSockets
        self._channels: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, language: str) -> None:
        """Accept the connection and register it under the given language channel."""
        await websocket.accept()
        async with self._lock:
            self._channels.setdefault(language, set()).add(websocket)
        logger.info("Client connected to channel '%s'", language)

    async def disconnect(self, websocket: WebSocket, language: str) -> None:
        """Remove the connection from the channel registry."""
        async with self._lock:
            channel = self._channels.get(language, set())
            channel.discard(websocket)
            if not channel:
                self._channels.pop(language, None)
        logger.info("Client disconnected from channel '%s'", language)

    async def broadcast(self, language: str, text: str) -> None:
        """Send *text* to every client subscribed to *language*."""
        async with self._lock:
            subscribers: List[WebSocket] = list(self._channels.get(language, set()))

        if not subscribers:
            return

        results = await asyncio.gather(
            *[ws.send_text(text) for ws in subscribers],
            return_exceptions=True,
        )

        # Remove any connections that failed during the send
        failed = [ws for ws, res in zip(subscribers, results) if isinstance(res, Exception)]
        for ws in failed:
            logger.warning("Removing failed connection from channel '%s'", language)
            await self.disconnect(ws, language)

    async def broadcast_all(self, text: str) -> None:
        """Send *text* to every connected client regardless of channel."""
        async with self._lock:
            languages = list(self._channels.keys())
        for language in languages:
            await self.broadcast(language, text)


# Module-level singleton shared across the application
manager = ConnectionManager()
