"""
Chat API Routes for Follow-up Queries.

Handles chat messages for tasks, maintaining REPL context.
Phase 16: Chat Interface for Follow-up Queries
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.web.database import (
    MessageRole,
    create_chat_message,
    get_chat_messages,
    get_task,
)
from src.web.dependencies import get_services

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks/{task_id}/chat", tags=["Chat"])
services = get_services()


class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""
    message: str


class ChatMessageResponse(BaseModel):
    """Response model for a chat message."""
    id: int
    role: str
    content: str
    timestamp: str


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    messages: list[ChatMessageResponse]
    count: int


@router.get("")
async def get_chat_history(task_id: str) -> ChatHistoryResponse:
    """
    Get chat history for a task.

    Args:
        task_id: Task identifier

    Returns:
        List of chat messages
    """
    # Verify task exists
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get messages
    messages = await get_chat_messages(task_id)

    return ChatHistoryResponse(
        messages=[
            ChatMessageResponse(
                id=msg.id,
                role=msg.role.value,
                content=msg.content,
                timestamp=msg.timestamp.isoformat(),
            )
            for msg in messages
        ],
        count=len(messages),
    )


@router.post("")
async def send_chat_message(task_id: str, request: ChatMessageRequest):
    """
    Send a follow-up message for a task.

    Executes the query in the same REPL context as the original task.

    Args:
        task_id: Task identifier
        request: Chat message request

    Returns:
        Assistant's response
    """
    # Verify task exists and is completed
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status.value not in ("completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail="Cannot chat with a task that is not completed"
        )

    # Store user message
    await create_chat_message(
        task_id=task_id,
        role=MessageRole.USER,
        content=request.message,
    )

    try:
        # Execute follow-up query with REPL context
        # Get session and create task service
        services_container = get_services()
        session_service = services_container.session_service
        session = session_service.get_session(task.session_id)
        
        if not session:
            raise HTTPException(
                status_code=400,
                detail="Session not found. The original session may have expired."
            )
        
        task_service = services_container.get_task_service(session)

        # Check if REPL state exists
        if not task_service.has_repl_state(task_id):
            error_msg = (
                "REPL state not available for this task. "
                "The task may not have completed successfully, "
                "or the state was cleared."
            )
            logger.warning(f"No REPL state for task {task_id}")

            # Store error message
            assistant_message = await create_chat_message(
                task_id=task_id,
                role=MessageRole.ASSISTANT,
                content=error_msg,
            )

            return {
                "response": error_msg,
                "message_id": assistant_message.id,
                "timestamp": assistant_message.timestamp.isoformat(),
            }

        # Run follow-up query with stored REPL
        response_text = task_service.run_followup(
            task_id=task_id,
            query=request.message,
            config_name=task.config_name,
        )

        # Store assistant response
        assistant_message = await create_chat_message(
            task_id=task_id,
            role=MessageRole.ASSISTANT,
            content=response_text,
        )

        return {
            "response": response_text,
            "message_id": assistant_message.id,
            "timestamp": assistant_message.timestamp.isoformat(),
        }

    except ValueError as e:
        # REPL state not found
        logger.error(f"REPL state error for task {task_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing chat message for task {task_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )
