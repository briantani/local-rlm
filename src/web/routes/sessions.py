"""
Session Routes.

Handles session creation and API key management.
API keys are stored only in memory, never persisted.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.rlm.services import SessionService
from src.web.dependencies import get_session_service

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class SessionResponse(BaseModel):
    """Response for session creation."""
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(default="Session created successfully")


class SetApiKeyRequest(BaseModel):
    """Request to set an API key."""
    provider: str = Field(..., description="Provider name (gemini, openai, anthropic)")
    api_key: str = Field(..., description="The API key value", min_length=1)


class ApiKeyStatusResponse(BaseModel):
    """Response showing which API keys are configured."""
    configured_providers: list[str] = Field(
        ...,
        description="List of providers with API keys set"
    )
    missing_for_profile: list[str] = Field(
        default=[],
        description="Providers needed for the specified profile but not configured"
    )


class SetApiKeyResponse(BaseModel):
    """Response after setting an API key."""
    success: bool
    provider: str
    message: str


# =============================================================================
# Routes
# =============================================================================


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """
    Create a new session.

    Returns a session_id that must be included in the X-Session-ID header
    for subsequent requests. Sessions are stored in memory only.
    """
    session = session_service.create_session()
    return SessionResponse(
        session_id=session.session_id,
        message="Session created. Include this session_id in X-Session-ID header for all requests.",
    )


@router.put("/{session_id}/keys", response_model=SetApiKeyResponse)
async def set_api_key(
    session_id: str,
    request: SetApiKeyRequest,
    session_service: SessionService = Depends(get_session_service),
) -> SetApiKeyResponse:
    """
    Set an API key for a provider.

    The API key is stored ONLY in memory and will be lost when the server
    restarts or the session expires. Keys are never written to disk.

    Supported providers: gemini, openai, anthropic
    """
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    # Validate provider
    valid_providers = {"gemini", "openai", "anthropic", "ollama"}
    provider = request.provider.lower()
    if provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider '{request.provider}'. Valid: {', '.join(valid_providers)}",
        )

    # Ollama doesn't need an API key
    if provider == "ollama":
        return SetApiKeyResponse(
            success=True,
            provider=provider,
            message="Ollama is a local provider and doesn't require an API key.",
        )

    session.set_api_key(provider, request.api_key)

    return SetApiKeyResponse(
        success=True,
        provider=provider,
        message=f"API key for {provider} set successfully. Key is stored in memory only.",
    )


@router.get("/{session_id}/keys/status", response_model=ApiKeyStatusResponse)
async def get_api_key_status(
    session_id: str,
    profile: str | None = None,
    session_service: SessionService = Depends(get_session_service),
) -> ApiKeyStatusResponse:
    """
    Check which API keys are configured for a session.

    Optionally specify a profile name to see which keys are missing
    for that specific configuration.
    """
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    configured = session.get_configured_providers()

    missing = []
    if profile:
        # Import here to avoid circular imports
        from src.web.dependencies import get_services
        services = get_services()
        required = services.config_service.get_required_providers(profile)
        _, missing = session.has_required_keys(required)

    return ApiKeyStatusResponse(
        configured_providers=configured,
        missing_for_profile=missing,
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
):
    """
    Delete a session and clear all its API keys from memory.
    """
    success = session_service.delete_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    return {"success": True, "message": "Session deleted and all API keys cleared from memory."}
