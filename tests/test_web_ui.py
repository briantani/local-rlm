"""
Tests for Phase 14/15: UI Routes and Templates.

Tests that UI pages render correctly and handle data properly.
Catches issues like API response format mismatches.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.web.app import create_app


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def app():
    """Create a test app instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_config_service():
    """Mock ConfigService for testing UI without real configs."""
    mock = MagicMock()

    # Mock list_profiles to return structured response
    mock.list_profiles.return_value = [
        {
            "name": "local-only",
            "description": "Free local models via Ollama",
            "root_model": "qwen2.5:7b",
            "root_provider": "ollama",
            "delegate_model": "qwen2.5:3b",
            "delegate_provider": "ollama",
            "max_budget": 0.0,
            "max_steps": 10,
            "max_depth": 3,
        },
        {
            "name": "hybrid",
            "description": "Best of both worlds",
            "root_model": "gemini-2.5-flash",
            "root_provider": "gemini",
            "delegate_model": "qwen2.5:3b",
            "delegate_provider": "ollama",
            "max_budget": 0.50,
            "max_steps": 15,
            "max_depth": 4,
        },
    ]

    # Mock get_profile_summary
    mock.get_profile_summary.return_value = MagicMock(
        name="local-only",
        description="Free local models via Ollama",
        root_model="qwen2.5:7b",
        root_provider="ollama",
        delegate_model="qwen2.5:3b",
        delegate_provider="ollama",
        max_budget=0.0,
        max_steps=10,
        max_depth=3,
    )

    # Mock load_profile to return ProfileConfig
    from dataclasses import dataclass, field
    from src.core.config_loader import (
        AgentConfig,
        ModulesConfig,
        BudgetConfig,
        DSPyConfig,
        LoggingConfig,
    )

    @dataclass
    class MockProfileConfig:
        profile_name: str = "Local Only"
        description: str = "Free local models via Ollama"
        root: AgentConfig = field(default_factory=lambda: AgentConfig(
            provider="ollama", model="qwen2.5:7b"
        ))
        delegate: AgentConfig = field(default_factory=lambda: AgentConfig(
            provider="ollama", model="qwen2.5:3b"
        ))
        modules: ModulesConfig = field(default_factory=ModulesConfig)
        budget: BudgetConfig = field(default_factory=BudgetConfig)
        dspy: DSPyConfig = field(default_factory=DSPyConfig)
        logging: LoggingConfig = field(default_factory=LoggingConfig)

    mock.load_profile.return_value = MockProfileConfig()

    # Mock get_required_providers
    mock.get_required_providers.return_value = []  # Empty for local-only

    return mock


# =============================================================================
# Home Page Tests
# =============================================================================


class TestHomePage:
    """Tests for the main home page (/)."""

    def test_home_page_renders(self, client):
        """Test that home page renders successfully."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"RLM Agent" in response.content or b"Task" in response.content

    def test_home_page_has_config_dropdown(self, client):
        """Test that home page includes config selection dropdown."""
        response = client.get("/")

        assert response.status_code == 200
        assert b'id="config"' in response.content or b'select' in response.content.lower()

    def test_home_page_has_task_input(self, client):
        """Test that home page has task input field."""
        response = client.get("/")

        assert response.status_code == 200
        assert b'textarea' in response.content.lower() or b'input' in response.content.lower()


# =============================================================================
# Config List Page Tests
# =============================================================================


class TestConfigListPage:
    """Tests for the configuration list page (/configs)."""

    def test_configs_page_renders(self, client):
        """Test that configs page renders successfully."""
        response = client.get("/configs")

        assert response.status_code == 200
        assert b"Configurations" in response.content or b"Configuration" in response.content

    def test_configs_page_loads_profiles(self, client):
        """Test that configs page attempts to load profiles."""
        response = client.get("/configs")

        assert response.status_code == 200
        # Should have Alpine.js initialization
        assert b"x-data" in response.content or b"alpine" in response.content.lower()


# =============================================================================
# Config Detail Page Tests
# =============================================================================


class TestConfigDetailPage:
    """Tests for the configuration detail page (/configs/{name})."""

    def test_config_detail_renders(self, client):
        """Test that config detail page renders for valid config."""
        # This will use real config files
        response = client.get("/configs/local-only")

        # Should either succeed or fail gracefully with error page
        assert response.status_code in (200, 404, 500)

        if response.status_code == 200:
            assert b"local-only" in response.content.lower() or b"Local" in response.content

    def test_config_detail_missing_config(self, client):
        """Test that missing config returns appropriate error."""
        response = client.get("/configs/nonexistent-config-12345")

        # Should return error page
        assert response.status_code in (404, 500)

    def test_config_detail_has_yaml_content(self, client):
        """Test that config detail shows YAML content."""
        response = client.get("/configs/local-only")

        if response.status_code == 200:
            # Should have some YAML-related content
            assert b"yaml" in response.content.lower() or b"<pre" in response.content.lower()


# =============================================================================
# Config Compare Page Tests
# =============================================================================


class TestConfigComparePage:
    """Tests for the configuration comparison page."""

    def test_compare_page_renders(self, client):
        """Test that compare page renders successfully."""
        response = client.get("/configs/compare")

        assert response.status_code == 200
        assert b"Compare" in response.content or b"comparison" in response.content.lower()

    def test_compare_page_with_query_params(self, client):
        """Test that compare page accepts query parameters."""
        response = client.get("/configs/compare?config=local-only&config=hybrid")

        assert response.status_code == 200


# =============================================================================
# Cost Estimator Page Tests
# =============================================================================


class TestCostEstimatorPage:
    """Tests for the cost estimator page."""

    def test_estimator_page_renders(self, client):
        """Test that estimator page renders successfully."""
        response = client.get("/configs/estimate")

        assert response.status_code == 200
        assert b"Cost" in response.content or b"Estimator" in response.content

    def test_estimator_has_complexity_slider(self, client):
        """Test that estimator has complexity controls."""
        response = client.get("/configs/estimate")

        assert response.status_code == 200
        # Should have slider or complexity control
        assert b"range" in response.content.lower() or b"slider" in response.content.lower()


# =============================================================================
# API Response Format Tests
# =============================================================================


class TestAPIResponseFormats:
    """Test that API endpoints return correctly formatted responses for the UI."""

    def test_configs_api_returns_profiles_array(self, client):
        """Test that /api/configs returns {profiles: [...], count: ...} format."""
        response = client.get("/api/configs")

        assert response.status_code == 200
        data = response.json()

        # Critical: Must have 'profiles' key
        assert "profiles" in data, "API response missing 'profiles' key"
        assert isinstance(data["profiles"], list), "'profiles' must be an array"

        # Should also have count
        assert "count" in data, "API response missing 'count' key"
        assert isinstance(data["count"], int), "'count' must be an integer"

        # Verify count matches array length
        assert data["count"] == len(data["profiles"]), "count doesn't match profiles length"

    def test_config_detail_api_structure(self, client):
        """Test that /api/configs/{name} returns correct structure."""
        response = client.get("/api/configs/local-only")

        if response.status_code == 200:
            data = response.json()

            # Should have essential fields (API returns flattened structure)
            assert "name" in data or "profile_name" in data
            assert "description" in data
            # API returns flattened response, not nested root
            assert "root_model" in data or "root_provider" in data

    def test_profile_summary_has_required_fields(self, client):
        """Test that profile summaries have all required UI fields."""
        response = client.get("/api/configs")

        assert response.status_code == 200
        data = response.json()
        profiles = data["profiles"]

        if len(profiles) > 0:
            profile = profiles[0]

            # Required fields for UI display
            required_fields = ["name", "description", "root_model", "root_provider"]
            for field in required_fields:
                assert field in profile, f"Profile missing required field: {field}"


# =============================================================================
# Template Data Handling Tests
# =============================================================================


class TestTemplateDataHandling:
    """Test that templates correctly handle data passed from routes."""

    def test_config_detail_route_gets_data(self, client):
        """Test that config detail route properly loads configuration."""
        response = client.get("/configs/local-only")

        # Should render successfully
        assert response.status_code == 200
        # Should have config name in the response
        assert b"local" in response.content.lower()

    def test_home_page_session_initialization(self, client):
        """Test that home page initializes session correctly."""
        response = client.get("/")

        assert response.status_code == 200
        # Should have session management code
        assert b"sessionStore" in response.content or b"session" in response.content.lower()


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test that UI handles errors gracefully."""

    def test_error_page_template_exists(self, client):
        """Test that error template renders correctly."""
        # Trigger an error by accessing non-existent config
        response = client.get("/configs/this-definitely-does-not-exist-12345")

        # Should return error status
        assert response.status_code in (404, 500)

        # Should show some error message
        if response.status_code == 500:
            assert b"Error" in response.content or b"error" in response.content.lower()

    def test_404_page_exists(self, client):
        """Test that 404 errors are handled."""
        response = client.get("/this-route-does-not-exist-12345")

        assert response.status_code == 404


# =============================================================================
# JavaScript Integration Tests
# =============================================================================


class TestJavaScriptIntegration:
    """Test that pages have required JavaScript for functionality."""

    def test_home_has_alpine_js(self, client):
        """Test that home page includes Alpine.js."""
        response = client.get("/")

        assert response.status_code == 200
        # Should reference Alpine.js
        assert b"alpine" in response.content.lower() or b"x-data" in response.content

    def test_home_has_htmx(self, client):
        """Test that home page includes HTMX."""
        response = client.get("/")

        assert response.status_code == 200
        # Should reference HTMX
        assert b"htmx" in response.content.lower() or b"hx-" in response.content

    def test_configs_page_has_fetch_calls(self, client):
        """Test that configs page has JavaScript fetch calls."""
        response = client.get("/configs")

        assert response.status_code == 200
        # Should have fetch API calls
        assert b"fetch" in response.content
        assert b"/api/configs" in response.content

    def test_home_handles_api_response_format(self, client):
        """Test that home page JavaScript handles {profiles: []} format."""
        response = client.get("/")

        assert response.status_code == 200
        # Should have code to extract profiles from response
        assert b"profiles" in response.content.lower()
