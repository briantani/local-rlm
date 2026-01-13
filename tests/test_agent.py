import pytest
import dspy
from src.core.agent import RLMAgent
from tests.conftest import MockArchitect, MockCoder, MockResponder, MockREPL


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
    from tests.conftest import get_lm_for_testing
    try:
        lm = get_lm_for_testing("ollama")
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


# ============================================================================
# PAPER-STYLE METADATA TESTS (MIT RLM Paper Implementation)
# ============================================================================

class TestPaperStyleContextHandling:
    """Tests for the paper-style metadata approach that prevents context overflow."""

    def test_format_context_metadata_empty(self):
        """Test metadata format when no execution history exists."""
        agent = RLMAgent(max_steps=3)
        metadata = agent.format_context_metadata()

        # Should contain basic info, not be empty
        assert "Execution History" in metadata or "0 steps" in metadata

    def test_format_context_metadata_with_history(self):
        """Test metadata accurately reflects execution history."""
        mock_repl = MockREPL(output="42")
        agent = RLMAgent(max_steps=3, repl=mock_repl)

        # Simulate execution history
        mock_repl.add_history_entry("x = 1", "1", step=1)
        mock_repl.add_history_entry("y = 2", "22", step=2)

        metadata = agent.format_context_metadata()
        assert "2 steps" in metadata
        assert "chars" in metadata

    def test_format_context_metadata_excludes_full_content(self):
        """Critical: Metadata must NOT contain actual execution content."""
        mock_repl = MockREPL(output="X" * 10000)
        agent = RLMAgent(max_steps=3, repl=mock_repl)

        # Add large content to history
        mock_repl.add_history_entry("big_code", "X" * 10000, step=1)

        metadata = agent.format_context_metadata()
        # Metadata should be short, not contain the 10KB
        assert len(metadata) < 500
        assert "XXXXXXXXXX" not in metadata  # Full content should NOT be present

    def test_get_last_output_preview_empty(self):
        """Test preview returns empty when no history."""
        mock_repl = MockREPL(output="")
        agent = RLMAgent(max_steps=3, repl=mock_repl)

        preview = agent.get_last_output_preview()
        assert preview == ""

    def test_get_last_output_preview_with_history(self):
        """Test preview includes truncated last output."""
        mock_repl = MockREPL(output="result")
        agent = RLMAgent(max_steps=3, repl=mock_repl)

        mock_repl.add_history_entry("print(42)", "42", step=1)

        preview = agent.get_last_output_preview()
        assert "42" in preview

    def test_architect_receives_metadata_not_full_context(self):
        """Test that Architect receives metadata, not full execution content."""
        large_output = "Y" * 5000
        mock_repl = MockREPL(output=large_output)

        # Track what architect receives
        architect_inputs = []
        def tracking_architect(**kwargs):
            architect_inputs.append(kwargs)
            return type('Pred', (), {'action': 'ANSWER'})()

        mock_architect = type('Mock', (), {'__call__': lambda self, **kw: tracking_architect(**kw)})()
        mock_responder = MockResponder(response="Done")

        agent = RLMAgent(
            max_steps=3,
            architect=mock_architect,
            responder=mock_responder,
            repl=mock_repl,
        )

        # Pre-populate history with large content
        mock_repl.add_history_entry("code", large_output, step=1)

        agent.run("Test query")

        # Architect should have received metadata, not the 5KB output
        assert len(architect_inputs) >= 1
        data_desc = architect_inputs[0].get('data_desc', '')
        assert len(data_desc) < 1000  # Should be much smaller than 5KB
        assert "YYYYY" not in data_desc or len(data_desc) < 1000  # Not full content

    def test_coder_receives_metadata_not_full_context(self):
        """Test that Coder receives metadata, not full execution content."""
        large_output = "Z" * 5000
        mock_repl = MockREPL(output=large_output)

        # Track what coder receives
        coder_inputs = []
        def tracking_coder(**kwargs):
            coder_inputs.append(kwargs)
            return type('Pred', (), {'python_code': 'print(1)'})()

        mock_coder = type('Mock', (), {'__call__': lambda self, **kw: tracking_coder(**kw)})()
        mock_responder = MockResponder(response="Done")

        # Architect returns CODE first, then ANSWER
        call_count = [0]
        def dynamic_architect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return type('Pred', (), {'action': 'CODE'})()
            return type('Pred', (), {'action': 'ANSWER'})()

        mock_architect = type('Mock', (), {'__call__': lambda self, **kw: dynamic_architect(**kw)})()

        agent = RLMAgent(
            max_steps=3,
            architect=mock_architect,
            coder=mock_coder,
            responder=mock_responder,
            repl=mock_repl,
        )

        # Pre-populate history with large content
        mock_repl.add_history_entry("code", large_output, step=1)

        agent.run("Test query")

        # Coder should have received metadata, not the 5KB output
        assert len(coder_inputs) >= 1
        context_summary = coder_inputs[0].get('context_summary', '')
        assert len(context_summary) < 1000  # Should be much smaller than 5KB

    def test_context_overflow_prevention(self):
        """Integration test: Verify large history doesn't overflow context."""
        mock_repl = MockREPL(output="ok")

        # Simulate many steps with large outputs
        for i in range(20):
            mock_repl.add_history_entry(f"step_{i}", "X" * 1000, step=i + 1)

        # Total content: 20 * 1000 = 20KB
        # Metadata should still be tiny
        mock_responder = MockResponder(response="Final answer")
        mock_architect = MockArchitect(action="ANSWER")

        agent = RLMAgent(
            max_steps=3,
            architect=mock_architect,
            responder=mock_responder,
            repl=mock_repl,
        )

        metadata = agent.format_context_metadata()
        assert len(metadata) < 500  # Metadata stays small regardless of history size
        assert "20 steps" in metadata  # But accurately reflects the count
