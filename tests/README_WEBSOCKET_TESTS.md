# WebSocket Real-Time Update Tests

This document describes the comprehensive test suite for the WebSocket-based real-time UI update functionality added in Phase 17.

## Background

During Phase 17 development, a critical bug was discovered where execution steps weren't appearing in real-time in the web UI. The canvas showed "Waiting for execution to start..." throughout the entire execution, with steps only appearing after completion.

### Root Cause

The JavaScript `handleUpdate()` function in `index.html` required a `step` message before processing `code` or `output` messages. However, the backend's `task_runner.py` sends CODE actions as:
1. `UpdateType.CODE` message with the code
2. `UpdateType.OUTPUT` message with the execution result

There was no preceding `UpdateType.STEP` message for CODE actions, so the frontend ignored the updates.

### Fix

Modified `handleUpdate()` to **automatically create step objects** when `code` or `output` messages arrive without an existing step. This ensures steps appear immediately as the backend sends updates.

## Test Coverage

The test suite in `tests/test_websocket_updates.py` provides comprehensive coverage:

### 1. Backend Update Publishing (3 tests)

Tests the `task_runner.py` pub/sub system:

- **`test_publish_step_update`**: Verifies basic step update publishing and subscription
- **`test_publish_code_and_output_separately`**: Tests CODE followed by OUTPUT message flow
- **`test_multiple_subscribers`**: Ensures multiple clients receive the same updates

### 2. Step Creation Logic (9 tests)

Simulates the JavaScript `handleUpdate()` function to test step creation:

- **`test_step_message_creates_step`**: Standard `step` message creates new step
- **`test_code_without_step_creates_step`**: **KEY FIX** - `code` message creates step if none exists
- **`test_code_then_output_creates_complete_step`**: Code + output sequence creates complete step
- **`test_output_without_step_creates_step`**: **KEY FIX** - `output` message creates step if none exists
- **`test_multiple_code_outputs_create_multiple_steps`**: Multiple CODE actions create separate steps
- **`test_step_then_code_then_output`**: Standard flow with explicit step message
- **`test_mixed_step_types`**: Handles CODE, DELEGATE, ANSWER actions
- **`test_status_messages_dont_affect_steps`**: Status updates don't create steps
- **`test_complete_marks_last_step_complete`**: Complete message finalizes last step

### 3. Canvas Display Logic (4 tests)

Tests the canvas component's `displayHistory` computed property:

- **`test_uses_live_steps_during_execution`**: Shows live steps during execution
- **`test_uses_final_history_when_complete`**: Switches to final execution history when complete
- **`test_empty_steps_returns_empty_array`**: Handles empty state gracefully
- **`test_live_steps_format_conversion`**: Converts live step format to display format

### 4. Error Handling (2 tests)

Tests edge cases and error scenarios:

- **`test_error_message_stops_updates`**: Error messages stop the update stream
- **`test_step_creation_handles_missing_data`**: Handles missing data in messages gracefully

## Test Results

**Total**: 18 tests
**Status**: ✅ All passing
**Coverage**: Backend publishing, frontend step creation, canvas reactivity, error handling

## Integration with Full Test Suite

These tests complement the existing test suite:

- **`tests/test_web.py`**: 28 tests for API endpoints
- **`tests/test_web_ui.py`**: 52 tests for UI pages and templates
- **`tests/test_websocket_updates.py`**: 18 tests for real-time updates (NEW)

**Total Web Tests**: 98
**Overall Test Suite**: 197 passed, 4 skipped

## Test Execution

Run WebSocket tests only:
```bash
uv run pytest tests/test_websocket_updates.py -v
```

Run all web tests:
```bash
uv run pytest tests/test_web*.py -v
```

Run full test suite:
```bash
uv run pytest
```

## Why These Tests Matter

These tests prevent regression of critical user-facing functionality:

1. **Real-time feedback**: Users see execution progress as it happens
2. **Canvas updates**: Execution logs update live during task execution
3. **Proper state transitions**: Steps move from running → complete correctly
4. **Multiple step handling**: Complex tasks with multiple CODE actions work properly

Without these tests, the bugs could easily reappear during future refactoring of:
- WebSocket message handling
- Task execution flow
- Canvas component reactivity
- Frontend state management

## Future Enhancements

Potential additions to the test suite:

1. **Browser-based tests**: Use Playwright/Selenium to test actual JavaScript behavior in a browser
2. **WebSocket disconnection**: Test reconnection and state recovery
3. **Message ordering**: Test out-of-order message arrival
4. **Performance tests**: Validate update handling with hundreds of steps
5. **Concurrent tasks**: Test multiple tasks streaming updates simultaneously

## Related Files

- **`src/web/task_runner.py`**: Backend update publishing (lines 100-239)
- **`src/web/websocket/stream.py`**: WebSocket endpoint (lines 1-70)
- **`src/web/templates/index.html`**: Frontend `handleUpdate()` (lines 508-567)
- **`src/web/templates/components/canvas.html`**: Canvas `displayHistory` (lines 220-231)
- **`tests/test_web_ui.py`**: UI template and API tests (updated for canvas signature)

## Best Practices Applied

This test suite follows the project's testing guidelines:

1. **Test-Driven Bug Fixing**: Created failing test → Fixed bug → Verified fix
2. **Comprehensive Coverage**: Backend, frontend logic, integration, errors
3. **Simulation Approach**: Simulated JavaScript behavior in Python for fast unit tests
4. **Real Integration Tests**: Also tested actual pub/sub system with asyncio
5. **Pattern Reuse**: Extended existing test file patterns (fixtures, TestClient, mocks)

## Conclusion

These tests ensure the real-time UI update functionality remains working as development continues. They provide confidence that users will see immediate feedback during task execution, a critical aspect of the user experience.
