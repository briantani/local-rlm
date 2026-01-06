"""
Tests for Phase 13: FastAPI Backend.

Tests REST endpoints, WebSocket streaming, and database persistence.
"""

import asyncio
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from fastapi.testclient import TestClient

# Import app after all patches are ready
from src.web.app import create_app
from src.web.database import (
    TaskRecord,
    TaskStatus,
    init_db,
    create_task,
    get_task,
    get_tasks_for_session,
    update_task_status,
    DB_PATH,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def setup_test_db(tmp_path_factory):
    """Setup test database for all tests in module."""
    import src.web.database as db_module

    # Use a temp path for all tests
    test_db_dir = tmp_path_factory.mktemp("data")
    db_module.DB_PATH = test_db_dir / "test_rlm.db"

    # Initialize DB synchronously using new event loop
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(db_module.init_db())
    finally:
        pass  # Keep loop for test usage

    yield db_module.DB_PATH


@pytest.fixture
def app():
    """Create a test app instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def session_id(client) -> str:
    """Create a session and return its ID."""
    response = client.post("/api/sessions")
    assert response.status_code == 201
    return response.json()["session_id"]


@pytest_asyncio.fixture
async def test_db(tmp_path):
    """Initialize a test database for async tests."""
    # Override DB_PATH for testing
    import src.web.database as db_module
    original_path = db_module.DB_PATH
    db_module.DB_PATH = tmp_path / "test_rlm.db"

    await init_db()

    yield db_module.DB_PATH

    # Restore original path
    db_module.DB_PATH = original_path


# =============================================================================
# Session Endpoint Tests
# =============================================================================


class TestSessionEndpoints:
    """Tests for /api/sessions endpoints."""

    def test_create_session(self, client):
        """Test creating a new session."""
        response = client.post("/api/sessions")

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 10

    def test_set_api_key(self, client, session_id):
        """Test setting an API key."""
        response = client.put(
            f"/api/sessions/{session_id}/keys",
            json={"provider": "gemini", "api_key": "test-key-123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["provider"] == "gemini"

    def test_set_api_key_invalid_session(self, client):
        """Test setting API key for non-existent session."""
        response = client.put(
            "/api/sessions/invalid-session-id/keys",
            json={"provider": "gemini", "api_key": "test-key"},
        )

        assert response.status_code == 404

    def test_set_api_key_invalid_provider(self, client, session_id):
        """Test setting API key for invalid provider."""
        response = client.put(
            f"/api/sessions/{session_id}/keys",
            json={"provider": "invalid-provider", "api_key": "test-key"},
        )

        assert response.status_code == 400

    def test_get_api_key_status(self, client, session_id):
        """Test checking API key status."""
        # Set a key first
        client.put(
            f"/api/sessions/{session_id}/keys",
            json={"provider": "gemini", "api_key": "test-key"},
        )

        response = client.get(f"/api/sessions/{session_id}/keys/status")

        assert response.status_code == 200
        data = response.json()
        assert "gemini" in data["configured_providers"]

    def test_get_api_key_status_with_profile(self, client, session_id):
        """Test checking API key status for a specific profile."""
        response = client.get(
            f"/api/sessions/{session_id}/keys/status",
            params={"profile": "cost-effective"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "missing_for_profile" in data

    def test_delete_session(self, client, session_id):
        """Test deleting a session."""
        response = client.delete(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Session should no longer exist
        response = client.get(f"/api/sessions/{session_id}/keys/status")
        assert response.status_code == 404


# =============================================================================
# Config Endpoint Tests
# =============================================================================


class TestConfigEndpoints:
    """Tests for /api/configs endpoints."""

    def test_list_profiles(self, client):
        """Test listing all profiles."""
        response = client.get("/api/configs")

        assert response.status_code == 200
        data = response.json()
        assert "profiles" in data
        assert data["count"] > 0

        # Check profile structure
        profile = data["profiles"][0]
        assert "name" in profile
        assert "root_model" in profile
        assert "max_budget" in profile

    def test_get_profile(self, client):
        """Test getting a specific profile."""
        response = client.get("/api/configs/cost-effective")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "cost-effective"
        assert "is_valid" in data
        assert "validation_errors" in data

    def test_get_profile_not_found(self, client):
        """Test getting a non-existent profile."""
        response = client.get("/api/configs/nonexistent-profile")

        assert response.status_code == 404

    def test_estimate_cost(self, client):
        """Test cost estimation."""
        response = client.get(
            "/api/configs/cost-effective/estimate",
            params={"input_tokens": 10000, "output_tokens": 2000, "steps": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert "estimated_cost" in data
        assert "max_budget" in data


# =============================================================================
# Task Endpoint Tests
# =============================================================================


class TestTaskEndpoints:
    """Tests for /api/tasks endpoints."""

    def test_create_task_requires_session(self, client):
        """Test that creating a task requires a session header."""
        response = client.post(
            "/api/tasks",
            json={"task": "test", "config_name": "cost-effective"},
        )

        # Should fail without X-Session-ID header
        assert response.status_code == 422  # Validation error

    def test_create_task_invalid_session(self, client):
        """Test that invalid session is rejected."""
        response = client.post(
            "/api/tasks",
            json={"task": "test", "config_name": "cost-effective"},
            headers={"X-Session-ID": "invalid-session"},
        )

        assert response.status_code == 401

    def test_create_task_missing_api_keys(self, client, session_id):
        """Test that task creation fails without required API keys."""
        response = client.post(
            "/api/tasks",
            json={"task": "test", "config_name": "cost-effective"},
            headers={"X-Session-ID": session_id},
        )

        assert response.status_code == 400
        assert "Missing API keys" in response.json()["detail"]

    def test_create_task_success(self, client, session_id):
        """Test successful task creation with mocked execution."""
        # Set required API key
        client.put(
            f"/api/sessions/{session_id}/keys",
            json={"provider": "gemini", "api_key": "test-key"},
        )

        # Mock the task runner to avoid actual execution
        with patch("src.web.routes.tasks.run_task_async"):
            response = client.post(
                "/api/tasks",
                json={"task": "What is 2+2?", "config_name": "cost-effective"},
                headers={"X-Session-ID": session_id},
            )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert "/ws/tasks/" in data["websocket_url"]

    def test_list_tasks_empty(self, client, session_id):
        """Test listing tasks when none exist."""
        response = client.get(
            "/api/tasks",
            headers={"X-Session-ID": session_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"] == []
        assert data["count"] == 0

    def test_get_task_not_found(self, client, session_id):
        """Test getting a non-existent task."""
        response = client.get(
            "/api/tasks/nonexistent-task",
            headers={"X-Session-ID": session_id},
        )

        assert response.status_code == 404


# =============================================================================
# Database Tests
# =============================================================================


class TestDatabase:
    """Tests for SQLite database operations."""

    @pytest.mark.asyncio
    async def test_create_and_get_task(self, test_db):
        """Test creating and retrieving a task."""
        task = await create_task(
            task_id="test-task-1",
            session_id="session-1",
            task_text="Test task",
            config_name="cost-effective",
        )

        assert task.id == "test-task-1"
        assert task.status == TaskStatus.PENDING

        retrieved = await get_task("test-task-1")
        assert retrieved is not None
        assert retrieved.task_text == "Test task"

    @pytest.mark.asyncio
    async def test_update_task_status(self, test_db):
        """Test updating task status."""
        await create_task(
            task_id="test-task-2",
            session_id="session-1",
            task_text="Test",
            config_name="test",
        )

        await update_task_status("test-task-2", TaskStatus.RUNNING)

        task = await get_task("test-task-2")
        assert task.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_update_task_with_result(self, test_db):
        """Test updating task with result data."""
        await create_task(
            task_id="test-task-3",
            session_id="session-1",
            task_text="Test",
            config_name="test",
        )

        result_data = {"answer": "42", "cost": 0.001}
        await update_task_status("test-task-3", TaskStatus.COMPLETED, result_data)

        task = await get_task("test-task-3")
        assert task.status == TaskStatus.COMPLETED
        assert task.result["answer"] == "42"
        assert task.completed_at is not None

    @pytest.mark.asyncio
    async def test_get_tasks_for_session(self, test_db):
        """Test getting tasks for a specific session."""
        # Create tasks for different sessions
        await create_task("task-a", "session-a", "Task A", "config")
        await create_task("task-b", "session-a", "Task B", "config")
        await create_task("task-c", "session-b", "Task C", "config")

        tasks = await get_tasks_for_session("session-a")

        assert len(tasks) == 2
        task_ids = [t.id for t in tasks]
        assert "task-a" in task_ids
        assert "task-b" in task_ids
        assert "task-c" not in task_ids


# =============================================================================
# Health Check Test
# =============================================================================


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
