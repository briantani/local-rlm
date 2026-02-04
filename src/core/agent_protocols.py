"""
Protocol definitions for RLM Agent components.

Enables dependency injection and testing with mocks that follow these interfaces.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class CodeExecutor(Protocol):
    """Protocol for code execution backends (e.g., PythonREPL)."""
    def execute(self, code: str) -> str:
        """Execute code and return output or error message."""
        ...

    def check_for_final(self, output: str) -> str | None:
        """Check if output contains FINAL() marker. Returns answer if present."""
        ...


@runtime_checkable
class TaskRouter(Protocol):
    """Protocol for task routing/decision making (e.g., Architect)."""
    def __call__(self, query: str, data_desc: str) -> object:
        """Decide next action: CODE or ANSWER."""
        ...


@runtime_checkable
class CodeGenerator(Protocol):
    """Protocol for code generation modules (e.g., Coder)."""
    def __call__(self, task: str, context_summary: str) -> object:
        """Generate Python code to solve a task."""
        ...


@runtime_checkable
class ResponseFormatter(Protocol):
    """Protocol for formatting final answers (e.g., Responder)."""
    def __call__(self, task: str, summary: str) -> object:
        """Format the final answer for the user."""
        ...
