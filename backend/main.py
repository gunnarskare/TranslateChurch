"""TranslateChurch backend – FastAPI application entry point.

Start the development server with::

    uvicorn backend.main:app --reload

or use the convenience script::

    python -m backend.main
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.routers.websocket import router as ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s – %(message)s",
)

app = FastAPI(
    title="TranslateChurch",
    description=(
        "Real-time AI translation system for churches. "
        "Streams live translated text to mobile devices via WebSockets."
    ),
    version="0.1.0",
)

# Allow all origins during development; tighten this for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST + WebSocket routes
app.include_router(ws_router)

# Serve the minimal frontend from the /frontend directory
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", include_in_schema=False)
async def serve_frontend() -> FileResponse:
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health() -> dict:
    """Liveness probe – returns ``{"status": "ok"}``."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
