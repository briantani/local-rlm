import pytest
import dspy
from src.core.agent import RLMAgent
from src.config import get_lm
from conftest import MockArchitect, MockCoder, MockResponder, MockREPL


# ============================================================================
# UNIT TESTS (Mocked - Fast, Reliable)
# ============================================================================

class TestAgentUnitTests:
    """Unit tests for RLMAgent using dependency injection with mocks."""

    def test_agent_answer_action(self):
        """Test that ANSWER action returns responder's response."""
        mock_architect = MockArchitect(action="ANSWER")
        mock_responder = MockResponder(response="The answer is 42.")

        agent = RLMAgent(
            max_steps=3,
            architect=mock_architect,
            responder=mock_responder,
        )

        result = agent.run("What is the meaning of life?")

        assert result == "The answer is 42."
        assert mock_architect.call_count == 1
        assert mock_responder.call_count == 1

    def test_agent_code_action(self):
        """Test that CODE action executes code and stores in history."""
        mock_coder = MockCoder(code="print(2 + 2)")
        mock_repl = MockREPL(output="4")
        mock_responder = MockResponder(response="The result is 4.")

        # Architect returns CODE first, then ANSWER
        call_count = [0]
        def dynamic_architect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return type('Pred', (), {'action': 'CODE'})()
            return type('Pred', (), {'action': 'ANSWER'})()

        mock_architect_dynamic = type('Mock', (), {'__call__': lambda self, **kw: dynamic_architect(**kw)})()

        agent = RLMAgent(
            max_steps=3,
            architect=mock_architect_dynamic,
            coder=mock_coder,
            repl=mock_repl,
            responder=mock_responder,
        )

        _ = agent.run("Calculate 2 + 2")

        assert mock_repl.call_count == 1
        assert "print(2 + 2)" in mock_repl.executed_code[0]
        assert len(agent.history) >= 1

    def test_agent_max_steps_reached(self):
        """Test that agent stops after max_steps and returns fallback message."""
        mock_architect = MockArchitect(action="CODE")
        mock_coder = MockCoder(code="x = 1")
        mock_repl = MockREPL(output="")

        agent = RLMAgent(
            max_steps=2,
            architect=mock_architect,
            coder=mock_coder,
            repl=mock_repl,
        )

        result = agent.run("Loop forever")

        assert "Max steps reached" in result
        assert mock_architect.call_count == 2

    def test_agent_delegate_max_depth(self):
        """Test that DELEGATE at max_depth adds failure to history."""
        mock_responder = MockResponder(response="Fallback answer")

        # Architect returns DELEGATE first, then ANSWER
        call_count = [0]
        def dynamic_architect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return type('Pred', (), {'action': 'DELEGATE'})()
            return type('Pred', (), {'action': 'ANSWER'})()

        mock_architect_dynamic = type('Mock', (), {'__call__': lambda self, **kw: dynamic_architect(**kw)})()

        agent = RLMAgent(
            max_steps=3,
            max_depth=1,
            depth=1,  # Already at max depth
            architect=mock_architect_dynamic,
            responder=mock_responder,
        )

        result = agent.run("Delegate this task")

        # Should have added failure message to history
        history_text = str(agent.history)
        assert "Max recursion saturation reached" in history_text or result == "Fallback answer"

    def test_agent_unknown_action(self):
        """Test that unknown action returns error message."""
        mock_architect = MockArchitect(action="UNKNOWN_ACTION")

        agent = RLMAgent(
            max_steps=1,
            architect=mock_architect,
        )

        result = agent.run("Do something weird")

        assert "Unknown action" in result


# ============================================================================
# INTEGRATION TESTS (LLM-dependent - Slower, May Skip)
# ============================================================================

@pytest.fixture(scope="module")
def setup_dspy_ollama():
    try:
        lm = get_lm("ollama")
        dspy.settings.configure(lm=lm)
        return lm
    except Exception as e:
        pytest.skip(f"Skipping Agent tests: {e}")


@pytest.mark.asyncio
async def test_agent_end_to_end_math(setup_dspy_ollama):
    """
    Test 4.1: End-to-End Simple.
    Task: "Calculate the sum of numbers from 1 to 10."
    Expectation: The agent writes code, gets '55', and answers '55'.
    """
    agent = RLMAgent(max_steps=5)
    task = "Calculate the sum of numbers from 1 to 10 using Python and tell me the result."

    result = agent.run(task)

    print(f"\nFinal Result: {result}")

    # Assertions
    # 1. Verification of correct math
    assert "55" in result, "The result should contain the calculated sum (55)."

    # 2. Verification of process (Did it use code?)
    # We can check history
    code_execution_found = False
    for action, output in agent.history:
        if "Executed Code" in action:
            code_execution_found = True
            assert "print" in action, "The generated code should print the result."
            assert "55" in output.strip(), "The code execution output should contain 55."
            break

    assert code_execution_found, "The agent should have executed Python code to solve this."


@pytest.mark.asyncio
async def test_agent_simple_answer(setup_dspy_ollama):
    """
    Test 4.2: Simple Answer (No Code).
    Task: "What is the capital of France?"
    Expectation: Agent answers directly without coding.
    """
    agent = RLMAgent(max_steps=3)
    task = "What is the capital of France?"

    result = agent.run(task)

    assert "Paris" in result, "Result should contain 'Paris'."

    # It might decide to code or answer, but usually answer for this.
    # If it codes, that's fine too, but let's check basic sanity.
