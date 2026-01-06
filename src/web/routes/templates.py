"""
Templates API routes for the RLM web interface.

Provides endpoints for creating, listing, and applying task templates.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from src.web.database import (
    create_template,
    delete_template,
    get_template,
    list_templates,
)

router = APIRouter()


class CreateTemplateRequest(BaseModel):
    """Request body for creating a template."""

    name: str
    description: str
    task_text: str
    config_name: str
    context_path: str | None = None


class ApplyTemplateResponse(BaseModel):
    """Response when applying a template."""

    task_text: str
    config_name: str
    context_path: str | None


@router.post("/api/templates")
async def create_template_endpoint(request: Request, body: CreateTemplateRequest):
    """
    Create a new task template.

    Args:
        request: FastAPI request object (for session)
        body: Template creation data

    Returns:
        Created template as JSON
    """
    # Get session ID if user is logged in (optional)
    session_id = request.session.get("session_id")

    template = await create_template(
        name=body.name,
        description=body.description,
        task_template=body.task_text,
        config_name=body.config_name,
        context_path=body.context_path,
        session_id=session_id,
    )

    return template.to_dict()


@router.get("/api/templates")
async def list_templates_endpoint(request: Request):
    """
    List all available templates.

    Args:
        request: FastAPI request object (for session filtering)

    Returns:
        List of templates as JSON
    """
    session_id = request.session.get("session_id")
    templates = await list_templates(session_id=session_id)
    return [t.to_dict() for t in templates]


@router.get("/api/templates/{template_id}")
async def get_template_endpoint(template_id: int):
    """
    Get a specific template by ID.

    Args:
        template_id: Template identifier

    Returns:
        Template as JSON

    Raises:
        HTTPException: If template not found
    """
    template = await get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template.to_dict()


@router.post("/api/templates/{template_id}/apply")
async def apply_template_endpoint(template_id: int) -> ApplyTemplateResponse:
    """
    Apply a template, returning its configuration for use.

    Args:
        template_id: Template identifier

    Returns:
        Template data ready to use

    Raises:
        HTTPException: If template not found
    """
    template = await get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return ApplyTemplateResponse(
        task_text=template.task_template,
        config_name=template.config_name,
        context_path=template.context_path,
    )


@router.delete("/api/templates/{template_id}")
async def delete_template_endpoint(template_id: int):
    """
    Delete a template.

    Args:
        template_id: Template identifier

    Returns:
        Success message

    Raises:
        HTTPException: If template not found
    """
    success = await delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")

    return {"message": "Template deleted successfully"}
