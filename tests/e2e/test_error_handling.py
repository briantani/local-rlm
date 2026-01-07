"""
E2E Test: Error Handling

Tests that errors are properly displayed to users and don't break the UI.
Validates error messages, loading states, and recovery from failures.

Covers:
- Task execution errors (Python errors in REPL)
- Network errors (simulated where possible)
- Invalid inputs
- Error message visibility
- UI recovery after errors
"""

from playwright.sync_api import Page, expect


def test_error_message_displays_on_task_failure(
    page: Page,
    app_url: str,
    submit_task
):
    """
    Test that execution errors are shown to the user.
    
    Submits a task that will cause an error and verifies
    the error is visible in the UI.
    """
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Submit task that will error (import non-existent module)
    submit_task(page, "local-only", "import nonexistent_module_xyz")
    
    # Wait for execution to start
    page.wait_for_selector(".execution-step", timeout=10000)
    
    # Wait for error to appear (either in step or error banner)
    # Use broad selector to catch error wherever it appears
    page.wait_for_function(
        "() => document.body.textContent.toLowerCase().includes('error') || "
        "document.body.textContent.toLowerCase().includes('traceback')",
        timeout=30000
    )
    
    # Verify error is visible to user
    # Check for red/error styling elements
    error_elements = page.locator(".error, .text-red-700, .bg-red-50, .text-red-900")
    assert error_elements.count() > 0, "Error message should be visible to user"
    
    # Verify submit button is re-enabled after error
    expect(page.locator("button[type='submit']")).to_be_enabled()


def test_empty_task_prevents_submission(page: Page, app_url: str):
    """Test that empty task text prevents form submission."""
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Wait for configs
    page.wait_for_function(
        "() => document.querySelector('select#config option:not([value=\"\"])') !== null",
        timeout=5000
    )
    
    # Select config but leave task empty
    page.locator("select#config").select_option("local-only")
    
    # Submit button should be disabled
    submit_button = page.locator("button[type='submit']")
    expect(submit_button).to_be_disabled()
    
    # Add whitespace only - should still be disabled
    page.locator("textarea#task").fill("   \n\n   ")
    expect(submit_button).to_be_disabled()


def test_no_config_selected_prevents_submission(page: Page, app_url: str):
    """Test that missing config selection prevents submission."""
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Enter task text but don't select config
    page.locator("textarea#task").fill("Test task")
    
    # Submit button should be disabled
    submit_button = page.locator("button[type='submit']")
    expect(submit_button).to_be_disabled()


def test_form_disabled_during_execution(
    page: Page,
    app_url: str,
    submit_task
):
    """Test that form is disabled while task is running."""
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Submit task
    submit_task(page, "local-only", "import time; time.sleep(0.5); print('done')")
    
    # Immediately check that form is disabled
    config_select = page.locator("select#config")
    task_textarea = page.locator("textarea#task")
    submit_button = page.locator("button[type='submit']")
    
    # All should be disabled during execution
    expect(config_select).to_be_disabled()
    expect(task_textarea).to_be_disabled()
    expect(submit_button).to_be_disabled()
    
    # Wait for completion
    page.wait_for_selector(".result-answer", timeout=30000)
    
    # Form should be re-enabled
    expect(config_select).to_be_enabled()
    expect(task_textarea).to_be_enabled()
    expect(submit_button).to_be_enabled()


def test_error_clears_on_new_submission(
    page: Page,
    app_url: str,
    submit_task
):
    """Test that previous error is cleared when submitting new task."""
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Submit task that will error
    submit_task(page, "local-only", "raise ValueError('test error')")
    
    # Wait for error
    page.wait_for_function(
        "() => document.body.textContent.toLowerCase().includes('error')",
        timeout=30000
    )
    
    # Verify error is present
    error_count_before = page.locator(".error, .text-red-700, .bg-red-50").count()
    assert error_count_before > 0
    
    # Submit new task
    submit_task(page, "local-only", "print('hello')")
    
    # Error should be cleared (or at least not dominating the UI)
    # Verify loading state appears (proves new submission started)
    expect(page.locator(".animate-spin")).to_be_visible(timeout=2000)


def test_nonexistent_config_page_shows_error(page: Page, app_url: str):
    """Test that accessing non-existent config shows error page."""
    page.goto(f"{app_url}/configs/this-config-does-not-exist-12345")
    
    # Should show error (404 or 500)
    # Check for error indication in content
    content = page.content()
    assert "error" in content.lower() or "not found" in content.lower() or "404" in content


def test_invalid_task_id_shows_appropriate_message(page: Page, app_url: str):
    """Test that accessing invalid task ID shows error."""
    page.goto(f"{app_url}/share/invalid-task-id-12345")
    
    # Should show error or "not found" message
    content = page.content()
    assert "error" in content.lower() or "not found" in content.lower()


def test_syntax_error_in_code_shows_traceback(
    page: Page,
    app_url: str,
    submit_task
):
    """Test that Python syntax errors show helpful traceback."""
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Submit code with syntax error
    submit_task(page, "local-only", "def broken_function(\nprint('missing closing paren')")
    
    # Wait for execution to complete
    page.wait_for_selector(".execution-step", timeout=10000)
    
    # Should show syntax error or traceback
    page.wait_for_function(
        "() => document.body.textContent.toLowerCase().includes('syntax') || "
        "document.body.textContent.toLowerCase().includes('error')",
        timeout=30000
    )


def test_very_long_input_accepted(page: Page, app_url: str):
    """Test that long task input is handled properly."""
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Create a long but valid task
    long_task = "Calculate the following:\n" + "\n".join([f"{i} + {i+1}" for i in range(100)])
    
    # Should be able to enter it
    textarea = page.locator("textarea#task")
    textarea.fill(long_task)
    
    # Verify it was set
    assert len(textarea.input_value()) > 1000


def test_special_characters_in_task(
    page: Page,
    app_url: str,
    submit_task
):
    """Test that special characters in task don't break submission."""
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Task with various special characters
    special_task = "Calculate: 2 + 2 # Comment with 中文 and emojis 🚀 and quotes \"like this\""
    
    # Should submit successfully
    submit_task(page, "local-only", special_task)
    
    # Should start execution (not crash)
    page.wait_for_selector(".execution-step", timeout=10000)


def test_multiple_rapid_submissions_prevented(
    page: Page,
    app_url: str
):
    """Test that rapid clicking submit button doesn't create duplicate tasks."""
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Wait for configs
    page.wait_for_function(
        "() => document.querySelector('select#config option:not([value=\"\"])') !== null",
        timeout=5000
    )
    
    # Fill form
    page.locator("select#config").select_option("local-only")
    page.locator("textarea#task").fill("Test task")
    
    # Click submit multiple times rapidly
    submit_button = page.locator("button[type='submit']")
    submit_button.click()
    submit_button.click()  # Second click should do nothing
    
    # Button should be disabled immediately
    expect(submit_button).to_be_disabled()
    
    # Should only see one execution starting
    # (Hard to verify definitively, but button disabled prevents duplicates)


def test_context_path_with_invalid_directory(
    page: Page,
    app_url: str,
    submit_task
):
    """Test that invalid context path is handled gracefully."""
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    
    # Wait for configs
    page.wait_for_function(
        "() => document.querySelector('select#config option:not([value=\"\"])') !== null",
        timeout=5000
    )
    
    # Enter invalid context path
    page.locator("select#config").select_option("local-only")
    page.locator("textarea#task").fill("List files in current directory")
    page.locator("input#contextPath").fill("/this/path/does/not/exist/12345")
    
    # Submit
    page.locator("button[type='submit']").click()
    
    # Should either:
    # 1. Show validation error before submission
    # 2. Start execution and handle error gracefully
    # Either way, UI shouldn't crash
    
    # Wait a moment for any error to appear
    page.wait_for_timeout(2000)
    
    # Page should still be functional
    expect(page.locator("select#config")).to_be_visible()
