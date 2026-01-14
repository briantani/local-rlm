import os
import pytest
import httpx


@pytest.mark.integration
def test_ollama_server_listening():
    """Integration test: ensure local Ollama server is reachable.

    This test is marked as integration and should only be run when
    `RLM_RUN_INTEGRATION=1` is set in the environment or when explicitly
    requested by CI. It validates that the server responds to the models
    endpoint.
    """
    if not os.getenv("RLM_RUN_INTEGRATION"):
        pytest.skip("Skipping integration test: RLM_RUN_INTEGRATION not set")

    try:
        resp = httpx.get("http://localhost:11434/v1/models", timeout=5.0)
        assert resp.status_code == 200
        assert resp.json() is not None
    except Exception as e:
        pytest.fail(f"Ollama server not reachable: {e}")
