from __future__ import annotations

import io
import logging
import wave

import numpy as np
from openai import AsyncOpenAI

from backend.config import Settings

logger = logging.getLogger(__name__)


class OpenAITranscriptionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe_segment(self, audio: np.ndarray) -> str:
        wav_bytes = self._to_wav_bytes(audio)
        file_obj = io.BytesIO(wav_bytes)
        file_obj.name = 'segment.wav'

        logger.info('Sending %.2fs audio segment to OpenAI transcription', len(audio) / self.settings.sample_rate)
        transcript = await self.client.audio.transcriptions.create(
            model=self.settings.transcription_model,
            file=file_obj,
            language='no',
            prompt='This is live church speech in Norwegian. Prefer punctuation and clear sentence boundaries.',
        )
        text = (getattr(transcript, 'text', '') or '').strip()
        logger.info('Transcript received: %s', text)
        return text

    def _to_wav_bytes(self, audio: np.ndarray) -> bytes:
        pcm = np.clip(audio, -1.0, 1.0)
        int16_audio = (pcm * 32767).astype(np.int16)
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.settings.sample_rate)
            wav_file.writeframes(int16_audio.tobytes())
        return buffer.getvalue()
