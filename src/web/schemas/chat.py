"""
Chat and messaging schemas.
"""

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    """Response from chat."""
    response: str
    session_id: str


class ChatHistoryResponse(BaseModel):
    """Chat history for a session."""
    messages: list[dict]
    count: int
