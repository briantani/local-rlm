import pytest
from src.core.explorer import scan_directory
from src.config import get_lm
import dspy

@pytest.fixture(scope="module")
def setup_dspy_ollama():
    try:
        # We try to use a slightly smarter model for code/reasoning if possible, but default is fine
        lm = get_lm("ollama")
        dspy.settings.configure(lm=lm)
        return lm
    except Exception as e:
        pytest.skip(f"Skipping Context tests: {e}")

def test_scan_directory(tmp_path):
    # Setup temp directory structure
    d1 = tmp_path / "sub"
    d1.mkdir()
    (d1 / "test.txt").write_text("hello")
    (tmp_path / "root.py").write_text("print('hi')")

    # Run scan
    result = scan_directory(tmp_path)

    # Assert
    assert "Directory listing for:" in result
    assert "[DIR]  sub" in result or "[DIR] sub" in result # Handling potential spacing
    assert "[FILE] sub/test.txt" in result
    assert "[FILE] root.py" in result
    assert "sub/test.txt" in result

@pytest.mark.asyncio
async def test_agent_can_see_files(tmp_path, setup_dspy_ollama):
    """
    Test 6.2: Agent perceives files and generates code to read them.
    """
    from src.core.agent import RLMAgent

    # Create a secret file
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("The secret code is 12345.")

    agent = RLMAgent(max_steps=3, root_dir=tmp_path)

    # Run agent
    # We expect the agent to:
    # 1. See secret.txt in context.
    # 2. Architect -> CODE.
    # 3. Coder -> print(open('secret.txt').read()).
    # 4. REPL output -> "The secret code is 12345."
    # 5. Architect -> ANSWER.

    res = agent.run("What is the secret code in secret.txt?")

    assert "12345" in res

