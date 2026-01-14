import os
if not os.getenv("RLM_RUN_INTEGRATION"):
    import pytest
    pytest.skip("Integration web tests disabled; set RLM_RUN_INTEGRATION=1 to run", allow_module_level=True)

import pytest
import asyncio

from src.web.task_runner import UpdateType, TaskUpdate, publish, subscribe


@pytest.mark.asyncio
async def test_publish_step_update():
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

    received_updates = []

    async def collect_updates():
        async for update in subscribe(task_id):
            received_updates.append(update)
            if update.type == UpdateType.COMPLETE:
                break

    subscriber_task = asyncio.create_task(collect_updates())
    await asyncio.sleep(0.1)
    await publish(task_id, update)
    await publish(task_id, TaskUpdate(type=UpdateType.COMPLETE, data={}))
    await subscriber_task

    assert len(received_updates) == 2
    assert received_updates[0].type == UpdateType.STEP
    assert received_updates[1].type == UpdateType.COMPLETE
