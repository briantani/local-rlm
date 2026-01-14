import os
import pytest
import socket
import httpx
from pathlib import Path
from src.core.budget import BudgetManager, BudgetWrapper
from src.core.config_loader import load_profile
from src.config import get_lm_for_role
import dspy

# Set testing environment variable to prevent log file creation
os.environ["RLM_TESTING"] = "1"

# Compatibility shim: Python 3.14 deprecates `asyncio.iscoroutinefunction`.
# Some third-party packages still call it; point it to `inspect.iscoroutinefunction`
# so callers get the modern behavior without emitting DeprecationWarnings.
import inspect
import asyncio as _asyncio
_asyncio.iscoroutinefunction = inspect.iscoroutinefunction


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
    # By default, avoid hitting external LMs during unit tests. Instead,
    # provide a fast in-memory MockLM for common providers unless
    # RLM_RUN_INTEGRATION=1 is set. This lets DSPy module tests exercise
    # logic without requiring a live model server.
    if provider in ("ollama", "gemini", "openai") and not os.environ.get("RLM_RUN_INTEGRATION"):
        # Return a Budget-wrapped MockLM for fast deterministic responses
        BudgetManager._clear()
        bm = BudgetManager(max_budget=10.0)
        class MockLM(dspy.LM):
            def __init__(self, name: str = "mock"):
                # Initialize Base LM with a model name so isinstance checks pass
                super().__init__(model=name)

            def __call__(self, prompt, **kwargs):
                text = str(prompt).lower()
                import re

                # Architect-like responses: return action prediction
                if any(k in text for k in ["code or answer", "decide", "what is", "action:"]):
                    # Prefer CODE for math/programming prompts
                    if re.search(r"\d+\s*\*\s*\d+", text) or any(w in text for w in ["calculate", "compute", "fibonacci"]):
                        return dspy.Prediction(action="CODE")
                    return dspy.Prediction(action="ANSWER")

                # Coder-like responses: return python_code field and optional expected_artifacts
                if any(w in text for w in ["python", "def ", "fibonacci", "print(", "sum("]):
                    if "fibonacci" in text:
                        code = "def fib(n):\n    a,b=0,1\n    for _ in range(n):\n        a,b=b,a+b\n    print(a)\nfib(10)"
                    elif re.search(r"(\d+)\s*\*\s*(\d+)", text):
                        m = re.search(r"(\d+)\s*\*\s*(\d+)", text)
                        product = int(m.group(1)) * int(m.group(2))
                        code = f"print({product})"
                    elif "sum of numbers" in text or "sum(" in text or "sum of" in text:
                        code = "print(sum(range(1,11)))"
                    else:
                        code = "print(\"MOCKED\")"

                    pred = dspy.Prediction(python_code=code)
                    # Detect inline expected artifacts annotation
                    # e.g., '# expected_artifacts: file1.png, data.csv' in the prompt
                    m_art = re.search(r"expected_artifacts\s*[:=]\s*(.+)", text)
                    if m_art:
                        files = [f.strip() for f in m_art.group(1).split(",") if f.strip()]
                        pred.expected_artifacts = files
                    else:
                        pred.expected_artifacts = []

                    return pred

                # Responder-like: return response text
                if any(w in text for w in ["say 'hello world'", "hello world", "mock_response"]):
                    return dspy.Prediction(response="Hello World")

                # Fallback: return a Prediction with response to be consistent
                return dspy.Prediction(response="MOCK_RESPONSE")

        mock = MockLM()
        wrapper = BudgetWrapper(mock, bm)
        wrapper._model_id = "mock"
        return wrapper

    # Use existing test configs or create a minimal one
    if provider == "ollama":
        config_path = Path(__file__).parent.parent / "configs" / "local-only.yaml"
        # Quick connectivity check for local Ollama server (port 11434).
        # Prefer an HTTP health check to ensure the service responds to requests.
        try:
            resp = httpx.get("http://localhost:11434/v1/models", timeout=1.0)
            if resp.status_code >= 500 or resp.status_code == 0:
                pytest.skip("Ollama server not responding correctly; skipping Ollama tests")
        except Exception:
            pytest.skip("Ollama server not reachable on localhost:11434; skipping Ollama tests")
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


class MockArchitect:
    """Mock Architect that returns a predetermined action."""

    def __init__(self, action: str = "ANSWER"):
        self.action = action
        self.call_count = 0

    def __call__(self, query: str, data_desc: str = "", artifacts_info: str = ""):
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

    def __call__(self, query: str, context: str = "", artifacts_info: str = ""):
        self.call_count += 1
        return MockPrediction(response=self._response)


class MockREPL:
    """Mock REPL that returns predetermined output."""

    def __init__(self, output: str = "mock output"):
        self.output = output
        self.call_count = 0
        self.executed_code: list[str] = []
        self._execution_history: list[dict] = []
        self._task = ""

    def execute(self, code: str) -> str:
        self.call_count += 1
        self.executed_code.append(code)
        return self.output

    def set_task(self, task: str) -> None:
        """Set the current task (paper-style interface)."""
        self._task = task

    def add_history_entry(self, code: str, output: str, step: int) -> None:
        """Add an execution history entry (paper-style interface)."""
        self._execution_history.append({
            "step": step,
            "code": code,
            "output": output,
            "output_length": len(output),
        })

    def get_history_metadata(self) -> str:
        """Paper-style: Return metadata about history, NOT full content."""
        total_chars = sum(len(e["code"]) + len(e["output"]) for e in self._execution_history)
        return f"Execution History: {len(self._execution_history)} steps, {total_chars} chars total."

    def get_last_output_preview(self, max_chars: int = 500) -> str:
        """Return truncated preview of last execution output."""
        if not self._execution_history:
            return ""
        last = self._execution_history[-1]
        output = last["output"]
        if len(output) > max_chars:
            output = output[:max_chars] + "..."
        return f"Last output ({last['output_length']} chars): {output}"


class MockPrediction:
    """Generic mock prediction object with dynamic attributes."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
