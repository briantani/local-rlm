"""
REPL Code Executor.

Handles code execution, extraction, and artifact detection.

Phase 3: REPL refactoring
"""

import os
import re
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any

from RestrictedPython import compile_restricted_exec
from src.core.parser import is_final, parse_response

if TYPE_CHECKING:
    from src.core.run_context import RunContext


class CodeExecutor:
    """Executes code in a restricted Python sandbox."""

    @staticmethod
    def execute(
        code: str,
        globals_dict: dict[str, Any],
        locals_dict: dict[str, Any],
        run_context: "RunContext | None" = None,
    ) -> str:
        """Execute Python code in a RestrictedPython sandbox.

        Args:
            code: The Python code to execute
            globals_dict: Global variables for execution
            locals_dict: Local variables for execution (modified in place)
            run_context: Optional run context for artifact tracking

        Returns:
            The captured stdout or error traceback
        """
        # Extract code from markdown blocks if present
        code = CodeExecutor._extract_code(code)

        if not code.strip():
            return "No code to execute"

        # Basic sanitization (RestrictedPython handles most)
        forbidden = ["os.system", "subprocess", "__builtins__"]
        for pattern in forbidden:
            if pattern in code:
                return f"SecurityError: Forbidden pattern '{pattern}' detected."

        # Save and change working directory
        original_cwd = os.getcwd()
        artifacts_abs_dir = None
        if run_context:
            artifacts_abs_dir = run_context.artifacts_dir.absolute()
            os.chdir(str(artifacts_abs_dir))

        try:
            # Compile with RestrictedPython
            byte_code = compile_restricted_exec(code)

            if byte_code.errors:
                error_msg = ", ".join(byte_code.errors)
                return f"CompilationError: {error_msg}"

            # Prepare execution environment
            exec_globals = globals_dict.copy()
            exec_globals.update(locals_dict)

            # Execute the code
            exec(byte_code.code, exec_globals, locals_dict)

            # Get output from PrintCollector
            output = ""
            if "_print" in locals_dict:
                print_collector = locals_dict["_print"]
                if callable(print_collector):
                    output = print_collector()
                elif hasattr(print_collector, "txt"):
                    output = "".join(print_collector.txt)

            # Check if last line was an expression
            lines = code.strip().split("\n")
            if lines:
                last_line = lines[-1].strip()
                keywords = [
                    "=", "import", "def", "class", "if", "for", "while",
                    "with", "try", "return",
                ]
                if last_line and not any(kw in last_line for kw in keywords):
                    try:
                        result = eval(last_line, exec_globals, locals_dict)
                        if result is not None:
                            output += str(result) + "\n"
                    except Exception:
                        pass  # Not an expression

            # Copy variables back to globals
            for key, value in locals_dict.items():
                if not key.startswith("_"):
                    globals_dict[key] = value

            if not output.strip():
                output = "Code executed successfully (no output)"

            # Detect created files
            if run_context and artifacts_abs_dir:
                CodeExecutor._detect_created_files(artifacts_abs_dir, run_context)

            return output.strip()

        except Exception as e:
            return f"ExecutionError: {e}\n{traceback.format_exc()}"

        finally:
            os.chdir(original_cwd)

    @staticmethod
    def _extract_code(text: str) -> str:
        """Extract Python code from markdown blocks or return as-is.

        Args:
            text: Text that may contain markdown code blocks

        Returns:
            Extracted Python code
        """
        # Try to extract from markdown code block
        match = re.search(r'```(?:python)?\n(.*?)\n```', text, re.DOTALL)
        if match:
            return match.group(1)
        return text

    @staticmethod
    def _detect_created_files(artifacts_dir: Path, run_context: "RunContext") -> None:
        """Detect and register any new files created during execution.

        Args:
            artifacts_dir: Directory where files may have been created
            run_context: Run context for registering artifacts
        """
        if not run_context:
            return

        for file_path in artifacts_dir.iterdir():
            if file_path.is_file():
                filename = file_path.name
                # Check if already registered
                if not any(a["filename"] == filename for a in run_context.artifacts):
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

                    run_context.artifacts.append({
                        "filename": filename,
                        "path": str(file_path),
                        "type": artifact_type,
                        "description": f"Auto-detected {artifact_type}",
                        "created_at": None,
                    })

    @staticmethod
    def check_for_final(output: str, globals_dict: dict, locals_dict: dict) -> str | None:
        """Check if output contains FINAL() termination and extract answer.

        Paper-style termination: when code outputs FINAL("answer"), the
        agent should return immediately.

        Args:
            output: The code execution output
            globals_dict: Global variables for variable lookup
            locals_dict: Local variables for variable lookup

        Returns:
            The final answer if FINAL() detected, None otherwise
        """
        if is_final(output):
            env = {**globals_dict, **locals_dict}
            return parse_response(output, env)
        return None
