from pydantic import BaseModel


class TextUpdate(BaseModel):
    """A live text update pushed to connected WebSocket clients."""

    language: str
    text: str
