"""
Share API Routes and Views.

Handles creating and viewing shareable task results.
Phase 17: Canvas & Export Features
"""

import logging
import secrets
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from src.web.database import create_share_token, get_task_by_share_token, get_task

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="src/web/templates")


class ShareResponse(BaseModel):
    """Response after creating a share link."""
    share_token: str
    share_url: str


@router.post("/api/tasks/{task_id}/share", response_model=ShareResponse)
async def create_share_link(task_id: str):
    """
    Create a shareable link for a task.

    Args:
        task_id: Task identifier

    Returns:
        Share token and URL
    """
    # Verify task exists and is completed
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status.value not in ("completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail="Can only share completed or failed tasks"
        )

    # Generate secure token
    token = secrets.token_urlsafe(32)

    # Store in database
    await create_share_token(task_id, token)

    return ShareResponse(
        share_token=token,
        share_url=f"/share/{token}"
    )


@router.get("/share/{token}", response_class=HTMLResponse)
async def view_shared_task(request: Request, token: str):
    """
    View a shared task result (read-only).

    Args:
        request: FastAPI request
        token: Share token

    Returns:
        HTML page with task result
    """
    # Get task by share token
    task = await get_task_by_share_token(token)
    if not task:
        raise HTTPException(status_code=404, detail="Shared task not found or expired")

    # Render shared view
    return templates.TemplateResponse(
        request,
        "share.html",
        {
            "task": task.to_dict(),
            "share_token": token
        }
    )
