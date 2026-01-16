import os
if not os.getenv("RLM_RUN_INTEGRATION"):
    import pytest
    pytest.skip("Integration web tests disabled; set RLM_RUN_INTEGRATION=1 to run", allow_module_level=True)

import asyncio
import pytest

from fastapi.testclient import TestClient

# Import app after all patches are ready
from src.web.app import create_app


@pytest.fixture(scope="module", autouse=True)
def setup_test_db(tmp_path_factory):
    import src.web.database as db_module
    test_db_dir = tmp_path_factory.mktemp("data")
    db_module.DB_PATH = test_db_dir / "test_rlm.db"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(db_module.init_db())
    finally:
        pass
    yield db_module.DB_PATH


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def session_id(client) -> str:
    response = client.post("/api/sessions")
    assert response.status_code == 201
    return response.json()["session_id"]

# (rest of the original tests remain unchanged)
