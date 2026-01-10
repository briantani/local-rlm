import contextlib
import io
import os
import traceback
from typing import TYPE_CHECKING

# Import tools to make them available in the sandbox
from src.tools.search import search_web
from src.core.llm_query import create_llm_query

if TYPE_CHECKING:
    from src.core.run_context import RunContext
    from src.core.budget import BudgetManager


class PythonREPL:
    """
    A stateful, secure Python sandbox for executing generated code.

    Provides key variables to code (paper-inspired design):
    - __context_dir__: Where input files are (from --context flag)
    - __artifacts_dir__: Where to save output files (from run_context)
    - __execution_history__: List of dicts with execution steps (code, output)
    - __task__: The original task/query string

    Pre-loaded functions:
    - search_web(query): Search the web using DuckDuckGo
    - llm_query(query, context_chunk): Make recursive sub-LM call on a chunk

    The llm_query function enables paper-style context handling:
        result = llm_query("Summarize this section", context[0:10000])
        results = [llm_query(f"Classify: {item}", item) for item in items]
    """
    def __init__(
        self,
        run_context: "RunContext | None" = None,
        context_dir: str | None = None,
        budget_manager: "BudgetManager | None" = None,
    ):
        self.globals = {}
        self.locals = {}
        self.run_context = run_context
        self.context_dir = context_dir
        self.budget_manager = budget_manager

        # Execution history exposed to code (paper-inspired)
        self._execution_history: list[dict] = []

        # Set up the directories for code execution
        self._setup_directories()

        # Pre-load tools into the sandbox
        self._preload_tools()

    def _setup_directories(self) -> None:
        """Set up input and output directories for code execution."""
        # Set up output directory (where files are saved)
        if self.run_context:
            artifacts_dir = self.run_context.get_working_directory()
            os.makedirs(artifacts_dir, exist_ok=True)
            self.globals["__artifacts_dir__"] = artifacts_dir
            self.globals["__run_context__"] = self.run_context

        # Set up input directory (where context files are)
        if self.context_dir:
            self.globals["__context_dir__"] = self.context_dir

    def _preload_tools(self) -> None:
        """Pre-load commonly used tools into the sandbox globals."""
        # Make search_web directly available (no import needed)
        self.globals["search_web"] = search_web

        # Create and expose llm_query for recursive sub-LM calls (paper-inspired)
        self._llm_query_fn = create_llm_query(budget_manager=self.budget_manager)
        self.globals["llm_query"] = self._llm_query_fn

        # Expose execution history as a list the code can access
        self.globals["__execution_history__"] = self._execution_history

        # Task placeholder (set by agent via set_task)
        self.globals["__task__"] = ""

    def set_task(self, task: str) -> None:
        """Set the current task so code can access it via __task__."""
        self.globals["__task__"] = task

    def add_history_entry(self, code: str, output: str, step: int) -> None:
        """Add an execution history entry accessible to code.

        This enables paper-style context manipulation:
            for entry in __execution_history__:
                if 'error' not in entry['output'].lower():
                    results.append(entry['output'])
        """
        entry = {
            "step": step,
            "code": code,
            "output": output,
            "output_length": len(output),
        }
        self._execution_history.append(entry)
        # Update the global reference
        self.globals["__execution_history__"] = self._execution_history

    def get_history_metadata(self) -> str:
        """Get metadata about execution history (paper-style: LLM sees metadata, not full context).

        This is the key insight from the MIT RLM paper: instead of passing full context
        to the LLM, we pass only metadata. The LLM accesses actual content via code:
            for entry in __execution_history__:
                chunk = entry['output'][:5000]
                summary = llm_query("Summarize", chunk)
        """
        if not self._execution_history:
            return "Execution History: 0 steps. No code executed yet."

        total_chars = sum(len(e["code"]) + len(e["output"]) for e in self._execution_history)
        step_summaries = []

        for entry in self._execution_history:
            # Only show first 80 chars of output as preview
            output_preview = entry["output"][:80].replace("\n", " ")
            if len(entry["output"]) > 80:
                output_preview += "..."
            step_summaries.append(
                f"  Step {entry['step']}: {entry['output_length']} chars output"
            )

        # Keep step summaries concise - only show last 5 steps in detail
        if len(step_summaries) > 5:
            shown_steps = step_summaries[-5:]
            hidden_count = len(step_summaries) - 5
            step_info = f"  ... ({hidden_count} earlier steps)\n" + "\n".join(shown_steps)
        else:
            step_info = "\n".join(step_summaries)

        return (
            f"Execution History: {len(self._execution_history)} steps, {total_chars} chars total.\n"
            f"Access via __execution_history__ in code. Recent steps:\n{step_info}\n"
            f"Use llm_query() on chunks to analyze long outputs."
        )

    def get_last_output_preview(self, max_chars: int = 500) -> str:
        """Get a preview of the last execution output.

        Used to give the Architect a hint about what just happened without
        including the full output in the prompt.
        """
        if not self._execution_history:
            return ""

        last = self._execution_history[-1]
        output = last["output"]
        if len(output) <= max_chars:
            return f"Last output (Step {last['step']}):\n{output}"
        else:
            return (
                f"Last output (Step {last['step']}, {len(output)} chars, truncated):\n"
                f"{output[:max_chars]}...\n"
                f"[Use __execution_history__[-1]['output'] in code for full content]"
            )

    def execute(self, code: str) -> str:
        """
        Executes the given Python code in the sandbox.

        Args:
            code: The Python code to execute.

        Returns:
            The captured stdout or the traceback if an exception occurred.
        """
        # Basic Sanitization
        if "os.system" in code or "subprocess" in code:
             return "SecurityError: Forbidden module or function usage."

        buffer = io.StringIO()

        # Save current directory and change to artifacts dir if available
        original_cwd = os.getcwd()
        artifacts_abs_dir = None
        if self.run_context:
            # Use absolute path to avoid issues after chdir
            artifacts_abs_dir = self.run_context.artifacts_dir.absolute()
            os.chdir(str(artifacts_abs_dir))

        try:
            with contextlib.redirect_stdout(buffer):
                exec(code, self.globals, self.locals)
            output = buffer.getvalue().strip()

            # Track any files that were created
            if self.run_context and artifacts_abs_dir:
                self._detect_created_files(artifacts_abs_dir)

            return output
        except Exception:
            # Return traceback as string, don't crash
            return traceback.format_exc()
        finally:
            # Restore original working directory
            os.chdir(original_cwd)

    def _detect_created_files(self, artifacts_dir) -> None:
        """Detect and register any new files created during execution."""
        if not self.run_context:
            return

        for file_path in artifacts_dir.iterdir():
            if file_path.is_file():
                filename = file_path.name
                # Check if already registered
                if not any(a["filename"] == filename for a in self.run_context.artifacts):
                    # Determine artifact type based on extension
                    ext = file_path.suffix.lower()
                    if ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
                        artifact_type = "image"
                    elif ext in (".md", ".txt", ".html"):
                        artifact_type = "report"
                    elif ext in (".csv", ".json", ".xlsx"):
                        artifact_type = "data"
                    else:
                        artifact_type = "file"

                    self.run_context.artifacts.append({
                        "filename": filename,
                        "path": str(file_path),
                        "type": artifact_type,
                        "description": f"Auto-detected {artifact_type}",
                        "created_at": None,
                    })
