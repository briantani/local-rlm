"""
Common schema patterns and generic responses for web API.

Provides reusable base classes to eliminate duplication across routes.
"""

from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T')


class ListResponse(BaseModel, Generic[T]):
    """
    Generic list response pattern.

    Replace duplicate patterns like:
        class TaskListResponse(BaseModel):
            tasks: list[TaskResponse]
            count: int

    With:
        ListResponse[TaskResponse]

    Usage:
        return ListResponse[TaskResponse](items=tasks, count=len(tasks))
    """
    items: list[T]
    count: int

    class Config:
        arbitrary_types_allowed = True


class MessageResponse(BaseModel):
    """Standard message response for operations without complex data."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    details: str | None = None
    success: bool = False
