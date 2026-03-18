from __future__ import annotations

from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


SupportedLanguage = Literal['no', 'en', 'uk']


class TranslationBundle(BaseModel):
    no: str = Field(..., description='Original Norwegian transcript')
    en: str = Field(..., description='English translation')
    uk: str = Field(..., description='Ukrainian translation')


class LiveMessage(BaseModel):
    type: Literal['translation_update'] = 'translation_update'
    segment_id: str
    source_language: SupportedLanguage = 'no'
    translations: TranslationBundle
    created_at: datetime


class DeviceInfo(BaseModel):
    index: int
    name: str
    max_input_channels: int
    default_samplerate: float


class ServiceStatus(BaseModel):
    running: bool
    test_mode: bool
    selected_device: Optional[DeviceInfo] = None


class ManualTranscriptRequest(BaseModel):
    text: str = Field(..., min_length=1, description='A manual Norwegian transcript used in test mode.')


class ManualSegmentRequest(BaseModel):
    transcript: str = Field(..., min_length=1, description='Recognized Norwegian transcript.')


class HealthResponse(BaseModel):
    status: Literal['ok'] = 'ok'
    audio: ServiceStatus
    websocket_clients: Dict[str, int]
