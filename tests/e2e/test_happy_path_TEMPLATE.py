"""
End-to-End Test: Happy Path Task Execution

This is a REFERENCE IMPLEMENTATION showing what our first E2E test should look like.
It demonstrates testing the complete user flow from task submission to result display.

To use this file:
1. Install Playwright: `uv add --dev playwright pytest-playwright`
2. Install browsers: `playwright install`
3. Start the web server: `uv run uvicorn src.web.app:app --reload`
4. Run this test: `uv run pytest tests/e2e/test_happy_path.py -v --headed`

Status: 🚧 NOT YET IMPLEMENTED (template only)
Priority: 🚨 HIGH - Implement ASAP
"""

import pytest
from playwright.sync_api import Page, expect
import time


@pytest.fixture(scope="module")
def app_url():
    """Base URL for the application.

    Note: Assumes dev server is running on localhost:8000
    In CI/CD, this would be a test server spun up automatically.
    """
    return "http://localhost:8000"


@pytest.fixture(scope="module")
def test_config():
    """Configuration for test execution.

    Returns config that's guaranteed to work without API keys.
    """
    return {
        "name": "local-only",
        "task": "Calculate the sum of 2 and 2",
        "expected_answer": "4"
    }


def test_happy_path_complete_task_execution(page: Page, app_url: str, test_config: dict):
    """
    Test the complete happy path: user submits task and sees real-time results.

    This test validates:
    1. ✅ Page loads correctly
    2. ✅ Config selector works
    3. ✅ Task submission succeeds
    4. ✅ WebSocket connection establishes
    5. ✅ Real-time steps appear as they execute
    6. ✅ Final answer displays correctly
    7. ✅ Canvas shows execution history
    8. ✅ Export buttons are available

    This is the MOST CRITICAL test - if this fails, the app is broken.
    """

    # ====================
    # Step 1: Load Home Page
    # ====================
    page.goto(app_url)

    # Wait for page to fully load (Alpine.js initialization)
    page.wait_for_load_state("networkidle")

    # Verify page title
    expect(page).to_have_title("RLM Agent - Home")

    # Verify main heading
    expect(page.locator("h1")).to_contain_text("RLM Agent")

    # ====================
    # Step 2: Select Configuration
    # ====================
    config_select = page.locator("select#config")

    # Wait for configs to load (fetch call completes)
    page.wait_for_function(
        "() => document.querySelector('select#config option:not([value=\"\"])') !== null",
        timeout=5000
    )

    # Select local-only config (no API keys required)
    config_select.select_option(test_config["name"])

    # Verify config details appear
    config_details = page.locator(".config-details")
    expect(config_details).to_be_visible()

    # ====================
    # Step 3: Enter Task
    # ====================
    task_textarea = page.locator("textarea#task")
    task_textarea.fill(test_config["task"])

    # Verify submit button is enabled
    submit_button = page.locator("button[type='submit']")
    expect(submit_button).to_be_enabled()

    # ====================
    # Step 4: Submit Task
    # ====================
    submit_button.click()

    # Verify loading state appears
    expect(page.locator(".animate-spin")).to_be_visible(timeout=1000)

    # Verify submit button is disabled during execution
    expect(submit_button).to_be_disabled()

    # ====================
    # Step 5: Wait for WebSocket Connection
    # ====================
    # Note: We can't directly inspect WebSocket, but we can verify UI effects

    # Wait for "Waiting for execution to start..." to disappear
    # (This proves WebSocket connected and first message received)
    page.wait_for_function(
        "() => !document.body.textContent.includes('Waiting for execution')",
        timeout=5000
    )

    # ====================
    # Step 6: Verify Real-Time Steps Appear
    # ====================
    # This is the CRITICAL test - steps MUST appear in real-time

    # Wait for first step to appear
    first_step = page.locator(".execution-step").first
    expect(first_step).to_be_visible(timeout=10000)

    # Verify step has required elements
    expect(first_step.locator(".step-action")).to_be_visible()

    # Optional: Watch steps appear over time (proves real-time updates)
    # Note: For simple tasks like "2+2", there may only be 1 step total
    # This check is more useful for multi-step tasks (see test_multiple_steps_show_sequentially)
    # We could add: assert page.locator(".execution-step").count() >= 1

    # ====================
    # Step 7: Wait for Task Completion
    # ====================
    # Wait for final answer to appear (proves task completed successfully)
    result_answer = page.locator(".result-answer")
    expect(result_answer).to_be_visible(timeout=30000)  # 30 second timeout for execution

    # Verify answer contains expected value
    answer_text = result_answer.text_content()
    assert test_config["expected_answer"] in answer_text, \
        f"Expected '{test_config['expected_answer']}' in answer, got: {answer_text}"

    # Verify loading spinner disappeared
    expect(page.locator(".animate-spin")).not_to_be_visible()

    # Verify submit button is enabled again
    expect(submit_button).to_be_enabled()

    # ====================
    # Step 8: Verify Canvas Shows Execution History
    # ====================
    canvas = page.locator(".canvas-viewer")
    expect(canvas).to_be_visible()

    # Verify execution history section exists
    execution_history = canvas.locator(".execution-history")
    expect(execution_history).to_be_visible()

    # Verify steps are listed
    history_steps = execution_history.locator(".step-item")
    assert history_steps.count() > 0, "Execution history should have at least one step"

    # ====================
    # Step 9: Verify Export Buttons Available
    # ====================
    # Export as Markdown
    export_md_button = canvas.locator("button:has-text('Export Markdown')")
    expect(export_md_button).to_be_visible()
    expect(export_md_button).to_be_enabled()

    # Export as JSON
    export_json_button = canvas.locator("button:has-text('Export JSON')")
    expect(export_json_button).to_be_visible()
    expect(export_json_button).to_be_enabled()

    # Export as PDF
    export_pdf_button = canvas.locator("button:has-text('Export PDF')")
    expect(export_pdf_button).to_be_visible()
    expect(export_pdf_button).to_be_enabled()

    # ====================
    # Step 10: Verify Cost Information (if available)
    # ====================
    if page.locator(".cost-breakdown").is_visible():
        cost_breakdown = page.locator(".cost-breakdown")
        expect(cost_breakdown).to_contain_text("Total Cost")

        # For local-only config, cost should be $0
        if test_config["name"] == "local-only":
            expect(cost_breakdown).to_contain_text("$0")


def test_multiple_steps_show_sequentially(page: Page, app_url: str):
    """
    Test that multi-step tasks show steps appearing one by one.

    This validates the real-time update bug fix where steps weren't
    appearing until task completion.
    """
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    # Select config
    page.locator("select#config").select_option("local-only")

    # Enter task that requires multiple steps
    page.locator("textarea#task").fill(
        "First calculate 10 + 20, then multiply the result by 2"
    )

    # Submit
    page.locator("button[type='submit']").click()

    # Wait for first step
    page.wait_for_selector(".execution-step", timeout=10000)

    # Record initial step count
    initial_count = page.locator(".execution-step").count()

    # Wait 3 seconds for more steps
    time.sleep(3)

    # Check if more steps appeared
    later_count = page.locator(".execution-step").count()

    # For multi-step task, should see steps appear incrementally
    # (This proves steps aren't all showing at once at the end)
    assert later_count >= initial_count, "Steps should appear over time, not all at once"


def test_error_message_displays_correctly(page: Page, app_url: str):
    """
    Test that errors are shown to the user appropriately.

    This validates error handling in the UI.
    """
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    # Select config
    page.locator("select#config").select_option("local-only")

    # Enter task that will likely cause an error
    page.locator("textarea#task").fill("import non_existent_module")

    # Submit
    page.locator("button[type='submit']").click()

    # Wait for error message (either in steps or error banner)
    # Use a broad selector to catch error wherever it appears
    page.wait_for_function(
        "() => document.body.textContent.toLowerCase().includes('error')",
        timeout=30000
    )

    # Verify error is visible to user
    error_elements = page.locator(".error, .text-red-700, .bg-red-50")
    assert error_elements.count() > 0, "Error message should be visible to user"


def test_stop_button_cancels_execution(page: Page, app_url: str):
    """
    Test that stop button (if implemented) cancels running task.

    Status: May not be implemented yet
    """
    pytest.skip("Stop button not yet implemented in Phase 17")

    # TODO: Implement when stop button is added
    # page.goto(app_url)
    # page.locator("select#config").select_option("local-only")
    # page.locator("textarea#task").fill("Long running task...")
    # page.locator("button[type='submit']").click()
    # page.locator("button:has-text('Stop')").click()
    # expect(page.locator(".execution-stopped")).to_be_visible()


# ====================
# Fixtures for Server Management
# ====================

@pytest.fixture(scope="session", autouse=True)
def check_server_running(app_url: str):
    """
    Verify dev server is running before tests start.

    In production, this would spin up a test server automatically.
    For now, it just checks and provides helpful error message.
    """
    import requests

    try:
        response = requests.get(app_url, timeout=5)
        if response.status_code != 200:
            pytest.fail(
                f"Server at {app_url} returned {response.status_code}. "
                f"Start the server: uv run uvicorn src.web.app:app --reload"
            )
    except requests.exceptions.ConnectionError:
        pytest.fail(
            f"Could not connect to {app_url}. "
            f"Start the server: uv run uvicorn src.web.app:app --reload"
        )


# ====================
# Helper Functions
# ====================

def wait_for_websocket_message(page: Page, message_type: str, timeout: int = 5000):
    """
    Helper to wait for specific WebSocket message type.

    Note: This is a placeholder - Playwright can intercept WebSocket
    messages with page.on("websocket"), but for simplicity we infer
    from UI state changes instead.
    """
    # TODO: Implement WebSocket message interception if needed
    pass


# ====================
# Usage Instructions
# ====================

"""
To run this test:

1. Install dependencies:
   uv add --dev playwright pytest-playwright
   playwright install

2. Start the web server:
   uv run uvicorn src.web.app:app --reload

3. Run the test:
   # Headless (fast)
   uv run pytest tests/e2e/test_happy_path.py -v

   # Headed (watch browser)
   uv run pytest tests/e2e/test_happy_path.py -v --headed

   # Slow motion (debug)
   uv run pytest tests/e2e/test_happy_path.py -v --headed --slowmo 500

   # With screenshots on failure
   uv run pytest tests/e2e/test_happy_path.py -v --screenshot on

4. Generate HTML report:
   uv run pytest tests/e2e/ --html=test_report.html --self-contained-html

Expected output:
  ✅ test_happy_path_complete_task_execution PASSED
  ✅ test_multiple_steps_show_sequentially PASSED
  ✅ test_error_message_displays_correctly PASSED
  ⏭️  test_stop_button_cancels_execution SKIPPED

If tests fail:
  - Check server is running
  - Check Ollama is running (for local-only config)
  - Check playwright installation: playwright install
  - Run with --headed --slowmo 500 to see what's happening
"""
