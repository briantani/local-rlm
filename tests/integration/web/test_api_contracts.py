import os
if not os.getenv("RLM_RUN_INTEGRATION"):
    import pytest
    pytest.skip("Integration web tests disabled; set RLM_RUN_INTEGRATION=1 to run", allow_module_level=True)

import pytest
from fastapi.testclient import TestClient

from src.web.app import app

client = TestClient(app)

pytestmark = pytest.mark.integration

class TestConfigsAPIContracts:
    def test_list_profiles_returns_correct_structure(self):
        response = client.get("/api/configs")
        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert "count" in data
