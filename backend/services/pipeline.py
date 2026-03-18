from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from backend.config import Settings
from backend.models import LiveMessage, ServiceStatus, TranslationBundle
from backend.services.audio_input import AudioInputService
from backend.services.broadcaster import manager
from backend.services.transcribe import OpenAITranscriptionService
from backend.services.translate import OpenAITranslationService
from backend.services.vad import VoiceActivityDetector

logger = logging.getLogger(__name__)


class TranslationPipeline:
    def __init__(
        self,
        settings: Settings,
        audio_input: AudioInputService,
        transcription_service: OpenAITranscriptionService,
        translation_service: OpenAITranslationService,
    ) -> None:
        self.settings = settings
        self.audio_input = audio_input
        self.transcription_service = transcription_service
        self.translation_service = translation_service
        self.vad = VoiceActivityDetector(
            sample_rate=settings.sample_rate,
            energy_threshold=settings.energy_threshold,
            silence_timeout_seconds=settings.silence_timeout_seconds,
            minimum_speech_seconds=settings.minimum_speech_seconds,
            maximum_segment_seconds=settings.maximum_segment_seconds,
        )
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        await self.audio_input.start()
        if self.settings.test_mode:
            self._running = True
            logger.info('Pipeline started in TEST_MODE; waiting for manual transcript injection')
            return
        self._task = asyncio.create_task(self._run_loop(), name='translation-pipeline')
        self._running = True
        logger.info('Translation pipeline started')

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self.audio_input.stop()

    async def _run_loop(self) -> None:
        while True:
            chunk = await self.audio_input.read_chunk()
            result = self.vad.process_chunk(chunk.data)
            if result is None:
                continue
            try:
                await self._handle_segment(result.audio)
            except Exception:
                logger.exception('Failed to process a detected speech segment')

    async def process_manual_transcript(self, text: str) -> LiveMessage | None:
        cleaned = text.strip()
        if len(cleaned) < self.settings.minimum_transcript_characters:
            logger.info('Manual transcript ignored because it is too short')
            return None
        try:
            return await self._publish_translations(cleaned)
        except Exception:
            logger.exception('Failed to publish manual transcript')
            raise

    async def _handle_segment(self, audio) -> None:  # type: ignore[no-untyped-def]
        transcript = (await self.transcription_service.transcribe_segment(audio)).strip()
        if len(transcript) < self.settings.minimum_transcript_characters:
            logger.info('Segment ignored because transcript was too short: %r', transcript)
            return
        await self._publish_translations(transcript)

    async def _publish_translations(self, transcript: str) -> LiveMessage:
        translations = await self.translation_service.translate_bundle(transcript)
        message = LiveMessage(
            segment_id=str(uuid4()),
            translations=TranslationBundle(no=transcript, en=translations['en'], uk=translations['uk']),
            created_at=datetime.now(timezone.utc),
        )
        await manager.broadcast_translation(message)
        logger.info('Translations sent for segment %s', message.segment_id)
        return message

    def status(self) -> ServiceStatus:
        return ServiceStatus(
            running=self._running,
            test_mode=self.settings.test_mode,
            selected_device=self.audio_input.get_selected_device(),
        )
