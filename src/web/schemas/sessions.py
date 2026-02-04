"""
Session and API key management schemas.
"""

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """Session information."""
    session_id: str
    created_at: str


class SetApiKeyRequest(BaseModel):
    """Request to set an API key for a provider."""
    provider: str  # gemini, openai
    api_key: str


class ApiKeyStatusResponse(BaseModel):
    """Status of configured API keys."""
    gemini: bool
    openai: bool
    ollama: bool


class SetApiKeyResponse(BaseModel):
    """Response after setting an API key."""
    message: str
    provider: str
    status: ApiKeyStatusResponse
