"""
REPL Execution History Tracker.

Manages execution history and context for code execution.

Phase 3: REPL refactoring
"""

from datetime import datetime
from typing import Any


class ExecutionHistory:
    """Manages execution history for REPL context."""

    def __init__(self):
        """Initialize execution history tracker."""
        self._history: list[dict[str, Any]] = []

    def add_entry(self, code: str, output: str, step: int) -> None:
        """Add an execution entry to the history.

        Args:
            code: The Python code that was executed
            output: The captured output
            step: The step number (for ordering)
        """
        entry = {
            "code": code,
            "output": output,
            "step": step,
            "output_length": len(output),
            "timestamp": datetime.now().isoformat(),
        }
        self._history.append(entry)

    def get_all(self) -> list[dict[str, Any]]:
        """Get all history entries.

        Returns:
            List of execution history entries
        """
        return self._history.copy()

    def get_last(self) -> dict[str, Any] | None:
        """Get the most recent history entry.

        Returns:
            The last history entry, or None if empty
        """
        return self._history[-1] if self._history else None

    def get_metadata_str(self) -> str:
        """Format execution history as metadata string for context.

        Returns a concise summary of execution history that can be sent to the LLM
        (per the MIT RLM paper, metadata instead of full content).

        Returns:
            Formatted execution history summary
        """
        if not self._history:
            return "Execution History: 0 steps. No code executed yet."

        # Count total chars
        total_chars = sum(len(e["code"]) + len(e["output"]) for e in self._history)
        num_steps = len(self._history)

        # Build summary
        lines = [f"Execution History: {num_steps} steps, {total_chars} chars total\n"]

        # Show summary of each step (metadata, not content)
        for entry in self._history:
            step = entry.get("step", "?")
            code_len = len(entry.get("code", ""))
            output_len = entry.get("output_length", len(entry.get("output", "")))
            lines.append(f"  Step {step}: {code_len} chars code → {output_len} chars output")

        return "".join(lines)

    def get_last_output(self) -> str:
        """Get the last execution's output (without any labels/preview header).

        Returns:
            The last output, or empty string if no history
        """
        if not self._history:
            return ""

        return self._history[-1].get("output", "")

    def get_last_output_preview(self, max_chars: int = 500) -> str:
        """Get a preview of the last execution's output.

        Truncates if longer than max_chars.

        Args:
            max_chars: Maximum characters to include

        Returns:
            Preview of the last output, or empty string if no history
        """
        if not self._history:
            return ""

        last_output = self._history[-1].get("output", "")

        if len(last_output) > max_chars:
            return f"Last output:\n{last_output[:max_chars]}\n... ({len(last_output)} chars)"

        return f"Last output:\n{last_output}"

    def clear(self) -> None:
        """Clear all execution history."""
        self._history.clear()

    def __len__(self) -> int:
        """Get the number of history entries."""
        return len(self._history)

    def __iter__(self):
        """Iterate over history entries."""
        return iter(self._history)
