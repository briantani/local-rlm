"""
WebSocket Streaming.

Provides real-time task updates via WebSocket connections.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.web.task_runner import subscribe, UpdateType
from src.web.database import get_task, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/tasks/{task_id}")
async def task_stream(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for streaming task updates.

    Connect to receive real-time updates for a task including:
    - status: Task status changes
    - step: Each agent step
    - code: Generated Python code
    - output: Code execution output
    - complete: Task completion with final result
    - error: Task failure with error details

    The connection will automatically close after receiving
    a 'complete' or 'error' message.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for task {task_id}")

    try:
        # Check if task exists
        task = await get_task(task_id)
        if not task:
            await websocket.send_json({
                "type": "error",
                "data": {"error": f"Task not found: {task_id}"},
            })
            await websocket.close()
            return

        # If task is already completed, send the result immediately
        if task.status == TaskStatus.COMPLETED:
            await websocket.send_json({
                "type": "complete",
                "data": task.result or {},
            })
            await websocket.close()
            return

        # If task failed, send the error
        if task.status == TaskStatus.FAILED:
            await websocket.send_json({
                "type": "error",
                "data": task.result or {"error": "Task failed"},
            })
            await websocket.close()
            return

        # Subscribe to updates
        async for update in subscribe(task_id):
            await websocket.send_json(update.to_dict())

            # Connection closes after completion or error
            if update.type in (UpdateType.COMPLETE, UpdateType.ERROR):
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"error": str(e)},
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
