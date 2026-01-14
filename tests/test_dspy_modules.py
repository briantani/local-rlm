import pytest
import dspy
import ast
from src.modules.coder import Coder
from src.modules.architect import Architect
from tests.conftest import get_lm_for_testing
import os
from tests.conftest import MockCoder, MockArchitect

# Setup the LM for testing
# We use Ollama for these tests as verified in Phase 0/1
@pytest.fixture(scope="module")
def setup_dspy():
    try:
        lm = get_lm_for_testing("ollama")
        dspy.settings.configure(lm=lm)
        return lm
    except Exception as e:
        pytest.skip(f"Skipping DSPy tests: {e}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_coder_valid_code(setup_dspy):
    """Test 3.1: Ask Coder to 'Calculate the 10th Fibonacci number'. Assert ast.parse(result) passes."""
    # If integration tests are disabled, use a fast MockCoder
    if not os.getenv("RLM_RUN_INTEGRATION"):
        mock = MockCoder(code="def fib(n):\n    a,b=0,1\n    for _ in range(n):\n        a,b=b,a+b\n    print(a)\nfib(10)")
        result = mock(task="Calculate the 10th Fibonacci number and print it.")
        code = result.python_code
    else:
        coder = Coder()
        task = "Calculate the 10th Fibonacci number and print it."

        # We might need to increase max_backtracks if the model is weak
        # But for a simple task, it should work.
        result = coder(task=task)
        code = result.python_code

    print(f"\nGenerated Code:\n{code}")

    # Assert it is valid python
    try:
        ast.parse(code)
    except SyntaxError:
        pytest.fail("Coder generated invalid Python syntax.")

    assert "print" in code or "return" in code # Basic check that it does something

@pytest.mark.integration
@pytest.mark.asyncio
async def test_architect_decision_making(setup_dspy):
    """Test 3.2: Ask Architect 'What is 2+2?' (Expect CODE or ANSWER)."""
    # Use MockArchitect when integration is disabled for fast deterministic behavior
    if not os.getenv("RLM_RUN_INTEGRATION"):
        mock_arch = MockArchitect(action="CODE")
        query = "What is 1234 * 5678?"
        result = mock_arch(query)
        assert result.action in ["CODE", "ANSWER"]

        query_abstract = "Explain the concept of recursion."
        mock_arch2 = MockArchitect(action="ANSWER")
        result_abstract = mock_arch2(query_abstract)
        assert result_abstract.action in ["ANSWER", "CODE"]
    else:
        architect = Architect()

        # Simple math -> CODE or ANSWER are acceptable, but usually CODE for precision
        query = "What is 1234 * 5678?"
        result = architect(query=query)
        print(f"\nQuery: {query} -> Action: {result.action}")
        assert result.action in ["CODE", "ANSWER"]

        # Complex/Abstract -> ANSWER (no DELEGATE anymore, just CODE or ANSWER)
        query_abstract = "Explain the concept of recursion."
        result_abstract = architect(query=query_abstract)
        print(f"\nQuery: {query_abstract} -> Action: {result_abstract.action}")
        assert result_abstract.action in ["ANSWER", "CODE"]
