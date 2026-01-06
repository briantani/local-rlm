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


class MessageRole(str, Enum):
    """Chat message role."""
    USER = "user"
    ASSISTANT = "assistant"


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


@dataclass
class ChatMessage:
    """Database record for a chat message."""
    id: int
    task_id: str
    role: MessageRole
    content: str
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class TaskTemplate:
    """Database record for a task template."""
    id: int
    name: str
    description: str
    task_template: str  # Template text with placeholders
    config_name: str
    context_path: str | None
    created_at: datetime
    session_id: str | None  # Optional: restrict to creator

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_template": self.task_template,
            "config_name": self.config_name,
            "context_path": self.context_path,
            "created_at": self.created_at.isoformat(),
            "session_id": self.session_id,
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

        # Chat messages table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """)

        # Index for task chat queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_task
            ON chat_messages(task_id, timestamp)
        """)

        # Share tokens table (Phase 17)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS share_tokens (
                token TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        """)

        # Index for token lookup
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_share_token_task
            ON share_tokens(task_id)
        """)

        # Task templates table (Phase 17)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                task_template TEXT NOT NULL,
                config_name TEXT NOT NULL,
                context_path TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT
            )
        """)

        # Index for template lookup
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_templates_session
            ON task_templates(session_id)
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


# =============================================================================
# Chat Message Operations
# =============================================================================


async def create_chat_message(
    task_id: str,
    role: MessageRole,
    content: str,
) -> ChatMessage:
    """
    Create a new chat message.

    Args:
        task_id: Task identifier
        role: Message role (user/assistant)
        content: Message content

    Returns:
        Created ChatMessage
    """
    now = datetime.now()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO chat_messages (task_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, role.value, content, now.isoformat()),
        )
        message_id = cursor.lastrowid
        await db.commit()

    return ChatMessage(
        id=message_id,
        task_id=task_id,
        role=role,
        content=content,
        timestamp=now,
    )


async def get_chat_messages(task_id: str) -> list[ChatMessage]:
    """
    Get all chat messages for a task.

    Args:
        task_id: Task identifier

    Returns:
        List of ChatMessages, ordered by timestamp
    """
    messages = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM chat_messages
            WHERE task_id = ?
            ORDER BY timestamp ASC
            """,
            (task_id,),
        ) as cursor:
            async for row in cursor:
                messages.append(_row_to_chat_message(row))
    return messages


def _row_to_chat_message(row: aiosqlite.Row) -> ChatMessage:
    """Convert a database row to ChatMessage."""
    return ChatMessage(
        id=row["id"],
        task_id=row["task_id"],
        role=MessageRole(row["role"]),
        content=row["content"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
    )


# =============================================================================
# Share Tokens (Phase 17)
# =============================================================================


async def create_share_token(task_id: str, token: str) -> str:
    """
    Create a shareable token for a task.

    Args:
        task_id: Task identifier
        token: Unique share token

    Returns:
        The created token
    """
    now = datetime.now()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO share_tokens (token, task_id, created_at)
            VALUES (?, ?, ?)
            """,
            (token, task_id, now),
        )
        await db.commit()

    logger.info(f"Created share token for task {task_id}")
    return token


async def get_task_by_share_token(token: str) -> TaskRecord | None:
    """
    Get task by share token.

    Args:
        token: Share token

    Returns:
        TaskRecord if found, None otherwise
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT t.* FROM tasks t
            INNER JOIN share_tokens st ON t.id = st.task_id
            WHERE st.token = ?
            """,
            (token,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return _row_to_record(row)
    return None


# =============================================================================
# Task Templates (Phase 17)
# =============================================================================


async def create_template(
    name: str,
    description: str,
    task_template: str,
    config_name: str,
    context_path: str | None = None,
    session_id: str | None = None,
) -> TaskTemplate:
    """
    Create a new task template.

    Args:
        name: Template name
        description: Template description
        task_template: Task text (can include placeholders)
        config_name: Configuration profile name
        context_path: Optional context folder path
        session_id: Optional session ID to restrict access

    Returns:
        Created TaskTemplate
    """
    now = datetime.now()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO task_templates (name, description, task_template, config_name, context_path, created_at, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, task_template, config_name, context_path, now, session_id),
        )
        template_id = cursor.lastrowid
        await db.commit()

    logger.info(f"Created template: {name}")
    return TaskTemplate(
        id=template_id,
        name=name,
        description=description,
        task_template=task_template,
        config_name=config_name,
        context_path=context_path,
        created_at=now,
        session_id=session_id,
    )


async def list_templates(session_id: str | None = None) -> list[TaskTemplate]:
    """
    List all templates, optionally filtered by session.

    Args:
        session_id: Optional session ID to filter by

    Returns:
        List of TaskTemplates
    """
    templates = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if session_id:
            # Get session-specific templates + public templates (session_id is NULL)
            query = """
                SELECT * FROM task_templates
                WHERE session_id = ? OR session_id IS NULL
                ORDER BY created_at DESC
            """
            params = (session_id,)
        else:
            # Get all public templates
            query = """
                SELECT * FROM task_templates
                WHERE session_id IS NULL
                ORDER BY created_at DESC
            """
            params = ()

        async with db.execute(query, params) as cursor:
            async for row in cursor:
                templates.append(_row_to_template(row))

    return templates


async def get_template(template_id: int) -> TaskTemplate | None:
    """
    Get a template by ID.

    Args:
        template_id: Template ID

    Returns:
        TaskTemplate if found, None otherwise
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM task_templates WHERE id = ?",
            (template_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return _row_to_template(row)
    return None


async def delete_template(template_id: int) -> bool:
    """
    Delete a template.

    Args:
        template_id: Template ID

    Returns:
        True if deleted, False if not found
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM task_templates WHERE id = ?",
            (template_id,),
        )
        await db.commit()
        return cursor.rowcount > 0


def _row_to_template(row: aiosqlite.Row) -> TaskTemplate:
    """Convert a database row to TaskTemplate."""
    return TaskTemplate(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        task_template=row["task_template"],
        config_name=row["config_name"],
        context_path=row["context_path"],
        created_at=datetime.fromisoformat(row["created_at"]),
        session_id=row["session_id"],
    )
