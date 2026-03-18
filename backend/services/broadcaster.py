from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import DefaultDict, Dict, List, Set

from fastapi import WebSocket

from backend.models import LiveMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._channels: DefaultDict[str, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._latest_message: LiveMessage | None = None

    async def connect(self, websocket: WebSocket, language: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._channels[language].add(websocket)
            latest = self._latest_message
        logger.info('WebSocket client connected for language=%s', language)
        if latest is not None:
            await websocket.send_text(self.serialize_for_language(latest, language))

    async def disconnect(self, websocket: WebSocket, language: str) -> None:
        async with self._lock:
            channel = self._channels.get(language)
            if channel is not None:
                channel.discard(websocket)
                if not channel:
                    self._channels.pop(language, None)
        logger.info('WebSocket client disconnected for language=%s', language)

    async def broadcast_translation(self, message: LiveMessage) -> None:
        async with self._lock:
            self._latest_message = message
            snapshot = {language: list(clients) for language, clients in self._channels.items()}

        for language, clients in snapshot.items():
            if not clients:
                continue
            payload = self.serialize_for_language(message, language)
            results = await asyncio.gather(
                *[client.send_text(payload) for client in clients],
                return_exceptions=True,
            )
            for client, result in zip(clients, results):
                if isinstance(result, Exception):
                    logger.warning('Removing stale websocket for language=%s: %s', language, result)
                    await self.disconnect(client, language)

    @staticmethod
    def serialize_for_language(message: LiveMessage, language: str) -> str:
        if language not in {'no', 'en', 'uk'}:
            language = 'en'
        payload = {
            'type': message.type,
            'segment_id': message.segment_id,
            'language': language,
            'text': getattr(message.translations, language),
            'translations': message.translations.model_dump(),
            'source_language': message.source_language,
            'created_at': message.created_at.isoformat(),
        }
        return json.dumps(payload)

    async def counts(self) -> Dict[str, int]:
        async with self._lock:
            return {language: len(clients) for language, clients in self._channels.items()}


manager = ConnectionManager()
