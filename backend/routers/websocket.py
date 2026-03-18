import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.broadcast import manager
from backend.services.translation import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{language}")
async def websocket_endpoint(websocket: WebSocket, language: str) -> None:
    """WebSocket endpoint.  Clients connect to ``/ws/<language>`` where
    *language* is one of the supported ISO 639-1 codes (``en``, ``uk``).

    The server will push :class:`~backend.models.message.TextUpdate` payloads
    (as plain text) whenever new translated content is available.

    Clients may also send text frames to the server; those messages are
    treated as source text and broadcast back to all subscribers of the
    same channel (useful for testing without a real audio pipeline).
    """
    if language not in SUPPORTED_LANGUAGES:
        await websocket.close(code=1008, reason=f"Unsupported language: {language}")
        return

    await manager.connect(websocket, language)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo the received text back to all subscribers of this channel
            await manager.broadcast(language, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, language)
        logger.info("WebSocket client disconnected from channel '%s'", language)
