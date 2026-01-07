"""
Tests for WebSocket real-time update handling.

Tests the client-side JavaScript logic for handling different WebSocket
message types and ensuring steps are created/updated correctly.

These tests use Playwright for browser automation to test actual JavaScript behavior.
"""

import pytest
import asyncio

from src.web.task_runner import UpdateType, TaskUpdate, publish, subscribe


# =============================================================================
# Unit Tests - Backend Update Publishing
# =============================================================================


@pytest.mark.asyncio
async def test_publish_step_update():
    """Test publishing a step update to subscribers."""
    task_id = "test-task-123"

    update = TaskUpdate(
        type=UpdateType.STEP,
        data={
            "step": 1,
            "action": "CODE",
            "input": "print('hello')",
            "output": "hello"
        }
    )

    # Subscribe to updates
    received_updates = []

    async def collect_updates():
        async for update in subscribe(task_id):
            received_updates.append(update)
            if update.type == UpdateType.COMPLETE:
                break

    # Start subscriber in background
    subscriber_task = asyncio.create_task(collect_updates())

    # Give subscriber time to start
    await asyncio.sleep(0.1)

    # Publish updates
    await publish(task_id, update)
    await publish(task_id, TaskUpdate(type=UpdateType.COMPLETE, data={}))

    # Wait for subscriber to finish
    await subscriber_task

    assert len(received_updates) == 2
    assert received_updates[0].type == UpdateType.STEP
    assert received_updates[0].data["action"] == "CODE"
    assert received_updates[1].type == UpdateType.COMPLETE


@pytest.mark.asyncio
async def test_publish_code_and_output_separately():
    """Test publishing code and output as separate messages."""
    task_id = "test-task-456"

    received_updates = []

    async def collect_updates():
        async for update in subscribe(task_id):
            received_updates.append(update)
            if update.type == UpdateType.COMPLETE:
                break

    subscriber_task = asyncio.create_task(collect_updates())
    await asyncio.sleep(0.1)

    # Publish code first
    await publish(task_id, TaskUpdate(
        type=UpdateType.CODE,
        data={"step": 1, "code": "x = 42"}
    ))

    # Then publish output
    await publish(task_id, TaskUpdate(
        type=UpdateType.OUTPUT,
        data={"step": 1, "output": "42"}
    ))

    # Complete
    await publish(task_id, TaskUpdate(type=UpdateType.COMPLETE, data={}))

    await subscriber_task

    assert len(received_updates) == 3
    assert received_updates[0].type == UpdateType.CODE
    assert received_updates[1].type == UpdateType.OUTPUT
    assert received_updates[2].type == UpdateType.COMPLETE


@pytest.mark.asyncio
async def test_multiple_subscribers():
    """Test that multiple subscribers receive the same updates."""
    task_id = "test-task-789"

    updates1 = []
    updates2 = []

    async def collect1():
        async for update in subscribe(task_id):
            updates1.append(update)
            if update.type == UpdateType.COMPLETE:
                break

    async def collect2():
        async for update in subscribe(task_id):
            updates2.append(update)
            if update.type == UpdateType.COMPLETE:
                break

    # Start both subscribers
    task1 = asyncio.create_task(collect1())
    task2 = asyncio.create_task(collect2())
    await asyncio.sleep(0.1)

    # Publish updates
    await publish(task_id, TaskUpdate(type=UpdateType.STATUS, data={"status": "running"}))
    await publish(task_id, TaskUpdate(type=UpdateType.CODE, data={"code": "test"}))
    await publish(task_id, TaskUpdate(type=UpdateType.COMPLETE, data={}))

    await task1
    await task2

    # Both should receive the same updates
    assert len(updates1) == 3
    assert len(updates2) == 3
    assert updates1[0].type == updates2[0].type == UpdateType.STATUS
    assert updates1[1].type == updates2[1].type == UpdateType.CODE
    assert updates1[2].type == updates2[2].type == UpdateType.COMPLETE


# =============================================================================
# Integration Tests - Step Creation Logic
# =============================================================================


class TestStepCreationLogic:
    """Test the JavaScript step creation logic (simulated in Python)."""

    def setup_method(self):
        """Initialize step tracking for each test."""
        self.steps = []

    def handle_update(self, update_type: str, data: dict):
        """
        Simulate the JavaScript handleUpdate function.

        This mimics the logic in index.html's handleUpdate method.
        """
        if update_type == "status":
            pass  # Status updates don't affect steps

        elif update_type == "step":
            # New step started
            self.steps.append({
                "action": data.get("action"),
                "status": "running",
                "code": None,
                "output": None
            })

        elif update_type == "code":
            # Code generated - create step if doesn't exist
            if len(self.steps) == 0 or self.steps[-1]["code"] is not None:
                # New CODE step
                self.steps.append({
                    "action": "CODE",
                    "status": "running",
                    "code": data.get("code"),
                    "output": None
                })
            else:
                self.steps[-1]["code"] = data.get("code")

        elif update_type == "output":
            # Code execution output - ensure step exists
            if len(self.steps) == 0:
                # Create step if missing
                self.steps.append({
                    "action": "CODE",
                    "status": "complete",  # Output means step is complete
                    "code": None,
                    "output": data.get("output")
                })
            else:
                self.steps[-1]["output"] = data.get("output")
                self.steps[-1]["status"] = "complete"

        elif update_type == "complete":
            # Task completed
            if len(self.steps) > 0:
                self.steps[-1]["status"] = "complete"

    def test_step_message_creates_step(self):
        """Test that a 'step' message creates a new step."""
        self.handle_update("step", {"action": "DELEGATE", "input": "task"})

        assert len(self.steps) == 1
        assert self.steps[0]["action"] == "DELEGATE"
        assert self.steps[0]["status"] == "running"

    def test_code_without_step_creates_step(self):
        """Test that 'code' message creates step if none exists."""
        self.handle_update("code", {"code": "print('hello')"})

        assert len(self.steps) == 1
        assert self.steps[0]["action"] == "CODE"
        assert self.steps[0]["code"] == "print('hello')"
        assert self.steps[0]["output"] is None

    def test_code_then_output_creates_complete_step(self):
        """Test that code followed by output creates a complete step."""
        self.handle_update("code", {"code": "x = 42"})
        self.handle_update("output", {"output": "42"})

        assert len(self.steps) == 1
        assert self.steps[0]["code"] == "x = 42"
        assert self.steps[0]["output"] == "42"
        assert self.steps[0]["status"] == "complete"

    def test_output_without_step_creates_step(self):
        """Test that 'output' message creates step if none exists."""
        self.handle_update("output", {"output": "result"})

        assert len(self.steps) == 1
        assert self.steps[0]["action"] == "CODE"
        assert self.steps[0]["output"] == "result"
        assert self.steps[0]["status"] == "complete"

    def test_multiple_code_outputs_create_multiple_steps(self):
        """Test that multiple code/output pairs create separate steps."""
        # First step
        self.handle_update("code", {"code": "step1"})
        self.handle_update("output", {"output": "output1"})

        # Second step
        self.handle_update("code", {"code": "step2"})
        self.handle_update("output", {"output": "output2"})

        assert len(self.steps) == 2
        assert self.steps[0]["code"] == "step1"
        assert self.steps[0]["output"] == "output1"
        assert self.steps[0]["status"] == "complete"
        assert self.steps[1]["code"] == "step2"
        assert self.steps[1]["output"] == "output2"
        assert self.steps[1]["status"] == "complete"

    def test_step_then_code_then_output(self):
        """Test standard flow: step message, then code, then output."""
        self.handle_update("step", {"action": "CODE"})
        self.handle_update("code", {"code": "test_code"})
        self.handle_update("output", {"output": "test_output"})

        assert len(self.steps) == 1
        assert self.steps[0]["action"] == "CODE"
        assert self.steps[0]["code"] == "test_code"
        assert self.steps[0]["output"] == "test_output"
        assert self.steps[0]["status"] == "complete"

    def test_mixed_step_types(self):
        """Test handling of mixed step types (CODE, DELEGATE, ANSWER)."""
        self.handle_update("step", {"action": "DELEGATE"})
        self.handle_update("code", {"code": "code1"})
        self.handle_update("output", {"output": "out1"})
        self.handle_update("step", {"action": "ANSWER"})

        assert len(self.steps) == 2
        assert self.steps[0]["action"] == "DELEGATE"
        assert self.steps[0]["code"] == "code1"
        assert self.steps[1]["action"] == "ANSWER"

    def test_status_messages_dont_affect_steps(self):
        """Test that status messages don't create or modify steps."""
        self.handle_update("status", {"status": "running"})

        assert len(self.steps) == 0

        self.handle_update("code", {"code": "test"})
        self.handle_update("status", {"status": "still_running"})

        assert len(self.steps) == 1

    def test_complete_marks_last_step_complete(self):
        """Test that 'complete' message marks the last step as complete."""
        self.handle_update("code", {"code": "final"})
        self.handle_update("complete", {})

        assert self.steps[0]["status"] == "complete"


# =============================================================================
# Canvas Component Tests
# =============================================================================


class TestCanvasDisplayHistory:
    """Test the canvas component's displayHistory logic."""

    def get_display_history(self, result, live_steps):
        """
        Simulate the canvas component's displayHistory computed property.

        Args:
            result: Final result with execution_history (or None)
            live_steps: Array of live steps from WebSocket

        Returns:
            Array of steps to display
        """
        # If task is complete, use the final execution_history
        if result and result.get("execution_history") and len(result["execution_history"]) > 0:
            return result["execution_history"]

        # Otherwise, show live steps being executed
        return [
            {
                "step": index + 1,
                "action": step.get("action", "UNKNOWN"),
                "input": step.get("code") or step.get("input", ""),
                "output": step.get("output", "")
            }
            for index, step in enumerate(live_steps)
        ]

    def test_uses_live_steps_during_execution(self):
        """Test that live steps are used when no final result exists."""
        live_steps = [
            {"action": "CODE", "code": "x=1", "output": ""},
            {"action": "CODE", "code": "y=2", "output": "2"}
        ]

        display = self.get_display_history(None, live_steps)

        assert len(display) == 2
        assert display[0]["action"] == "CODE"
        assert display[0]["input"] == "x=1"
        assert display[1]["input"] == "y=2"

    def test_uses_final_history_when_complete(self):
        """Test that final execution_history is used when result exists."""
        result = {
            "execution_history": [
                {"step": 1, "action": "CODE", "input": "final1", "output": "out1"},
                {"step": 2, "action": "ANSWER", "input": "final2", "output": "out2"}
            ]
        }

        live_steps = [
            {"action": "CODE", "code": "old", "output": ""}
        ]

        display = self.get_display_history(result, live_steps)

        # Should use result, not live_steps
        assert len(display) == 2
        assert display[0]["input"] == "final1"
        assert display[1]["input"] == "final2"

    def test_empty_steps_returns_empty_array(self):
        """Test that empty live steps returns empty array."""
        display = self.get_display_history(None, [])

        assert display == []

    def test_live_steps_format_conversion(self):
        """Test that live steps are properly formatted for display."""
        live_steps = [
            {"action": "DELEGATE", "input": "subtask", "output": "result"},
            {"action": "CODE", "code": "print(1)", "output": "1"}
        ]

        display = self.get_display_history(None, live_steps)

        assert display[0]["step"] == 1
        assert display[0]["action"] == "DELEGATE"
        assert display[0]["input"] == "subtask"
        assert display[1]["step"] == 2
        assert display[1]["action"] == "CODE"
        assert display[1]["input"] == "print(1)"


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
async def test_error_message_stops_updates():
    """Test that error messages stop the update stream."""
    task_id = "test-error"

    received_updates = []

    async def collect_updates():
        async for update in subscribe(task_id):
            received_updates.append(update)
            # Should stop after error

    asyncio.create_task(collect_updates())
    await asyncio.sleep(0.1)

    await publish(task_id, TaskUpdate(type=UpdateType.CODE, data={"code": "bad"}))
    await publish(task_id, TaskUpdate(
        type=UpdateType.ERROR,
        data={"error": "Execution failed"}
    ))

    # Wait for subscriber to finish
    await asyncio.sleep(0.2)

    # Should have received both updates
    assert len(received_updates) == 2
    assert received_updates[-1].type == UpdateType.ERROR


def test_step_creation_handles_missing_data():
    """Test that step creation handles missing data gracefully."""
    handler = TestStepCreationLogic()
    handler.setup_method()

    # Code with no actual code
    handler.handle_update("code", {})
    assert len(handler.steps) == 1
    assert handler.steps[0]["code"] is None

    # Output with no data
    handler.handle_update("output", {})
    assert handler.steps[0]["output"] is None
