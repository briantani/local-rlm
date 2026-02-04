"""
Task-related schemas for the web API.
"""

from typing import Any
from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    """Request to create and start a task."""
    task: str = Field(..., description="The task/query to execute", min_length=1)
    config_name: str = Field(..., description="Configuration profile name")
    context_path: str | None = Field(
        default=None,
        description="Optional path to directory with context files"
    )


class TaskResponse(BaseModel):
    """Response with task information."""
    id: str
    session_id: str
    task_text: str
    config_name: str
    status: str
    created_at: str
    completed_at: str | None = None

    @classmethod
    def from_record(cls, record: Any) -> "TaskResponse":
        """Create from database TaskRecord."""
        return cls(
            id=record.id,
            session_id=record.session_id,
            task_text=record.task_text,
            config_name=record.config_name,
            status=record.status.value,
            created_at=record.created_at.isoformat(),
            completed_at=record.completed_at.isoformat() if record.completed_at else None,
        )


class TaskResultResponse(TaskResponse):
    """Response with full task result."""
    result: dict[str, Any] | None = None


class CreateTaskResponse(BaseModel):
    """Response after creating a task."""
    task_id: str
    status: str
    message: str
    websocket_url: str
