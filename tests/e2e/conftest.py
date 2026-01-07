"""
Shared fixtures for E2E tests.

Provides fixtures for:
- Server management (starting/stopping test server)
- Database setup/teardown
- Common page elements and helpers
"""

import pytest
import time
import requests


@pytest.fixture(scope="session")
def app_url():
    """Base URL for the application.
    
    For now, assumes dev server is running on localhost:8000.
    Future: Could spin up test server automatically.
    """
    return "http://localhost:8000"


@pytest.fixture(scope="session", autouse=True)
def verify_server_running(app_url: str):
    """
    Verify dev server is running before tests start.
    
    Provides helpful error message if server isn't available.
    In production, this could spin up a test server automatically.
    """
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.get(app_url, timeout=5)
            if response.status_code == 200:
                print(f"\n✅ Server available at {app_url}")
                return
            print(f"⚠️  Server returned {response.status_code}, retrying...")
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                print(f"⚠️  Server not available, waiting {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                pytest.exit(
                    f"\n❌ Could not connect to {app_url}\n"
                    f"   Start the server first:\n"
                    f"   uv run uvicorn src.web.app:app --reload\n",
                    returncode=1
                )


@pytest.fixture
def test_config():
    """Default test configuration that works without API keys."""
    return {
        "name": "local-only",
        "task": "Calculate the sum of 2 and 2",
        "expected_answer": "4"
    }


@pytest.fixture
def wait_for_element():
    """Helper function to wait for elements with custom timeout."""
    def _wait(page, selector: str, timeout: int = 5000, state: str = "visible"):
        """Wait for element to be in specified state.
        
        Args:
            page: Playwright page object
            selector: CSS selector
            timeout: Timeout in milliseconds
            state: Element state ('visible', 'attached', 'detached', 'hidden')
        """
        page.wait_for_selector(selector, timeout=timeout, state=state)
        return page.locator(selector)
    
    return _wait


@pytest.fixture
def wait_for_text():
    """Helper to wait for specific text to appear on page."""
    def _wait(page, text: str, timeout: int = 5000):
        """Wait for text to appear anywhere on page.
        
        Args:
            page: Playwright page object
            text: Text to wait for
            timeout: Timeout in milliseconds
        """
        page.wait_for_function(
            f"() => document.body.textContent.includes('{text}')",
            timeout=timeout
        )
    
    return _wait


@pytest.fixture
def submit_task():
    """Helper to submit a task through the UI."""
    def _submit(page, config_name: str, task_text: str):
        """Submit task via the UI form.
        
        Args:
            page: Playwright page object
            config_name: Configuration to select
            task_text: Task description
        
        Returns:
            None (task submitted, WebSocket should connect)
        """
        # Wait for configs to load
        page.wait_for_function(
            "() => document.querySelector('select#config option:not([value=\"\"])') !== null",
            timeout=5000
        )
        
        # Select config
        page.locator("select#config").select_option(config_name)
        
        # Enter task
        page.locator("textarea#task").fill(task_text)
        
        # Submit
        page.locator("button[type='submit']").click()
    
    return _submit
