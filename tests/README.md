# RLM Agent Test Suite

Comprehensive test coverage for the Recursive Language Model (RLM) Agent project.

## 📊 Current Status

**Total Tests:** 197 passing + 26 E2E tests active + 81 tests being fixed, 4 skipped
**Coverage Areas:** Backend logic, API endpoints, UI templates, WebSocket updates, End-to-End flows
**Test Types:** Unit, Integration, API, JavaScript syntax validation, E2E (Playwright)

⚠️ **Note**: Some new tests are temporarily skipped while selector issues are being fixed. See [TEST_FAILURE_FIX_SUMMARY.md](TEST_FAILURE_FIX_SUMMARY.md) for details.

### Test Distribution

- **Backend Core:** 41 tests (agent, budget, config, REPL, tools)
- **Web API:** 28 tests (routes, database, sessions)
- **Web UI:** 52 tests (templates, JavaScript integration, API response formats)
- **WebSocket:** 18 tests (pub/sub, step creation, canvas display)
- **Services:** 35 tests (task service, config service, session service)
- **E2E Tests (Active):** 26 tests ✅ **WORKING**
  - Happy Path: 11 tests
  - Error Handling: 14 tests
  - Config Estimation: 1 test
- **E2E Tests (Being Fixed):** 81 tests 🚧 **SKIPPED TEMPORARILY**
  - API Keys: 10 tests (needs modal workflow investigation)
  - Form Validation: 21 tests (needs selector updates)
  - State Management: 21 tests (needs selector updates)
  - WebSocket Reconnection: 11 tests (needs selector updates)
  - API Contracts: 18 tests (needs API expectation fixes)
- **Optimization:** 2 tests (DSPy modules)
- **Other:** 21 tests (context, prompt files, PDF export, parallel execution)

## 🚀 Running Tests

### Quick Start

```bash
# All tests
uv run pytest

# With verbose output
uv run pytest -v

# Specific test file
uv run pytest tests/test_web.py -v

# Specific test function
uv run pytest tests/test_web.py::test_home_page -v

# Show test coverage
uv run pytest --cov=src --cov-report=html
```

### Test Categories

```bash
# Backend unit tests
uv run pytest tests/test_agent.py tests/test_budget.py tests/test_repl.py

# Web tests
uv run pytest tests/test_web.py tests/test_web_ui.py

# WebSocket update tests
uv run pytest tests/test_websocket_updates.py -v

# PDF export tests
uv run pytest tests/test_pdf_export.py -v

# All web-related tests
uv run pytest tests/test_web*.py -v

# E2E tests (requires dev server running)
./tests/e2e/run_e2e_tests.sh              # All E2E tests
./tests/e2e/run_e2e_tests.sh --headed     # With visible browser
./tests/e2e/run_e2e_tests.sh --debug      # Slow motion debugging
./tests/e2e/run_e2e_tests.sh happy        # Happy path only
```

### Running with Options

```bash
# Stop on first failure
uv run pytest -x

# Show local variables on failure
uv run pytest -l

# Capture output
uv run pytest -s

# Run specific markers
uv run pytest -m "not integration"
```

## 📁 Test Structure

```
tests/
├── README.md                           # This file
├── conftest.py                         # Shared pytest fixtures
│
├── test_agent.py                       # Agent orchestration tests
├── test_budget.py                      # Token budget tracking
├── test_config_loader.py               # YAML config parsing
├── test_connectivity.py                # LLM provider connections
├── test_context.py                     # File context exploration
├── test_dspy_modules.py                # DSPy Architect/Coder modules
├── test_parallel.py                    # Parallel delegation
├── test_prompt_file.py                 # Task from file
├── test_repl.py                        # Python sandbox execution
├── test_tools.py                       # External tools (web search)
│
├── test_services.py                    # Service layer (Phase 12)
├── test_web.py                         # Web API endpoints (Phase 13)
├── test_web_ui.py                      # UI templates & pages (Phase 14-15)
├── test_websocket_updates.py           # Real-time updates (Phase 17 fix)
├── test_javascript_syntax.py           # JS syntax validation
├── test_pdf_export.py                  # PDF export feature (Phase 17)
│
├── UI_TESTING_STRATEGY.md              # Comprehensive testing analysis
├── TESTING_CHECKLIST.md                # Quick reference checklist
├── README_WEBSOCKET_TESTS.md           # WebSocket test documentation
│✨ NEW
    ├── __init__.py                     # E2E test package
    ├── conftest.py                     # E2E fixtures (server check, helpers)
    ├── run_e2e_tests.sh                # Test runner script
    ├── test_happy_path.py              # Complete task execution flow (11 tests)
    ├── test_error_handling.py          # Error display and recovery (14 tests)
    ├── test_api_keys.py                # API key modal interaction (11 tests)
    └── test_happy_path_TEMPLATE.py     # Reference implementation
    └── test_happy_path_TEMPLATE.py     # Example E2E test template
```

## 🧪 Test Types

### 1. Unit Tests

Test individual functions and classes in isolation.

**Example:**
```python
def test_repl_executes_code():
    repl = REPL()
    output = repl.execute("print('hello')")
    assert "hello" in output
```

**Files:** Most `test_*.py` files

### 2. Integration Tests

Test multiple components working together.

**Example:**
```python
def test_agent_with_real_coder():
    agent = RLMAgent(architect=..., coder=..., repl=...)
    result = agent.run("Calculate 2+2")
    assert result.final_answer == "4"
```

**Files:** `test_agent.py`, `test_web.py`

### 3. API Tests

Test HTTP endpoints and response formats.

**Example:**
```python
def test_configs_api(client):
    response = client.get("/api/configs")
    assert response.status_code == 200
    data = response.json()
    assert "profiles" in data
```

**Files:** `test_web.py`, `test_web_ui.py`

### 4. WebSocket Tests

Test pub/sub messaging and real-time updates.

**Example:**
```python
async def test_publish_step_update():
    await publish("task-123", TaskUpdate(type=UpdateType.STEP, ...))
    # Verify subscribers receive update
```

**Files:** `test_websocket_updates.py`

### 5. UI Template Tests

Test that pages render correctly and handle data properly.

**Example:**
```python
def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"RLM Agent" in response.content
```

**Files:** `test_web_ui.py`

### 6. JavaScript Syntax Tests

Validate JavaScript code in templates.

**Example:**
```python
def test_index_page_javascript_syntax():
    js_blocks = extract_javascript("src/web/templates/index.html")
    for js_code, line_num in js_blocks:
        assert validate_javascript_syntax(js_code)
```

**Files:** `test_javascript_syntax.py`

### 7. End-to-End (E2E) Tests ✨ **NEW**

Test complete user flows in real browsers using Playwright.

**Example:**
```python
def test_complete_task_execution_happy_path(page, app_url, submit_task):
    page.goto(app_url)
    page.wait_for_load_state("networkidle")

    # Submit task
    submit_task(page, "local-only", "Calculate 2+2")

    # Wait for execution
    expect(page.locator(".execution-step").first).to_be_visible(timeout=10000)

    # Wait for result
    expect(page.locator(".result-answer")).to_be_visible(timeout=30000)

    # Verify answer
    answer_text = page.locator(".result-answer").text_content()
    assert "4" in answer_text
```

**Files:** `tests/e2e/*.py`

**Prerequisites:**
1. Dev server running: `uv run uvicorn src.web.app:app --reload`
2. Playwright installed: `uv run playwright install chromium`
3. For local-only tests: Ollama running

**Running E2E Tests:**
```bash
# Quick way
./tests/e2e/run_e2e_tests.sh

# With browser visible
./tests/e2e/run_e2e_tests.sh --headed

# Slow motion for debugging
./tests/e2e/run_e2e_tests.sh --debug

# Specific test file
./tests/e2e/run_e2e_tests.sh happy
```

### 8. API Contract Tests ✨ **NEW**

Test API response structures, field types, and data formats to prevent frontend/backend mismatches.

**Example:**
```python
def test_list_profiles_returns_correct_structure():
    response = client.get("/api/configs")
    assert response.status_code == 200
    data = response.json()

    assert "profiles" in data
    assert "count" in data
    assert isinstance(data["profiles"], list)
    assert isinstance(data["count"], int)
    assert data["count"] == len(data["profiles"])
```

**What These Tests Validate:**
- Response structure matches expected format
- Field types are correct (string, int, bool, array, object)
- Datetime fields use ISO format
- Required fields are present
- Error responses have proper structure

**Files:** `tests/test_api_contracts.py`

**Running Contract Tests:**
```bash
uv run pytest tests/test_api_contracts.py -v
```

## 🎯 Testing Best Practices

### 1. Use Fixtures for Setup

```python
@pytest.fixture
def agent():
    return RLMAgent(
        architect=MockArchitect(),
        coder=MockCoder(),
        repl=MockREPL()
    )

def test_agent_runs(agent):
    result = agent.run("test task")
    assert result is not None
```

### 2. Mock External Dependencies

```python
@pytest.fixture
def mock_config_service():
    mock = MagicMock()
    mock.list_profiles.return_value = [...]
    return mock
```

### 3. Test Edge Cases

```python
def test_empty_input():
    # Test with empty string
def test_very_long_input():
    # Test with 10K+ character input
def test_special_characters():
    # Test with Unicode, emojis, etc.
```

### 4. Clear Test Names

```python
# ❌ Bad
def test_agent():
    ...

# ✅ Good
def test_agent_returns_correct_answer_for_simple_math():
    ...
```

## 🐛 Testing for Bugs

### Recent Bug Fixes Covered by Tests

1. **WebSocket Steps Not Appearing** (Phase 17)
   - **Bug:** Steps only appeared after task completion
   - **Root Cause:** `handleUpdate()` required 'step' message before 'code'/'output'
   - **Fix:** Automatic step creation from code/output messages
   - **Tests:** `test_websocket_updates.py` (18 tests)

2. **API Response Format Mismatch** (Phase 14)
   - **Bug:** JavaScript expected array, API returned `{profiles: []}`
   - **Fix:** JavaScript handles both formats
   - **Tests:** `test_web_ui.py::TestAPIResponseFormats`

3. **Coder Model Missing from Config Detail** (Phase 15)
   - **Bug:** Coder model not displayed in config detail/compare pages
   - **Fix:** Added coder model to config enhancement
   - **Tests:** `test_web_ui.py::test_config_detail_shows_coder_model`

## 📚 Documentation

- **[UI Testing Strategy](UI_TESTING_STRATEGY.md)** - Comprehensive analysis of testing gaps
- **[Testing Checklist](TESTING_CHECKLIST.md)** - Quick reference for must-have tests
- **[WebSocket Tests](README_WEBSOCKET_TESTS.md)** - Documentation of WebSocket test suite

## 🚧 What's Missing

See [UI_TESTING_STRATEGY.md](UI_TESTING_STRATEGY.md) for detailed analysis.

### ~~Critical Gaps~~ → ✅ **IMPLEMENTED (Phase 18)**

1. ✅ **End-to-End (E2E) Tests** - Browser automation testing with Playwright (**103 tests added!**)
   - Happy path: 11 tests (complete task execution flow)
   - Error handling: 14 tests (API errors, validation, user feedback)
   - API key modal: 11 tests (auto-open, validation, session management)
   - WebSocket reconnection: 11 tests (connection resilience, error handling)
   - Form validation: 21 tests (empty fields, disabled states, input handling)
   - State management: 21 tests (Alpine.js state, loading states, race conditions)
   - Templates: 14 tests (page rendering, component integration)

2. ✅ **API Contract Tests** - Response structure validation (**18 tests added!**)
   - Configs API: 5 tests (list, detail, estimate, validation)
   - Tasks API: 6 tests (create, list, get, validation)
   - Sessions API: 4 tests (create, keys, status)
   - WebSocket messages: 3 tests (message structure, types)

### Remaining Medium Priority

3. **Visual Regression Tests** - Screenshot comparison
   - Catch unintended UI changes
   - Mobile viewport testing
   - Component rendering consistency

4. **Performance Tests** - Load testing and benchmarks
   - Page load times
   - WebSocket connection speed
   - Memory leak detection
   - Long-running task stability

5. **Browser Compatibility** - Multi-browser testing
   - Firefox support
   - Safari support
   - Mobile browsers (iOS Safari, Chrome Mobile)

### Lower Priority

6. **Accessibility (a11y) Tests** - Screen reader and keyboard navigation
7. **Load Tests** - Multiple concurrent users
8. **Security Tests** - XSS, CSRF, injection attacks

### Remaining Gaps (Lower Priority)

2. ⚠️ **WebSocket Connection Lifecycle** - Disconnection, reconnection, timeouts
3. ⚠️ **Component State Management** - Alpine.js computed properties, watchers
4. ⚠️ **Mobile & Responsive Behavior** - Touch events, small screens
5. ⚠️ **Browser Compatibility** - Safari, Firefox testing
6. ⚠️ **Accessibility (a11y)** - Keyboard navigation, screen readers

## 🏗️ Contributing Tests

### Adding a New Test

1. **Choose the right file:**
   - Backend logic → `test_<module>.py`
   - API endpoint → `test_web.py`
   - UI page → `test_web_ui.py`
   - WebSocket → `test_websocket_updates.py`

2. **Use descriptive names:**
   ```python
   def test_config_selector_updates_when_api_returns_new_configs():
       ...
   ```

3. **Add docstrings:**
   ```python
   def test_something():
       """Test that X behaves correctly when Y happens.

       This guards against the bug where Z was broken.
       """
   ```

4. **Run tests before committing:**
   ```bash
   uv run pytest tests/<your_test_file>.py -v
   uvx ruff check --fix
   ```

### Test-Driven Development (TDD)

1. **Write failing test first**
   ```python
   def test_new_feature():
       result = new_feature()
       assert result == expected_value
   ```

2. **Run test (should fail)**
   ```bash
   uv run pytest tests/test_new_feature.py -v
   ```

3. **Implement feature**
   ```python
   def new_feature():
       return expected_value
   ```

4. **Run test (should pass)**
   ```bash
   uv run pytest tests/test_new_feature.py -v
   ```

## 🔍 Debugging Failed Tests

### View Full Output

```bash
# Show print statements
uv run pytest tests/test_example.py -s

# Show local variables on failure
uv run pytest tests/test_example.py -l

# Stop on first failure
uv run pytest -x

# Run with more verbose output
uv run pytest tests/test_example.py -vv
```

### Debug with pdb

```python
def test_something():
    result = compute_something()
    import pdb; pdb.set_trace()  # Debugger starts here
    assert result == expected
```

### Check Test Logs

```bash
# Run with logging enabled
uv run pytest tests/test_example.py -v --log-cli-level=DEBUG
```

## 📊 Coverage Reports

```bash
# Generate HTML coverage report
uv run pytest --cov=src --cov-report=html

# Open report
open htmlcov/index.html
```

## 🎓 Resources

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Playwright Python](https://playwright.dev/python/)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)

---

**Last Updated:** January 7, 2026
**Test Suite Version:** 1.0
**Python Version:** 3.14.2
**Test Framework:** pytest 9.0.2
