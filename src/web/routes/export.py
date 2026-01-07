"""
Export API Routes.

Handles exporting task results to various formats (Markdown, JSON, PDF).
Phase 17: Canvas & Export Features
"""

import logging
from datetime import datetime
from io import BytesIO
from fastapi import APIRouter, HTTPException, Response
import json
import markdown
from weasyprint import HTML

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


@router.get("/pdf")
async def export_pdf(task_id: str):
    """
    Export task results as PDF file.

    Args:
        task_id: Task identifier

    Returns:
        PDF file download
    """
    # Get task
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.result:
        raise HTTPException(status_code=400, detail="Task has no result to export")

    # Build Markdown content (same as markdown export)
    result = task.result
    markdown_content = f"""# Task Result: {task.task_text[:60]}...

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
        markdown_content += "\n---\n\n## Execution History\n\n"
        for i, step in enumerate(result['execution_history'], 1):
            markdown_content += f"### Step {i}: {step.get('action', 'Unknown')}\n\n"

            if step.get('input'):
                markdown_content += f"**Input:**\n```\n{step['input'][:500]}\n```\n\n"

            if step.get('output'):
                markdown_content += f"**Output:**\n```\n{step['output'][:1000]}\n```\n\n"

    # Add model breakdown if available
    if 'model_breakdown' in result and result['model_breakdown']:
        markdown_content += "\n---\n\n## Model Usage\n\n"
        for model, cost in result['model_breakdown'].items():
            markdown_content += f"- **{model}**: ${cost:.4f}\n"

    # Convert Markdown to HTML
    html_content = markdown.markdown(
        markdown_content,
        extensions=['fenced_code', 'tables', 'nl2br']
    )

    # Wrap in styled HTML document
    styled_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Task Result - {task_id}</title>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
            }}
            h1 {{
                color: #2563eb;
                border-bottom: 3px solid #2563eb;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #4f46e5;
                margin-top: 30px;
                border-bottom: 2px solid #e5e7eb;
                padding-bottom: 8px;
            }}
            h3 {{
                color: #6366f1;
                margin-top: 20px;
            }}
            code {{
                background-color: #f3f4f6;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
            }}
            pre {{
                background-color: #1f2937;
                color: #f3f4f6;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                font-family: 'Courier New', monospace;
                font-size: 0.85em;
                line-height: 1.4;
            }}
            pre code {{
                background-color: transparent;
                padding: 0;
                color: inherit;
            }}
            hr {{
                border: none;
                border-top: 1px solid #e5e7eb;
                margin: 30px 0;
            }}
            strong {{
                color: #1f2937;
            }}
            ul, ol {{
                margin-left: 20px;
            }}
            li {{
                margin-bottom: 8px;
            }}
        </style>
    </head>
    <body>
        {html_content}
        <hr>
        <p style="text-align: center; color: #9ca3af; font-size: 0.9em; margin-top: 40px;">
            Generated by RLM Agent | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </body>
    </html>
    """

    # Convert HTML to PDF using WeasyPrint
    pdf_file = BytesIO()
    HTML(string=styled_html).write_pdf(pdf_file)
    pdf_file.seek(0)

    # Return as downloadable PDF file
    return Response(
        content=pdf_file.read(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=task_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        }
    )
