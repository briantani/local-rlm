"""
Task Routes.

Handles task creation, status checking, and history.
"""

import secrets
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.rlm.services import ConfigService
from src.rlm.services.session_service import Session
from src.web.dependencies import (
    get_config_service,
    get_current_session,
    get_services,
)
from src.web.database import (
    TaskRecord,
    create_task,
    get_task,
    get_tasks_for_session,
)
from src.web.task_runner import run_task_async

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


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
    def from_record(cls, record: TaskRecord) -> "TaskResponse":
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


class TaskListResponse(BaseModel):
    """Response for listing tasks."""
    tasks: list[TaskResponse]
    count: int


class CreateTaskResponse(BaseModel):
    """Response after creating a task."""
    task_id: str
    status: str
    message: str
    websocket_url: str


# =============================================================================
# Routes
# =============================================================================


@router.post("", response_model=CreateTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_and_start_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_current_session),
    config_service: ConfigService = Depends(get_config_service),
):
    """
    Create and start a new task.

    The task runs asynchronously. Use the WebSocket endpoint or
    GET /api/tasks/{task_id} to check status and get results.

    Requires X-Session-ID header with a valid session that has
    the required API keys configured.
    """
    # Validate profile exists
    if not config_service.profile_exists(request.config_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile not found: {request.config_name}. Use GET /api/configs to list available profiles.",
        )

    # Check required API keys
    required = config_service.get_required_providers(request.config_name)
    has_all, missing = session.has_required_keys(required)
    if not has_all:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing API keys for: {', '.join(missing)}. Use PUT /api/sessions/{{id}}/keys to set them.",
        )

    # Generate task ID
    task_id = f"task_{secrets.token_urlsafe(12)}"

    # Create task record
    await create_task(
        task_id=task_id,
        session_id=session.session_id,
        task_text=request.task,
        config_name=request.config_name,
    )

    # Start task in background
    services = get_services()
    task_service = services.get_task_service(session)

    background_tasks.add_task(
        run_task_async,
        task_id=task_id,
        task_text=request.task,
        config_name=request.config_name,
        context_path=request.context_path,
        task_service=task_service,
    )

    return CreateTaskResponse(
        task_id=task_id,
        status="pending",
        message="Task created and queued for execution. Connect to WebSocket for real-time updates.",
        websocket_url=f"/ws/tasks/{task_id}",
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    limit: int = 50,
    session: Session = Depends(get_current_session),
) -> TaskListResponse:
    """
    List tasks for the current session.

    Returns tasks ordered by creation time (newest first).
    """
    records = await get_tasks_for_session(session.session_id, limit=limit)
    tasks = [TaskResponse.from_record(r) for r in records]

    return TaskListResponse(
        tasks=tasks,
        count=len(tasks),
    )


@router.get("/{task_id}", response_model=TaskResultResponse)
async def get_task_by_id(
    task_id: str,
    session: Session = Depends(get_current_session),
) -> TaskResultResponse:
    """
    Get a specific task by ID.

    Only returns tasks belonging to the current session.
    """
    record = await get_task(task_id)

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    # Session isolation: only return tasks for this session
    if record.session_id != session.session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task not found: {task_id}",
        )

    return TaskResultResponse(
        id=record.id,
        session_id=record.session_id,
        task_text=record.task_text,
        config_name=record.config_name,
        status=record.status.value,
        created_at=record.created_at.isoformat(),
        completed_at=record.completed_at.isoformat() if record.completed_at else None,
        result=record.result,
    )
