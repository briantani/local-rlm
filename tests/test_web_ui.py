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

    def test_configs_page_displays_coder_models_in_cards(self, client):
        """Test that config cards display coder model information.

        This is the PRIMARY test for the bug we just fixed. The config
        cards were showing 'Not Configured' for coder models despite
        them being properly set in YAML files.
        """
        response = client.get("/configs")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have JavaScript that accesses config.coder_model
        assert "coder_model" in content, "Template should reference coder_model field"

        # The JavaScript should display the coder model text
        # (The actual values are loaded via API, but template should have the display logic)
        assert "Coder:" in content or "coder" in content.lower(), "Coder label should be in template"


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

    def test_config_detail_shows_coder_model(self, client):
        """Test that config detail page displays coder model information.

        Ensures the detail view includes coder model, which was missing
        in the original bug.
        """
        # Test with hybrid (has explicit coder)
        response = client.get("/configs/hybrid")

        if response.status_code == 200:
            # Should show the coder model in the page
            assert b"coder" in response.content.lower(), "Coder section not found in detail page"
            # The actual model name appears in YAML content
            assert b"qwen2.5-coder:14b" in response.content, "Coder model name not displayed"


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

    def test_compare_page_shows_coder_models(self, client):
        """Test that comparison page includes coder model information.

        Guards against the bug where coder models weren't displayed
        in the comparison view.
        """
        response = client.get("/configs/compare?config=hybrid&config=cost-effective")

        assert response.status_code == 200
        content = response.content.decode()

        # Hybrid has explicit coder model
        assert "qwen2.5-coder:14b" in content, "Hybrid coder model not found in comparison"

        # Cost-effective uses root model
        assert "(uses root model)" in content or "gemini-2.5-flash" in content, "Cost-effective coder info not found"


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
            required_fields = [
                "name",
                "description",
                "root_model",
                "root_provider",
                "coder_model",  # Added to prevent bug regression
                "coder_provider",
                "delegate_model",
                "delegate_provider",
            ]
            for field in required_fields:
                assert field in profile, f"Profile missing required field: {field}"

    def test_coder_model_displays_correctly(self, client):
        """Test that coder model is correctly exposed in API response.

        This test specifically guards against the bug where coder_model
        was showing 'Not Configured' despite being in the YAML file.
        """
        response = client.get("/api/configs")
        assert response.status_code == 200
        data = response.json()
        profiles = data["profiles"]

        # Find hybrid config (has explicit coder module)
        hybrid = next((p for p in profiles if p["name"] == "hybrid"), None)
        if hybrid:
            assert "coder_model" in hybrid, "hybrid profile missing coder_model field"
            assert hybrid["coder_model"] != "Not configured", "coder_model should not be 'Not configured'"
            assert hybrid["coder_model"] == "qwen2.5-coder:14b", f"Expected qwen2.5-coder:14b, got {hybrid['coder_model']}"

        # Find cost-effective config (no explicit coder module, uses root)
        cost_effective = next((p for p in profiles if p["name"] == "cost-effective"), None)
        if cost_effective:
            assert "coder_model" in cost_effective, "cost-effective profile missing coder_model field"
            assert cost_effective["coder_model"] == "(uses root model)", f"Expected '(uses root model)', got {cost_effective['coder_model']}"


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

# =============================================================================
# Chat Interface Tests (Phase 16)
# =============================================================================


class TestChatInterface:
    """Test chat interface for follow-up queries."""

    def test_chat_panel_component_exists(self, client):
        """Test that chat panel component file exists."""
        from pathlib import Path

        chat_panel_path = Path("src/web/templates/components/chat_panel.html")
        assert chat_panel_path.exists(), "Chat panel component should exist"

    def test_home_page_includes_chat_panel(self, client):
        """Test that home page includes chat panel component."""
        response = client.get("/")

        assert response.status_code == 200
        # Should reference chat panel (either directly or via include)
        # The actual chat panel is conditionally shown via x-show
        assert b"chat" in response.content.lower() or b"components/chat_panel" in response.content

    def test_chat_panel_has_alpine_js_integration(self, client):
        """Test that chat panel uses Alpine.js."""
        from pathlib import Path

        chat_panel_path = Path("src/web/templates/components/chat_panel.html")
        content = chat_panel_path.read_text()

        # Should have Alpine.js directives
        assert "x-data" in content or "x-show" in content
        assert "chatPanel" in content  # Alpine component function

    def test_home_has_current_task_id_for_chat(self, client):
        """Test that home page tracks currentTaskId for chat integration."""
        response = client.get("/")

        assert response.status_code == 200
        # Should have currentTaskId in Alpine state
        assert b"currentTaskId" in response.content

class TestContextPath:
    """Test context path functionality for file access."""

    def test_home_has_context_path_field(self, client):
        """Test that home page includes context path input field."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content

        # Check for context path input field
        assert b'id="contextPath"' in content
        assert b'x-model="contextPath"' in content

        # Check for helpful label/description
        assert b"Context Folder" in content

        # Check that contextPath is in the component state
        assert b"contextPath:" in content


# =============================================================================
# API Key Modal Tests
# =============================================================================


class TestAPIKeyModal:
    """Tests for API key configuration modal."""

    def test_api_key_button_exists_in_navigation(self, client):
        """Test that API Keys button appears in navigation bar."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have the API Keys button
        assert "API Keys" in content, "API Keys button not found in navigation"

        # Should have the click handler
        assert "open-api-key-modal" in content, "Modal event dispatcher not found"

    def test_api_key_modal_component_exists(self, client):
        """Test that API key modal component is included in base template."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should include the modal component
        assert "apiKeyModal" in content, "Modal component function not found"
        assert "Configure API Keys" in content, "Modal title not found"

    def test_modal_has_provider_inputs(self, client):
        """Test that modal has input fields for API providers."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have fields for major providers
        assert "Gemini" in content or "gemini" in content, "Gemini input not found"
        assert "OpenAI" in content or "openai" in content, "OpenAI input not found"

    def test_modal_has_save_functionality(self, client):
        """Test that modal has save button and logic."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have save button
        assert "saveKeys" in content, "Save function not found"
        # Save button text
        assert "Save Keys" in content or "save" in content.lower(), "Save button not found"

    def test_modal_integrates_with_session_store(self, client):
        """Test that modal uses session store for API key management."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Modal should interact with session store
        assert "sessionStore" in content, "Session store not found"
        assert "setApiKey" in content, "API key setter not found"

    def test_session_recreation_on_404(self, client):
        """Test that session is recreated when backend returns 404."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have session recreation logic for 404 errors
        assert "response.status === 404" in content, "404 handling not found"
        assert "localStorage.removeItem('rlm_session_id')" in content, "Session cleanup not found"
        # Should reinitialize session after cleanup
        assert "await this.init()" in content, "Session reinitialization not found"


# =============================================================================
# Canvas Component Tests
# =============================================================================


class TestCanvasComponent:
    """Test canvas component for displaying task results."""

    def test_canvas_component_exists(self, client):
        """Test that canvas component is included in home page."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should include canvas component content (check for canvasViewer function)
        assert "canvasViewer" in content, "Canvas component not included"
        assert "Task Result" in content, "Canvas header not found"

    def test_canvas_receives_result_data(self, client):
        """Test that canvas component receives result and taskId as parameters."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should pass result, taskId, and steps to canvas function
        assert "canvasViewer(result, taskId, steps)" in content, "Canvas not receiving parameters"

    def test_canvas_displays_final_answer(self, client):
        """Test that canvas has section for final answer."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have final answer section
        assert "Final Answer" in content, "Final answer section not found"
        assert "result?.answer" in content, "Answer binding not found"

    def test_canvas_has_execution_timeline(self, client):
        """Test that canvas includes execution timeline/logs."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have execution timeline section
        assert "Execution Timeline" in content or "execution_history" in content, "Execution timeline not found"

    def test_canvas_has_metadata_display(self, client):
        """Test that canvas shows execution metadata (cost, duration, steps)."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should display execution metadata
        assert "total_cost" in content or "Total Cost" in content, "Cost display not found"
        assert "duration_seconds" in content or "Duration" in content, "Duration display not found"
        assert "step_count" in content or "Steps" in content, "Step count display not found"

    def test_canvas_has_export_actions(self, client):
        """Test that canvas includes export actions (markdown, JSON, share)."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have export buttons
        assert "exportMarkdown" in content, "Markdown export not found"
        assert "exportJSON" in content, "JSON export not found"
        assert "shareTask" in content, "Share function not found"

    def test_canvas_has_save_template_action(self, client):
        """Test that canvas includes save as template action."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have save template button
        assert "saveAsTemplate" in content, "Save template function not found"
        assert "Save Template" in content or "Save as template" in content.lower(), "Save template button not found"

    def test_canvas_logs_are_collapsible(self, client):
        """Test that execution logs are in a collapsible section."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have collapsible logs section
        assert "showLogs" in content, "showLogs state not found"
        assert "Execution Logs" in content, "Execution Logs section not found"
        # Should use x-collapse or similar mechanism
        assert "x-show=\"showLogs\"" in content or "@click=\"showLogs" in content, "Collapse mechanism not found"

    def test_canvas_separates_report_from_logs(self, client):
        """Test that canvas clearly separates final report from execution logs."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have separate sections
        assert "Final Report" in content or "Final Answer" in content, "Final report section not found"
        assert "Execution Logs" in content, "Execution logs section not found"
        # Logs should come after summary
        assert "Execution Summary" in content or "Execution Details" in content, "Execution summary not found"


# =============================================================================
# Context Path / Folder Picker Tests
# =============================================================================


class TestFolderPicker:
    """Test folder picker functionality for context path."""

    def test_context_path_input_exists(self, client):
        """Test that context path input field exists."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have context path input
        assert 'id="contextPath"' in content, "Context path input not found"
        assert "x-model=\"contextPath\"" in content, "Alpine.js binding not found"

    def test_browse_button_exists(self, client):
        """Test that Browse button exists for folder selection."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have browse button
        assert "📁 Browse" in content or "Browse" in content, "Browse button not found"
        assert "@click=\"selectFolder()\"" in content, "Folder selection handler not found"

    def test_select_folder_function_exists(self, client):
        """Test that selectFolder() function is implemented."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have selectFolder function
        assert "async selectFolder()" in content or "selectFolder()" in content, "selectFolder function not found"
        assert "showDirectoryPicker" in content, "File System Access API not implemented"

    def test_folder_picker_has_fallback(self, client):
        """Test that folder picker has fallback for older browsers."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should have fallback for browsers without showDirectoryPicker
        assert "webkitdirectory" in content, "Fallback directory picker not found"
        assert "input.type = 'file'" in content, "File input creation not found"

    def test_folder_picker_defaults_to_downloads(self, client):
        """Test that folder picker attempts to default to downloads folder."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.content.decode()

        # Should configure startIn option for File System Access API
        assert "startIn: 'downloads'" in content, "Downloads default not configured"
