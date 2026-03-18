from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.routers.api import router as api_router
from backend.routers.websocket import router as websocket_router
from backend.services.audio_input import AudioInputService
from backend.services.pipeline import TranslationPipeline
from backend.services.transcribe import OpenAITranscriptionService
from backend.services.translate import OpenAITranslationService

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s %(levelname)-8s %(name)s - %(message)s',
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / 'frontend'


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.openai_api_key and not settings.test_mode:
        raise RuntimeError('OPENAI_API_KEY is required unless TEST_MODE=true.')

    audio_input = AudioInputService(settings)
    transcription_service = OpenAITranscriptionService(settings)
    translation_service = OpenAITranslationService(settings)
    pipeline = TranslationPipeline(settings, audio_input, transcription_service, translation_service)
    app.state.pipeline = pipeline
    await pipeline.start()
    try:
        yield
    finally:
        await pipeline.stop()


app = FastAPI(
    title=settings.app_name,
    version='0.1.0',
    description='Live church translation MVP with Norwegian transcription and browser streaming.',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(api_router)
app.include_router(websocket_router)
app.mount('/static', StaticFiles(directory=FRONTEND_DIR), name='static')


@app.get('/', include_in_schema=False)
async def frontend() -> FileResponse:
    return FileResponse(FRONTEND_DIR / 'index.html')


if __name__ == '__main__':
    uvicorn.run('backend.main:app', host=settings.host, port=settings.port, reload=True)
