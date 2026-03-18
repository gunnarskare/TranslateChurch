from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.config import Settings, get_settings
from backend.models import DeviceInfo, HealthResponse, ManualSegmentRequest
from backend.services.broadcaster import manager
from backend.services.pipeline import TranslationPipeline

router = APIRouter(prefix='/api', tags=['api'])


def _pipeline_from_request(request: Request) -> TranslationPipeline:
    return request.app.state.pipeline


@router.get('/health', response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    pipeline = _pipeline_from_request(request)
    return HealthResponse(status='ok', audio=pipeline.status(), websocket_clients=await manager.counts())


@router.get('/audio/devices', response_model=list[DeviceInfo])
async def list_audio_devices(request: Request) -> list[DeviceInfo]:
    pipeline = _pipeline_from_request(request)
    return pipeline.audio_input.list_input_devices()


@router.post('/test/segment')
async def post_test_segment(
    payload: ManualSegmentRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    if not settings.test_mode:
        raise HTTPException(status_code=403, detail='Manual test mode is disabled. Set TEST_MODE=true to use this endpoint.')
    pipeline = _pipeline_from_request(request)
    message = await pipeline.process_manual_transcript(payload.transcript)
    if message is None:
        raise HTTPException(status_code=400, detail='Transcript was too short to publish.')
    return {'published': True, 'segment_id': message.segment_id}
