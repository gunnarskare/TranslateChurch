from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.broadcaster import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=['websocket'])
SUPPORTED_LANGUAGES = {'no', 'en', 'uk'}


@router.websocket('/ws/{language}')
async def websocket_endpoint(websocket: WebSocket, language: str) -> None:
    if language not in SUPPORTED_LANGUAGES:
        await websocket.close(code=1008, reason=f'Unsupported language: {language}')
        return

    await manager.connect(websocket, language)
    try:
        while True:
            # We keep the socket open and ignore client messages for now.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, language)
        logger.info('WebSocket client disconnected from language=%s', language)
