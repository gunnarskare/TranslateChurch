from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv('APP_NAME', 'TranslateChurch')
    host: str = os.getenv('HOST', '0.0.0.0')
    port: int = int(os.getenv('PORT', '8000'))
    log_level: str = os.getenv('LOG_LEVEL', 'INFO')

    openai_api_key: str = os.getenv('OPENAI_API_KEY', '')
    transcription_model: str = os.getenv('OPENAI_TRANSCRIPTION_MODEL', 'gpt-4o-mini-transcribe')
    translation_model: str = os.getenv('OPENAI_TRANSLATION_MODEL', 'gpt-4o-mini')

    sample_rate: int = int(os.getenv('AUDIO_SAMPLE_RATE', '16000'))
    channels: int = int(os.getenv('AUDIO_CHANNELS', '1'))
    dtype: str = os.getenv('AUDIO_DTYPE', 'float32')
    block_duration_ms: int = int(os.getenv('AUDIO_BLOCK_DURATION_MS', '100'))
    device_name: Optional[str] = os.getenv('AUDIO_DEVICE_NAME') or None
    device_index: Optional[int] = int(os.getenv('AUDIO_DEVICE_INDEX')) if os.getenv('AUDIO_DEVICE_INDEX') else None

    energy_threshold: float = float(os.getenv('VAD_ENERGY_THRESHOLD', '0.015'))
    silence_timeout_seconds: float = float(os.getenv('VAD_SILENCE_TIMEOUT_SECONDS', '1.0'))
    minimum_speech_seconds: float = float(os.getenv('VAD_MINIMUM_SPEECH_SECONDS', '0.7'))
    minimum_transcript_characters: int = int(os.getenv('MINIMUM_TRANSCRIPT_CHARACTERS', '3'))
    maximum_segment_seconds: float = float(os.getenv('MAXIMUM_SEGMENT_SECONDS', '30.0'))

    frontend_title: str = os.getenv('FRONTEND_TITLE', 'TranslateChurch Live Translation')
    allowed_origins_raw: str = os.getenv('ALLOWED_ORIGINS', '*')

    test_mode: bool = os.getenv('TEST_MODE', 'false').lower() in {'1', 'true', 'yes', 'on'}

    @property
    def allowed_origins(self) -> list[str]:
        if self.allowed_origins_raw.strip() == '*':
            return ['*']
        return [item.strip() for item in self.allowed_origins_raw.split(',') if item.strip()]

    @property
    def block_size(self) -> int:
        return max(1, int(self.sample_rate * (self.block_duration_ms / 1000)))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
