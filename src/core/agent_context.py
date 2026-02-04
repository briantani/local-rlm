"""
Context formatting and history management for RLM Agent.

Handles execution history tracking and context formatting with two modes:
1. Full context (deprecated): Returns entire execution history
2. Metadata-only (paper-style): Returns just summary statistics
"""

import threading


class AgentContext:
    """Manages execution history and context formatting for the agent."""

    def __init__(self):
        """Initialize with thread-safe history tracking (Python 3.14t compatibility)."""
        self._history_lock = threading.Lock()
        self.history: list[tuple[str, str]] = []  # List of (Action/Code, Output)

    def add_history(self, action: str, output: str) -> None:
        """
        Thread-safe history append for Python 3.14t compatibility.

        Args:
            action: The action or code that was executed
            output: The result or output from execution
        """
        with self._history_lock:
            self.history.append((action, output))

    def format_context(self) -> str:
        """
        Format the execution history into a string context.

        DEPRECATED: This returns full context. For paper-style metadata-only
        approach, use format_context_metadata() instead.

        Returns:
            Formatted string with full execution history
        """
        with self._history_lock:
            if not self.history:
                return ""

            context_str = "Execution History:\n"
            for i, (action_or_code, output) in enumerate(self.history, 1):
                context_str += f"--- Step {i} ---\n"
                context_str += f"Input: {action_or_code}\n"
                context_str += f"Output: {output}\n"
            return context_str

    def format_context_metadata(self, repl=None) -> str:
        """
        Get metadata about execution history (paper-style approach).

        Paper insight: "Long prompts should not be fed into the neural network
        directly but should instead be treated as part of the environment."

        Returns metadata like step count and char totals, NOT full content.
        The LLM accesses full content via __execution_history__ in code.

        Args:
            repl: Optional REPL instance that may have a get_history_metadata method

        Returns:
            Metadata string describing execution history
        """
        # Use REPL's metadata method if available
        if repl and hasattr(repl, 'get_history_metadata'):
            return repl.get_history_metadata()

        # Fallback for mocked REPLs in tests
        with self._history_lock:
            if not self.history:
                return "Execution History: 0 steps. No code executed yet."

            total_chars = sum(len(a) + len(o) for a, o in self.history)
            return f"Execution History: {len(self.history)} steps, {total_chars} chars total."

    def get_last_output_preview(self, repl=None, max_chars: int = 500) -> str:
        """
        Get a preview of the last output for decision making.

        Args:
            repl: Optional REPL instance that may have a get_last_output_preview method
            max_chars: Maximum characters to include in preview

        Returns:
            Preview string of last output
        """
        if repl and hasattr(repl, 'get_last_output_preview'):
            return repl.get_last_output_preview(max_chars=max_chars)

        # Fallback for mocked REPLs
        with self._history_lock:
            if not self.history:
                return ""
            _, last_output = self.history[-1]
            if len(last_output) <= max_chars:
                return f"Last output:\n{last_output}"
            return f"Last output ({len(last_output)} chars, truncated):\n{last_output[:max_chars]}..."

    def get_history_copy(self) -> list[tuple[str, str]]:
        """
        Get a thread-safe copy of the history.

        Returns:
            Copy of the history list
        """
        with self._history_lock:
            return self.history.copy()
