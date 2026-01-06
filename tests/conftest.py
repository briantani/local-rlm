import os
import pytest
from src.core.budget import BudgetManager

# Set testing environment variable to prevent log file creation
os.environ["RLM_TESTING"] = "1"


@pytest.fixture(autouse=True)
def reset_budget():
    """
    Automatically reset the BudgetManager singleton before each test.
    This ensures that tests like 'test_budget_hard_stop' don't pollute
    the state for other tests.
    """
    budget = BudgetManager()
    budget.reset()
    budget.max_budget = 1.0  # Reset to default limit
    yield
    # Optional: Reset after test too
    budget.reset()
    budget.max_budget = 1.0


class MockArchitect:
    """Mock Architect that returns a predetermined action."""

    def __init__(self, action: str = "ANSWER"):
        self.action = action
        self.call_count = 0

    def __call__(self, query: str, data_desc: str = ""):
        self.call_count += 1
        return MockPrediction(action=self.action)


class MockCoder:
    """Mock Coder that returns predetermined code."""

    def __init__(self, code: str = "print('hello')"):
        self.code = code
        self.call_count = 0

    def __call__(self, task: str, context_summary: str = ""):
        self.call_count += 1
        return MockPrediction(python_code=self.code)


class MockResponder:
    """Mock Responder that returns a predetermined response."""

    def __init__(self, response: str = "Mock response"):
        self._response = response
        self.call_count = 0

    def __call__(self, query: str, context: str = ""):
        self.call_count += 1
        return MockPrediction(response=self._response)


class MockDelegator:
    """Mock Delegator that returns predetermined subtasks."""

    def __init__(self, subtasks: list[str] | None = None):
        self.subtasks = subtasks or ["subtask1", "subtask2"]
        self.call_count = 0

    def __call__(self, task: str, context: str = ""):
        self.call_count += 1
        return self.subtasks


class MockREPL:
    """Mock REPL that returns predetermined output."""

    def __init__(self, output: str = "mock output"):
        self.output = output
        self.call_count = 0
        self.executed_code: list[str] = []

    def execute(self, code: str) -> str:
        self.call_count += 1
        self.executed_code.append(code)
        return self.output


class MockPrediction:
    """Generic mock prediction object with dynamic attributes."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
