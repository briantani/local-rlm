import pytest
import dspy
from src.core.agent import RLMAgent
from src.config import get_lm

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
