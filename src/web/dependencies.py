"""
FastAPI Dependency Injection.

Provides shared instances of services for request handlers.
"""

from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status

from src.rlm.services import ConfigService, SessionService, TaskService
from src.rlm.services.session_service import Session


@dataclass
class Services:
    """Container for all application services."""
    session_service: SessionService
    config_service: ConfigService

    def get_task_service(self, session: Session) -> TaskService:
        """Create a TaskService with the given session."""
        return TaskService(self.config_service, session)


@lru_cache()
def get_services() -> Services:
    """
    Get singleton services container.

    Uses lru_cache to ensure single instance across requests.
    """
    return Services(
        session_service=SessionService(),
        config_service=ConfigService(),
    )


def get_session_service(
    services: Services = Depends(get_services)
) -> SessionService:
    """Get the session service."""
    return services.session_service


def get_config_service(
    services: Services = Depends(get_services)
) -> ConfigService:
    """Get the config service."""
    return services.config_service


async def get_current_session(
    x_session_id: str = Header(..., description="Session ID from POST /api/sessions"),
    services: Services = Depends(get_services),
) -> Session:
    """
    Get the current session from the X-Session-ID header.

    Raises:
        HTTPException: If session not found or invalid
    """
    session = services.session_service.get_session(x_session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Create a new session via POST /api/sessions",
        )
    return session


async def get_task_service(
    session: Session = Depends(get_current_session),
    services: Services = Depends(get_services),
) -> TaskService:
    """Get a TaskService configured with the current session."""
    return services.get_task_service(session)
