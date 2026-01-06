"""
Export API Routes.

Handles exporting task results to various formats (Markdown, JSON).
Phase 17: Canvas & Export Features
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Response
import json

from src.web.database import get_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks/{task_id}/export", tags=["Export"])


@router.get("/markdown")
async def export_markdown(task_id: str):
    """
    Export task results as Markdown file.

    Args:
        task_id: Task identifier

    Returns:
        Markdown file download
    """
    # Get task
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.result:
        raise HTTPException(status_code=400, detail="Task has no result to export")

    # Build Markdown content
    result = task.result
    markdown = f"""# Task Result: {task.task_text[:60]}...

**Status**: {task.status.value}
**Configuration**: {task.config_name}
**Created**: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}
**Completed**: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else 'N/A'}

---

## Final Answer

{result.get('answer', 'No answer provided')}

---

## Execution Details

- **Total Cost**: ${result.get('total_cost', 0):.4f}
- **Duration**: {result.get('duration_seconds', 0):.1f} seconds
- **Steps**: {result.get('step_count', 0)}

"""

    # Add execution history if available
    if 'execution_history' in result and result['execution_history']:
        markdown += "\n---\n\n## Execution History\n\n"
        for i, step in enumerate(result['execution_history'], 1):
            markdown += f"### Step {i}: {step.get('action', 'Unknown')}\n\n"
            
            if step.get('input'):
                markdown += f"**Input:**\n```\n{step['input'][:500]}\n```\n\n"
            
            if step.get('output'):
                markdown += f"**Output:**\n```\n{step['output'][:1000]}\n```\n\n"

    # Add model breakdown if available
    if 'model_breakdown' in result and result['model_breakdown']:
        markdown += "\n---\n\n## Model Usage\n\n"
        for model, cost in result['model_breakdown'].items():
            markdown += f"- **{model}**: ${cost:.4f}\n"

    # Return as downloadable file
    return Response(
        content=markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=task_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        }
    )


@router.get("/json")
async def export_json(task_id: str):
    """
    Export full task data as JSON.

    Args:
        task_id: Task identifier

    Returns:
        JSON file download with complete task data
    """
    # Get task
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Build complete JSON export
    export_data = {
        "task_id": task.id,
        "task_text": task.task_text,
        "config_name": task.config_name,
        "status": task.status.value,
        "session_id": task.session_id,
        "created_at": task.created_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "result": task.result if task.result else None,
        "exported_at": datetime.now().isoformat(),
        "version": "1.0"
    }

    # Return as downloadable JSON file
    return Response(
        content=json.dumps(export_data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=task_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        }
    )
