import os
import pytest
from pathlib import Path
from src.core.budget import BudgetManager
from src.core.config_loader import load_profile
from src.config import get_lm_for_role

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


def get_lm_for_testing(provider: str = "ollama", model: str | None = None):
    """
    Helper function for tests to get an LM using the new config-based approach.
    Creates a minimal ProfileConfig for testing purposes.

    Args:
        provider: Provider name (ollama, gemini, openai)
        model: Optional model name

    Returns:
        A dspy.LM instance wrapped with BudgetWrapper
    """
    # Use existing test configs or create a minimal one
    if provider == "ollama":
        config_path = Path(__file__).parent.parent / "configs" / "local-only.yaml"
    elif provider == "gemini":
        config_path = Path(__file__).parent.parent / "configs" / "cost-effective.yaml"
    else:
        config_path = Path(__file__).parent.parent / "configs" / "base.yaml"

    try:
        config = load_profile(config_path)
        BudgetManager._clear()
        budget_manager = BudgetManager(max_budget=10.0)  # High budget for tests
        return get_lm_for_role("root", config, budget_manager=budget_manager)
    except Exception as e:
        pytest.skip(f"Could not load test config: {e}")
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
