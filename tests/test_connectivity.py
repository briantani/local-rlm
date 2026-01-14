import pytest
import dspy
import os
from tests.conftest import get_lm_for_testing
from src.core.budget import BudgetWrapper

def test_get_lm_gemini():
    """Test that we can initialize the Gemini provider."""
    # We don't actually call the API here to avoid cost/auth issues in unit tests unless integration testing
    # But the plan says "verify we can talk to...". So we should probably try a real call if the key is present.
    # For now, let's just check instantiation.
    try:
        lm = get_lm_for_testing("gemini")
        # It should be wrapped now
        assert isinstance(lm, BudgetWrapper)
        # And the underlying LM should be dspy.LM
        assert isinstance(lm.lm, dspy.LM)
    except ValueError as e:
        pytest.skip(f"Skipping Gemini test: {e}")

def test_get_lm_ollama():
    """Test that we can initialize the Ollama provider."""
    lm = get_lm_for_testing("ollama")
    assert isinstance(lm, BudgetWrapper)
    assert isinstance(lm.lm, dspy.LM)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_connectivity_ollama():
    """Test actual connectivity to Ollama."""
    try:
        lm = get_lm_for_testing("ollama")
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
@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="No Gemini API key")
def test_connectivity_gemini():
    """Test actual connectivity to Gemini."""
    try:
        lm = get_lm_for_testing("gemini")
        dspy.settings.configure(lm=lm)
        response = lm("Say 'Hello World'")
        assert response is not None
    except Exception as e:
        # If we hit a rate limit, we consider connectivity verified (we reached the server)
        # Gemini Free tier often hits this.
        if "Quota exceeded" in str(e) or "429" in str(e) or "RateLimitError" in str(e):
            pytest.skip(f"Gemini Rate Limit hit (Connectivity verified): {e}")
        else:
            pytest.fail(f"Gemini connectivity failed: {e}")
    assert len(response) > 0
    print(f"Gemini response: {response}")
