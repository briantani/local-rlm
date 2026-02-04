"""
Consolidated web API schemas.

Provides all Pydantic models for request/response handling across routes.
Import schemas from here instead of defining them in route files.
"""

from src.web.schemas.common import ListResponse, MessageResponse, ErrorResponse
from src.web.schemas.tasks import (
    CreateTaskRequest,
    TaskResponse,
    TaskResultResponse,
    CreateTaskResponse,
)
from src.web.schemas.configs import (
    ProfileSummaryResponse,
    ProfileDetailResponse,
)
from src.web.schemas.sessions import (
    SessionResponse,
    SetApiKeyRequest,
    ApiKeyStatusResponse,
    SetApiKeyResponse,
)
from src.web.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse,
)
from src.web.schemas.export import ShareResponse
from src.web.schemas.templates import (
    CreateTemplateRequest,
    ApplyTemplateResponse,
)

__all__ = [
    # Common
    "ListResponse",
    "MessageResponse",
    "ErrorResponse",
    # Tasks
    "CreateTaskRequest",
    "TaskResponse",
    "TaskResultResponse",
    "CreateTaskResponse",
    # Configs
    "ProfileSummaryResponse",
    "ProfileDetailResponse",
    # Sessions
    "SessionResponse",
    "SetApiKeyRequest",
    "ApiKeyStatusResponse",
    "SetApiKeyResponse",
    # Chat
    "ChatMessageRequest",
    "ChatMessageResponse",
    "ChatHistoryResponse",
    # Export/Share
    "ShareResponse",
    # Templates
    "CreateTemplateRequest",
    "ApplyTemplateResponse",
]
