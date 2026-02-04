"""
Template schemas.
"""

from pydantic import BaseModel, Field


class CreateTemplateRequest(BaseModel):
    """Request to create a template."""
    name: str = Field(..., min_length=1)
    description: str | None = None
    task_template: str = Field(..., min_length=1)
    config_name: str


class ApplyTemplateResponse(BaseModel):
    """Response after applying a template."""
    task_id: str
    status: str
    message: str
