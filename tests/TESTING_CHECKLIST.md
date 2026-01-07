# Critical UI Testing Checklist

Quick reference for must-have tests based on [UI_TESTING_STRATEGY.md](UI_TESTING_STRATEGY.md).

## 🚨 Immediate Priority (Week 1)

### E2E Tests with Playwright

- [ ] **test_e2e_happy_path.py**
  - User loads home page
  - Selects config
  - Enters task text
  - Clicks submit
  - WebSocket connects
  - Steps appear in real-time
  - Final answer displays
  - Canvas shows execution history

- [ ] **test_e2e_error_handling.py**
  - API returns 500 error → User sees error message
  - WebSocket connection fails → User sees connection error
  - Invalid config selected → User prevented from submitting

- [ ] **test_e2e_api_key_modal.py**
  - User selects config requiring API keys
  - Modal opens automatically
  - User enters keys
  - Keys validated
  - Modal closes
  - Task proceeds

## ⚠️ High Priority (Week 2)

### WebSocket Behavior Tests

- [ ] **test_websocket_reconnection.py**
  - Connection established successfully
  - Connection drops mid-task → Error displayed
  - Reconnect button works
  - State preserved after reconnect

- [ ] **test_websocket_multiple_messages.py**
  - Rapid message arrival handled correctly
  - Out-of-order messages handled gracefully
  - Large messages (>10KB) don't break parsing

### API Contract Tests

- [ ] **test_api_contracts.py**
  - `/api/configs` returns `{profiles: [], count: N}`
  - `/api/tasks` POST accepts `{task, config_name, context_path?}`
  - WebSocket messages have valid `type` and `data` fields
  - All datetime fields are ISO format

## 📋 Medium Priority (Week 3-4)

### Component Integration Tests

- [ ] **test_form_validation.py**
  - Empty task text → Submit disabled
  - No config selected → Submit disabled
  - Task running → Form disabled
  - Invalid characters in context path → Validation error

- [ ] **test_state_management.py**
  - Config selection updates configDetails
  - Task completion sets result
  - Error state clears on new submission
  - Loading state prevents double-submit

- [ ] **test_canvas_component.py**
  - displayHistory shows live steps during execution
  - displayHistory switches to final history after completion
  - Export buttons work correctly
  - Step rendering handles all action types (CODE, DELEGATE, ANSWER)

### Error Handling Tests

- [ ] **test_network_errors.py**
  - Offline → Fetch fails → User sees "Network error"
  - Timeout → Request aborted → User sees "Request timed out"
  - 401 Unauthorized → User redirected to login (future)
  - 429 Rate limit → User sees "Too many requests"

## 📊 Lower Priority (Future)

### Visual Regression Tests

- [ ] Screenshot test for home page
- [ ] Screenshot test for configs page
- [ ] Screenshot test for modal open/close
- [ ] Screenshot test for mobile viewport

### Accessibility Tests

- [ ] Keyboard navigation works (Tab, Enter, Esc)
- [ ] Screen reader announces errors
- [ ] ARIA labels present on interactive elements
- [ ] Focus management after modal close

### Performance Tests

- [ ] Page load < 2 seconds
- [ ] WebSocket connects < 500ms
- [ ] Config list renders < 1 second
- [ ] No memory leaks during long tasks

## 🔧 Setup Commands

### Install Playwright

```bash
# Add to project
uv add --dev playwright pytest-playwright

# Install browsers
playwright install
```

### Run E2E Tests

```bash
# All E2E tests
uv run pytest tests/e2e/ -v

# Specific test
uv run pytest tests/e2e/test_happy_path.py -v

# With browser UI visible (headed mode)
uv run pytest tests/e2e/ --headed

# Generate HTML report
uv run pytest tests/e2e/ --html=test_report.html
```

### Create E2E Test Structure

```bash
mkdir -p tests/e2e
touch tests/e2e/__init__.py
touch tests/e2e/conftest.py
touch tests/e2e/test_happy_path.py
touch tests/e2e/test_error_handling.py
touch tests/e2e/test_api_key_modal.py
```

## 📝 Example E2E Test Template

```python
"""
E2E Test Template
tests/e2e/test_template.py
"""
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture
def app_url():
    """Base URL for the application."""
    return "http://localhost:8000"

def test_example_flow(page: Page, app_url: str):
    """Test a complete user flow."""
    # Navigate to home page
    page.goto(app_url)

    # Wait for page to load
    expect(page.locator("h1")).to_contain_text("RLM Agent")

    # Interact with form
    page.select_option("select#config", "local-only")
    page.fill("textarea#task", "Test task")

    # Submit form
    page.click("button[type='submit']")

    # Wait for WebSocket response
    page.wait_for_selector(".execution-step", timeout=5000)

    # Verify steps appear
    steps = page.locator(".execution-step").all()
    assert len(steps) > 0

    # Wait for completion
    page.wait_for_selector(".result-answer", timeout=30000)

    # Verify result
    answer = page.locator(".result-answer").text_content()
    assert answer is not None
```

## 🎯 Testing Goals

| Metric | Target | Current | Gap |
|--------|--------|---------|-----|
| E2E Coverage | 70% of critical paths | 0% | ❌ **High Risk** |
| Component Tests | 50% of components | 0% | ⚠️ **Medium Risk** |
| API Contract Tests | 100% of endpoints | 0% | ⚠️ **Medium Risk** |
| Bug Detection | 80% caught in testing | ~30% | ❌ **High Risk** |

## 📚 Resources

- [Full Testing Strategy](UI_TESTING_STRATEGY.md)
- [Playwright Documentation](https://playwright.dev/python/)
- [pytest-playwright Plugin](https://playwright.dev/python/docs/test-runners)
- [Alpine.js Testing Guide](https://alpinejs.dev/advanced/testing)

## ✅ Completion Tracking

**Week 1:** [ ] 3 E2E tests (happy path, errors, API keys)
**Week 2:** [ ] WebSocket + API contract tests
**Week 3-4:** [ ] Component integration + error handling
**Future:** [ ] Visual regression + accessibility + performance

---

**Last Updated:** January 7, 2026
**Status:** 🚧 In Progress (0/3 critical tests complete)
