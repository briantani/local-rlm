import contextlib
import io
import os
import traceback
from typing import TYPE_CHECKING

# Import tools to make them available in the sandbox
from src.tools.search import search_web

if TYPE_CHECKING:
    from src.core.run_context import RunContext


class PythonREPL:
    """
    A stateful, secure Python sandbox for executing generated code.

    Provides two key directories to code:
    - __context_dir__: Where input files are (from --context flag)
    - __artifacts_dir__: Where to save output files (from run_context)

    Pre-loaded functions:
    - search_web(query): Search the web using DuckDuckGo
    """
    def __init__(
        self,
        run_context: "RunContext | None" = None,
        context_dir: str | None = None,
    ):
        self.globals = {}
        self.locals = {}
        self.run_context = run_context
        self.context_dir = context_dir

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
