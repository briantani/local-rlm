# Quick Start: Running E2E Tests

## Prerequisites

1. **Install Playwright** (one-time setup)
   ```bash
   uv add --dev playwright pytest-playwright
   uv run playwright install chromium
   ```

2. **Start the dev server** (keep running in separate terminal)
   ```bash
   uv run uvicorn src.web.app:app --reload
   ```

3. **Start Ollama** (for local-only tests)
   ```bash
   ollama serve
   ```

## Running Tests

### Quick Start (Most Common)

```bash
# Run all E2E tests (headless, fast)
./tests/e2e/run_e2e_tests.sh
```

### Watch Mode (For Development)

```bash
# Run with browser visible - great for debugging!
./tests/e2e/run_e2e_tests.sh --headed
```

### Debugging Mode

```bash
# Slow motion - watch each step execute
./tests/e2e/run_e2e_tests.sh --debug
```

### Run Specific Tests

```bash
# Just happy path tests
./tests/e2e/run_e2e_tests.sh happy

# Just error handling tests
./tests/e2e/run_e2e_tests.sh errors

# Just API key tests
./tests/e2e/run_e2e_tests.sh keys
```

### Advanced Usage

```bash
# Run specific test function
uv run pytest tests/e2e/test_happy_path.py::test_complete_task_execution_happy_path -v --headed

# Run tests matching pattern
uv run pytest tests/e2e/ -k "real_time" -v --headed

# Generate HTML report
uv run pytest tests/e2e/ --html=test_report.html --self-contained-html
```

## Troubleshooting

### "Could not connect to http://localhost:8000"

**Problem:** Dev server not running

**Solution:**
```bash
# Start server in separate terminal
uv run uvicorn src.web.app:app --reload
```

### "Ollama not available" or tests timing out

**Problem:** Ollama not running

**Solution:**
```bash
# Start Ollama
ollama serve

# Verify it's working
ollama list
```

### Tests fail with "Cannot find element"

**Problem:** UI changed, selectors outdated

**Solution:**
```bash
# Run in headed mode to see what's happening
./tests/e2e/run_e2e_tests.sh --headed

# Run in debug mode for slow motion
./tests/e2e/run_e2e_tests.sh --debug
```

### Browser keeps crashing

**Problem:** Playwright browsers not installed

**Solution:**
```bash
# Reinstall browsers
uv run playwright install chromium
```

## Tips

### 1. Use Headed Mode for Development

When writing new tests, always use `--headed` so you can see what's happening:

```bash
uv run pytest tests/e2e/test_happy_path.py --headed --slowmo 500
```

### 2. Use Selectors Carefully

Prefer data attributes over CSS classes:

```python
# ❌ Fragile - class names change
page.locator(".btn-primary")

# ✅ Better - ID is stable
page.locator("button#submit")

# ✅ Best - semantic selector
page.locator("button[type='submit']")
```

### 3. Wait for State, Not Time

```python
# ❌ Bad - arbitrary timeout
time.sleep(5)

# ✅ Good - wait for specific condition
page.wait_for_selector(".result-answer", timeout=30000)

# ✅ Better - use expect with timeout
expect(page.locator(".result-answer")).to_be_visible(timeout=30000)
```

### 4. Test Helpers Save Time

Use the `submit_task` fixture instead of repeating code:

```python
def test_something(page, app_url, submit_task):
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    # ✅ Use helper
    submit_task(page, "local-only", "My task")

    # ❌ Don't repeat this every time
    # page.locator("select#config").select_option("local-only")
    # page.locator("textarea#task").fill("My task")
    # page.locator("button[type='submit']").click()
```

## Common Patterns

### Test Page Load

```python
def test_page_loads(page, app_url):
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    expect(page).to_have_title("RLM Agent - Home")
```

### Test Form Submission

```python
def test_form_submit(page, app_url, submit_task):
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    submit_task(page, "local-only", "Calculate 2+2")
    expect(page.locator(".result-answer")).to_be_visible(timeout=30000)
```

### Test Error Display

```python
def test_error_shown(page, app_url, submit_task):
    page.goto(app_url)
    page.wait_for_load_state("networkidle")
    submit_task(page, "local-only", "raise ValueError('test')")

    # Wait for error anywhere on page
    page.wait_for_function(
        "() => document.body.textContent.toLowerCase().includes('error')",
        timeout=30000
    )
```

### Test Button States

```python
def test_button_disabled(page, app_url):
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    button = page.locator("button[type='submit']")
    expect(button).to_be_disabled()

    # Enable it
    page.locator("textarea#task").fill("Test")
    page.locator("select#config").select_option("local-only")

    expect(button).to_be_enabled()
```

## Next Steps

1. **Read the tests** - Look at existing tests for patterns
2. **Run in headed mode** - See what the browser is doing
3. **Add your own tests** - Follow the patterns you see
4. **Use the helpers** - Fixtures in conftest.py save time

## Resources

- [Playwright Python Docs](https://playwright.dev/python/)
- [pytest-playwright Plugin](https://playwright.dev/python/docs/test-runners)
- [Our E2E Implementation Guide](E2E_IMPLEMENTATION.md)
- [Full Testing Strategy](../UI_TESTING_STRATEGY.md)
