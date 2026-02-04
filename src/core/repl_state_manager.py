"""
REPL State Manager.

Handles storage and retrieval of REPL instances for follow-up queries.
Extracted from TaskService for better separation of concerns.

Phase 6: Service Layer Refactoring
"""

import logging
import threading

from src.core.repl import PythonREPL


logger = logging.getLogger(__name__)


class ReplStateManager:
    """
    Manages REPL state storage for follow-up queries.

    Uses in-memory storage keyed by task_id. Thread-safe for concurrent access.
    REPL state is NOT persisted to disk - only stored in memory during runtime.
    """

    def __init__(self):
        """Initialize the REPL state manager with empty storage."""
        self._storage: dict[str, PythonREPL] = {}
        self._lock = threading.Lock()

    def store(self, task_id: str, repl: PythonREPL) -> None:
        """
        Store REPL state for a task.

        Args:
            task_id: Task identifier
            repl: REPL instance to store
        """
        with self._lock:
            self._storage[task_id] = repl
            logger.debug(
                f"Stored REPL state for task {task_id} "
                f"({len(repl.globals)} globals, {len(repl.locals)} locals)"
            )

    def retrieve(self, task_id: str) -> PythonREPL | None:
        """
        Retrieve REPL state for a task.

        Args:
            task_id: Task identifier

        Returns:
            REPL instance if found, None otherwise
        """
        with self._lock:
            repl = self._storage.get(task_id)
            if repl:
                logger.debug(
                    f"Retrieved REPL state for task {task_id} "
                    f"({len(repl.globals)} globals, {len(repl.locals)} locals)"
                )
            return repl

    def clear(self, task_id: str) -> None:
        """
        Clear stored REPL state for a task.

        Args:
            task_id: Task identifier
        """
        with self._lock:
            if task_id in self._storage:
                del self._storage[task_id]
                logger.info(f"Cleared REPL state for task {task_id}")

    def has(self, task_id: str) -> bool:
        """
        Check if REPL state exists for a task.

        Args:
            task_id: Task identifier

        Returns:
            True if REPL state exists
        """
        with self._lock:
            return task_id in self._storage

    def clear_all(self) -> None:
        """Clear all stored REPL states. Useful for cleanup."""
        with self._lock:
            count = len(self._storage)
            self._storage.clear()
            logger.info(f"Cleared all REPL states ({count} tasks)")
