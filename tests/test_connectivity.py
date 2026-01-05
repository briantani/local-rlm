import pytest
import dspy
import os
from src.config import get_lm

def test_get_lm_gemini():
    """Test that we can initialize the Gemini provider."""
    # We don't actually call the API here to avoid cost/auth issues in unit tests unless integration testing
    # But the plan says "verify we can talk to...". So we should probably try a real call if the key is present.
    # For now, let's just check instantiation.
    try:
        lm = get_lm("gemini")
        assert isinstance(lm, dspy.LM)
    except ValueError as e:
        pytest.skip(f"Skipping Gemini test: {e}")

def test_get_lm_ollama():
    """Test that we can initialize the Ollama provider."""
    lm = get_lm("ollama")
    assert isinstance(lm, dspy.LM)

@pytest.mark.asyncio
async def test_connectivity_ollama():
    """Test actual connectivity to Ollama."""
    try:
        lm = get_lm("ollama")
        dspy.settings.configure(lm=lm)
        # Simple generation
        response = lm("Say 'Hello World'")
        assert response is not None
        assert len(response) > 0
        print(f"Ollama response: {response}")
    except Exception as e:
        pytest.fail(f"Ollama connectivity failed: {e}")

# We skip Gemini connectivity test by default to avoid needing a real key in CI/automated runs
# unless the user specifically wants to run it.
@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="No Gemini API key")
def test_connectivity_gemini():
    """Test actual connectivity to Gemini."""
    lm = get_lm("gemini")
    dspy.settings.configure(lm=lm)
    response = lm("Say 'Hello World'")
    assert response is not None
    assert len(response) > 0
    print(f"Gemini response: {response}")
