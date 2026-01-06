"""
RLM (Recursive Language Model) Core Library.

This package provides the core business logic for the RLM Agent,
designed to be used by both CLI and Web interfaces.

Phase 12 introduces the service layer pattern:
- TaskService: Agent orchestration and execution
- ConfigService: Profile management and loading
- SessionService: Session and API key management (in-memory only)
"""

from src.rlm.services.task_service import TaskService, TaskResult
from src.rlm.services.config_service import ConfigService, ProfileSummary
from src.rlm.services.session_service import SessionService, Session

__all__ = [
    "TaskService",
    "TaskResult",
    "ConfigService",
    "ProfileSummary",
    "SessionService",
    "Session",
]
