"""
Task Runner.

Handles async task execution with event streaming for WebSocket updates.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator

from src.rlm.services import TaskService
from src.rlm.services.task_service import StepInfo, TaskResult
from src.web.database import TaskStatus, update_task_status

logger = logging.getLogger(__name__)


class UpdateType(str, Enum):
    """Types of task updates."""
    STATUS = "status"
    STEP = "step"
    CODE = "code"
    OUTPUT = "output"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class TaskUpdate:
    """A single update event for a task."""
    type: UpdateType
    data: dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


# Global task update queues (in-memory pub/sub)
# Maps task_id -> list of asyncio.Queue for subscribers
task_updates: dict[str, list[asyncio.Queue]] = defaultdict(list)

# Lock for thread-safe access to task_updates
_updates_lock = asyncio.Lock()


async def subscribe(task_id: str) -> AsyncGenerator[TaskUpdate, None]:
    """
    Subscribe to updates for a task.

    Yields TaskUpdate objects as they are published.

    Args:
        task_id: The task to subscribe to

    Yields:
        TaskUpdate objects
    """
    queue: asyncio.Queue = asyncio.Queue()

    async with _updates_lock:
        task_updates[task_id].append(queue)

    try:
        while True:
            update = await queue.get()
            yield update

            # Stop on completion or error
            if update.type in (UpdateType.COMPLETE, UpdateType.ERROR):
                break
    finally:
        async with _updates_lock:
            if queue in task_updates[task_id]:
                task_updates[task_id].remove(queue)
            # Cleanup empty lists
            if not task_updates[task_id]:
                del task_updates[task_id]


async def publish(task_id: str, update: TaskUpdate):
    """
    Publish an update to all subscribers of a task.

    Args:
        task_id: The task ID
        update: The update to publish
    """
    async with _updates_lock:
        queues = task_updates.get(task_id, [])
        for queue in queues:
            await queue.put(update)


async def run_task_async(
    task_id: str,
    task_text: str,
    config_name: str,
    context_path: str | None,
    task_service: TaskService,
):
    """
    Run a task asynchronously and publish updates.

    This function is designed to be run in a background task.

    Args:
        task_id: Unique task identifier
        task_text: The task/query text
        config_name: Configuration profile name
        context_path: Optional path to context directory
        task_service: TaskService instance with session
    """
    logger.info(f"Starting task {task_id}: {task_text[:50]}...")

    try:
        # Update status to running
        await update_task_status(task_id, TaskStatus.RUNNING)
        await publish(task_id, TaskUpdate(
            type=UpdateType.STATUS,
            data={"status": "running"},
        ))

        # Define callback for step updates
        def on_step(step_info: StepInfo):
            # Schedule the async publish in the event loop
            asyncio.create_task(_publish_step(task_id, step_info))

        # Run the task in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: task_service.run_task(
                task=task_text,
                config_name=config_name,
                context_path=Path(context_path) if context_path else None,
                on_step=on_step,
            )
        )

        # Build result data
        result_data = {
            "answer": result.answer,
            "total_cost": result.total_cost,
            "model_breakdown": result.model_breakdown,
            "duration_seconds": result.duration_seconds,
            "step_count": result.step_count,
            "execution_history": [
                {
                    "step": s.step_number,
                    "action": s.action,
                    "input": s.input_text[:500],  # Truncate for storage
                    "output": s.output_text[:1000],  # Truncate for storage
                }
                for s in result.execution_history
            ],
        }

        # Update database
        await update_task_status(task_id, TaskStatus.COMPLETED, result_data)

        # Publish completion
        await publish(task_id, TaskUpdate(
            type=UpdateType.COMPLETE,
            data=result_data,
        ))

        logger.info(f"Task {task_id} completed successfully")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")

        error_data = {
            "error": str(e),
            "error_type": type(e).__name__,
        }

        # Update database
        await update_task_status(task_id, TaskStatus.FAILED, error_data)

        # Publish error
        await publish(task_id, TaskUpdate(
            type=UpdateType.ERROR,
            data=error_data,
        ))


async def _publish_step(task_id: str, step_info: StepInfo):
    """Publish a step update."""
    # Determine if this is code or output
    if step_info.action == "CODE":
        await publish(task_id, TaskUpdate(
            type=UpdateType.CODE,
            data={
                "step": step_info.step_number,
                "code": step_info.input_text,
            },
        ))
        await publish(task_id, TaskUpdate(
            type=UpdateType.OUTPUT,
            data={
                "step": step_info.step_number,
                "output": step_info.output_text,
            },
        ))
    else:
        await publish(task_id, TaskUpdate(
            type=UpdateType.STEP,
            data={
                "step": step_info.step_number,
                "action": step_info.action,
                "input": step_info.input_text[:500],
                "output": step_info.output_text[:1000],
            },
        ))
