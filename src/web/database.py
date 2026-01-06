"""
SQLite Database for Task History.

Provides async database access for persisting task history.
API keys are NEVER stored in the database.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# Database file location
DB_PATH = Path("data/rlm.db")


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskRecord:
    """Database record for a task."""
    id: str
    session_id: str
    task_text: str
    config_name: str
    status: TaskStatus
    result: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "task_text": self.task_text,
            "config_name": self.config_name,
            "status": self.status.value,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


async def init_db():
    """Initialize the database with required tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                task_text TEXT NOT NULL,
                config_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)

        # Index for session queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_session
            ON tasks(session_id)
        """)

        await db.commit()
        logger.info(f"Database initialized at {DB_PATH}")


async def create_task(
    task_id: str,
    session_id: str,
    task_text: str,
    config_name: str,
) -> TaskRecord:
    """
    Create a new task record.

    Args:
        task_id: Unique task identifier
        session_id: Session that owns this task
        task_text: The task/query text
        config_name: Configuration profile name

    Returns:
        Created TaskRecord
    """
    now = datetime.now()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO tasks (id, session_id, task_text, config_name, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, session_id, task_text, config_name, TaskStatus.PENDING.value, now.isoformat()),
        )
        await db.commit()

    return TaskRecord(
        id=task_id,
        session_id=session_id,
        task_text=task_text,
        config_name=config_name,
        status=TaskStatus.PENDING,
        result=None,
        created_at=now,
        completed_at=None,
    )


async def update_task_status(
    task_id: str,
    status: TaskStatus,
    result: dict[str, Any] | None = None,
):
    """
    Update task status and optionally result.

    Args:
        task_id: Task identifier
        status: New status
        result: Optional result data
    """
    async with aiosqlite.connect(DB_PATH) as db:
        if status == TaskStatus.COMPLETED or status == TaskStatus.FAILED:
            await db.execute(
                """
                UPDATE tasks
                SET status = ?, result = ?, completed_at = ?
                WHERE id = ?
                """,
                (status.value, json.dumps(result) if result else None, datetime.now().isoformat(), task_id),
            )
        else:
            await db.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (status.value, task_id),
            )
        await db.commit()


async def get_task(task_id: str) -> TaskRecord | None:
    """
    Get a task by ID.

    Args:
        task_id: Task identifier

    Returns:
        TaskRecord or None if not found
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return _row_to_record(row)
    return None


async def get_tasks_for_session(
    session_id: str,
    limit: int = 50,
) -> list[TaskRecord]:
    """
    Get tasks for a session.

    Args:
        session_id: Session identifier
        limit: Maximum number of tasks to return

    Returns:
        List of TaskRecords, newest first
    """
    tasks = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM tasks
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit),
        ) as cursor:
            async for row in cursor:
                tasks.append(_row_to_record(row))
    return tasks


def _row_to_record(row: aiosqlite.Row) -> TaskRecord:
    """Convert a database row to TaskRecord."""
    return TaskRecord(
        id=row["id"],
        session_id=row["session_id"],
        task_text=row["task_text"],
        config_name=row["config_name"],
        status=TaskStatus(row["status"]),
        result=json.loads(row["result"]) if row["result"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
    )
