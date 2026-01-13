import os
import re
import io
import json
import math
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any

# Data science libraries (pre-loaded for code execution)
try:
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend for saving files
    import matplotlib.pyplot as plt
    HAS_DATA_SCIENCE_LIBS = True
except ImportError:
    np = None
    pd = None
    plt = None
    HAS_DATA_SCIENCE_LIBS = False

# Extended data science libraries
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    sns = None
    HAS_SEABORN = False

try:
    import scipy
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    scipy = None
    scipy_stats = None
    HAS_SCIPY = False

try:
    import sklearn
    from sklearn import (
        linear_model as sklearn_linear,
        cluster as sklearn_cluster,
        preprocessing as sklearn_preprocessing,
        metrics as sklearn_metrics,
    )
    HAS_SKLEARN = True
except ImportError:
    sklearn = None
    sklearn_linear = None
    sklearn_cluster = None
    sklearn_preprocessing = None
    sklearn_metrics = None
    HAS_SKLEARN = False

try:
    import statsmodels
    import statsmodels.api as sm
    HAS_STATSMODELS = True
except ImportError:
    statsmodels = None
    sm = None
    HAS_STATSMODELS = False

# Document processing libraries
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    pdfplumber = None
    HAS_PDFPLUMBER = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    pypdf = None
    HAS_PYPDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    docx = None
    HAS_DOCX = False

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    openpyxl = None
    HAS_OPENPYXL = False

# RestrictedPython for safer code execution (paper-style)
from RestrictedPython import compile_restricted_exec, safe_globals
from RestrictedPython.Guards import (
    guarded_iter_unpack_sequence,
    safer_getattr,
    guarded_unpack_sequence,
)
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.PrintCollector import PrintCollector  # Use built-in PrintCollector

# Import tools to make them available in the sandbox
from src.tools.search import search_web
from src.core.llm_query import create_llm_query
from src.core.parser import is_final, parse_response

if TYPE_CHECKING:
    from src.core.run_context import RunContext
    from src.core.budget import BudgetManager


class PythonREPL:
    """
    A stateful, secure Python sandbox for executing generated code.

    Uses RestrictedPython for safer execution (paper-style).

    Provides key variables to code (paper-inspired design):
    - context: Last output or empty string (simple paper-style access)
    - history: List of dicts with execution steps (alias for __execution_history__)
    - __context_dir__: Where input files are (from --context flag)
    - __artifacts_dir__: Where to save output files (from run_context)
    - __execution_history__: List of dicts with execution steps (code, output)
    - __task__: The original task/query string

    Pre-loaded functions:
    - search_web(query): Search the web using DuckDuckGo
    - llm_query(query, context_chunk): Make recursive sub-LM call on a chunk
    - recursive_llm(sub_query, sub_context): Spawn sub-agent (paper-style recursion)
    - FINAL(answer): Paper-style termination (detected by agent)

    The recursive_llm function enables paper-style emergent recursion:
        result = recursive_llm("Analyze this section", context[0:10000])
        results = [recursive_llm(f"Process: {item}", item) for item in items]
    """
    def __init__(
        self,
        run_context: "RunContext | None" = None,
        context_dir: str | None = None,
        budget_manager: "BudgetManager | None" = None,
        # Agent factory for recursive_llm (paper-style recursion)
        agent_config: "Any" = None,
        current_depth: int = 0,
        max_depth: int = 5,
    ):
        self.run_context = run_context
        self.context_dir = context_dir
        self.budget_manager = budget_manager
        self.agent_config = agent_config
        self.current_depth = current_depth
        self.max_depth = max_depth

        # Execution history exposed to code (paper-inspired)
        self._execution_history: list[dict] = []

        # Build restricted globals with safe builtins
        self.globals = self._build_restricted_globals()
        self.locals: dict[str, Any] = {}

        # Set up the directories for code execution
        self._setup_directories()

        # Pre-load tools into the sandbox
        self._preload_tools()

    def _build_restricted_globals(self) -> dict[str, Any]:
        """Build a restricted globals dict with safe builtins.

        Based on RestrictedPython patterns from the paper's implementation.
        """
        restricted = dict(safe_globals)

        # Add RestrictedPython guards
        restricted["_getattr_"] = safer_getattr
        restricted["_getitem_"] = default_guarded_getitem
        restricted["_getiter_"] = default_guarded_getiter
        restricted["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence
        restricted["_unpack_sequence_"] = guarded_unpack_sequence

        # Add in-place variable helper for augmented assignment (+=, -=, etc.)
        restricted["_inplacevar_"] = self._inplacevar

        # Add write guard for attribute/item assignment (obj.attr = x, obj[key] = x)
        # This is required for operations like df['col'] = values, df.at[i, j] = val
        restricted["_write_"] = self._write_guard

        # Add print collector
        restricted["_print_"] = PrintCollector

        # Add safe builtins that RestrictedPython allows
        safe_builtins = {
            # Types
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "frozenset": frozenset,
            "bytes": bytes,
            "bytearray": bytearray,
            # Iteration
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "reversed": reversed,
            "iter": iter,
            "next": next,
            # Aggregation
            "sorted": sorted,
            "sum": sum,
            "min": min,
            "max": max,
            "any": any,
            "all": all,
            # Math
            "abs": abs,
            "round": round,
            "pow": pow,
            "divmod": divmod,
            # String/repr
            "chr": chr,
            "ord": ord,
            "hex": hex,
            "oct": oct,
            "bin": bin,
            "repr": repr,
            "ascii": ascii,
            "format": format,
            # Type checking
            "isinstance": isinstance,
            "issubclass": issubclass,
            "callable": callable,
            "type": type,
            "hasattr": hasattr,
            "getattr": getattr,
            # Other
            "open": open,  # Needed for file reading (sandbox handles security)
            "print": print,  # Will be captured by PrintCollector
            "input": None,  # Disabled
            "exec": None,  # Disabled
            "eval": None,  # Disabled
            "compile": None,  # Disabled
            "__import__": None,  # Disabled
        }
        restricted.update(safe_builtins)

        # Add safe standard library modules (read-only, no system access)
        restricted.update({
            "re": re,
            "json": json,
            "math": math,
            "datetime": datetime,
            "timedelta": timedelta,
            "Counter": Counter,
            "defaultdict": defaultdict,
            "Path": Path,  # pathlib.Path for file path handling
            "StringIO": io.StringIO,  # For in-memory text streams
            "BytesIO": io.BytesIO,  # For in-memory binary streams
        })

        # Add limited os.path functions for file checking (no system access)
        # Create a safe os module with only path-related functions
        class SafeOsPath:
            """Safe subset of os.path for file operations."""
            exists = staticmethod(os.path.exists)
            isfile = staticmethod(os.path.isfile)
            isdir = staticmethod(os.path.isdir)
            join = staticmethod(os.path.join)
            basename = staticmethod(os.path.basename)
            dirname = staticmethod(os.path.dirname)
            splitext = staticmethod(os.path.splitext)

        class SafeOs:
            """Safe subset of os module with only path operations."""
            path = SafeOsPath()
            # Add listdir for directory listing
            listdir = staticmethod(os.listdir)

        restricted["os"] = SafeOs()

        # Add data science libraries if available
        if HAS_DATA_SCIENCE_LIBS:
            restricted.update({
                "np": np,
                "numpy": np,
                "pd": pd,
                "pandas": pd,
                "plt": plt,
                "matplotlib": matplotlib,
            })

        # Add seaborn for statistical visualization
        if HAS_SEABORN:
            restricted.update({
                "sns": sns,
                "seaborn": sns,
            })

        # Add scipy for scientific computing
        if HAS_SCIPY:
            restricted.update({
                "scipy": scipy,
                "scipy_stats": scipy_stats,  # scipy.stats
            })

        # Add scikit-learn for machine learning
        if HAS_SKLEARN:
            restricted.update({
                "sklearn": sklearn,
                "LinearRegression": sklearn_linear.LinearRegression if sklearn_linear else None,
                "LogisticRegression": sklearn_linear.LogisticRegression if sklearn_linear else None,
                "KMeans": sklearn_cluster.KMeans if sklearn_cluster else None,
                "StandardScaler": sklearn_preprocessing.StandardScaler if sklearn_preprocessing else None,
                "sklearn_metrics": sklearn_metrics,
            })

        # Add statsmodels for statistical analysis
        if HAS_STATSMODELS:
            restricted.update({
                "statsmodels": statsmodels,
                "sm": sm,  # statsmodels.api
            })

        # Add document processing libraries
        if HAS_PDFPLUMBER:
            restricted["pdfplumber"] = pdfplumber
        if HAS_PYPDF:
            restricted["pypdf"] = pypdf
        if HAS_DOCX:
            restricted["docx"] = docx
        if HAS_OPENPYXL:
            restricted["openpyxl"] = openpyxl

        return restricted

    def _setup_directories(self) -> None:
        """Set up input and output directories for code execution."""
        # Set up output directory (where files are saved)
        if self.run_context:
            artifacts_dir = self.run_context.get_working_directory()
            os.makedirs(artifacts_dir, exist_ok=True)
            self.globals["__artifacts_dir__"] = artifacts_dir
            self.globals["output_dir"] = artifacts_dir  # Simple alias for RestrictedPython
            self.globals["__run_context__"] = self.run_context

            # Default input_dir to output_dir if no context_dir provided
            # This ensures input_dir is always defined for delegates
            if not self.context_dir:
                self.globals["__context_dir__"] = artifacts_dir
                self.globals["input_dir"] = artifacts_dir

        # Set up input directory (where context files are)
        if self.context_dir:
            self.globals["__context_dir__"] = self.context_dir
            self.globals["input_dir"] = self.context_dir  # Simple alias for RestrictedPython

    def _preload_tools(self) -> None:
        """Pre-load commonly used tools into the sandbox globals."""
        # Make search_web directly available (no import needed)
        self.globals["search_web"] = search_web

        # Create and expose llm_query for recursive sub-LM calls (paper-inspired)
        self._llm_query_fn = create_llm_query(budget_manager=self.budget_manager)
        self.globals["llm_query"] = self._llm_query_fn

        # Create recursive_llm for spawning sub-agents (paper-style)
        self._recursive_llm_fn = self._create_recursive_llm()
        self.globals["recursive_llm"] = self._recursive_llm_fn

        # Expose execution history as a list the code can access
        self.globals["__execution_history__"] = self._execution_history

        # Simpler aliases for paper-style access
        self.globals["history"] = self._execution_history  # history[-1]['output']

        # context = last output (simple paper-style: context[:100])
        self.globals["context"] = ""

        # Task placeholder (set by agent via set_task)
        self.globals["__task__"] = ""
        self.globals["task"] = ""  # Simple alias

    @staticmethod
    def _inplacevar(op: str, x: Any, y: Any) -> Any:
        """Implement in-place operations for RestrictedPython.

        RestrictedPython requires this helper for augmented assignment (+=, -=, etc.)
        because it rewrites `x += y` to `x = _inplacevar_('+=', x, y)`.
        """
        if op == "+=":
            return x + y
        elif op == "-=":
            return x - y
        elif op == "*=":
            return x * y
        elif op == "/=":
            return x / y
        elif op == "//=":
            return x // y
        elif op == "%=":
            return x % y
        elif op == "**=":
            return x ** y
        elif op == "&=":
            return x & y
        elif op == "|=":
            return x | y
        elif op == "^=":
            return x ^ y
        elif op == ">>=":
            return x >> y
        elif op == "<<=":
            return x << y
        else:
            raise ValueError(f"Unsupported in-place operation: {op}")

    @staticmethod
    def _write_guard(obj: Any) -> Any:
        """Guard for write operations in RestrictedPython.

        RestrictedPython rewrites attribute/item assignment to use _write_:
            obj.attr = val  ->  _write_(obj).attr = val
            obj[key] = val  ->  _write_(obj)[key] = val

        We allow writes to most objects but could add restrictions here.
        For pandas DataFrames/Series, numpy arrays, dicts, lists - we allow writes.
        """
        # Allow writes to common data types used in data science
        # Could add restrictions here if needed for security
        return obj

    def _create_recursive_llm(self):
        """Create a recursive_llm function for paper-style sub-agent spawning.

        This function allows code to spawn a sub-agent to handle a sub-task:
            result = recursive_llm("Analyze this section", context[0:10000])

        The sub-agent runs at depth+1 and shares budget tracking.

        Returns:
            A callable that spawns a sub-agent and returns the result string.
        """
        def recursive_llm(sub_query: str, sub_context: str = "") -> str:
            """Spawn a sub-agent to handle a sub-task (paper-style recursion).

            Args:
                sub_query: The sub-task to solve.
                sub_context: Optional context string for the sub-agent.

            Returns:
                The sub-agent's final answer as a string.
            """
            # Check depth limit
            if self.current_depth >= self.max_depth:
                return f"[ERROR: Max recursion depth ({self.max_depth}) reached. Cannot spawn sub-agent.]"

            # Only import here to avoid circular imports
            from src.core.agent import RLMAgent

            try:
                # Create sub-agent at depth+1
                sub_agent = RLMAgent(
                    depth=self.current_depth + 1,
                    config=self.agent_config,
                    is_delegate=True,
                    budget_manager=self.budget_manager,
                    run_context=self.run_context,
                    root_dir=self.context_dir,
                )

                # If sub_context provided, add it to the task
                if sub_context:
                    # Truncate context if too long for prompt
                    if len(sub_context) > 50000:
                        sub_context = sub_context[:50000] + "\n...[truncated]..."
                    full_query = f"{sub_query}\n\nContext:\n{sub_context}"
                else:
                    full_query = sub_query

                # Run the sub-agent
                result = sub_agent.run(full_query)
                return result

            except Exception as e:
                return f"[ERROR in recursive_llm: {e}]"

        return recursive_llm

    def set_task(self, task: str) -> None:
        """Set the current task so code can access it via __task__ or task."""
        self.globals["__task__"] = task
        self.globals["task"] = task  # Simple alias

    def add_history_entry(self, code: str, output: str, step: int) -> None:
        """Add an execution history entry accessible to code.

        This enables paper-style context manipulation:
            for entry in __execution_history__:
                if 'error' not in entry['output'].lower():
                    results.append(entry['output'])

        Also updates 'context' to the last output for simple paper-style access:
            print(context[:100])  # See first 100 chars of last output
        """
        entry = {
            "step": step,
            "code": code,
            "output": output,
            "output_length": len(output),
        }
        self._execution_history.append(entry)

        # Update the global references
        self.globals["__execution_history__"] = self._execution_history
        self.globals["history"] = self._execution_history

        # Update 'context' to last output (paper-style: context[:100])
        self.globals["context"] = output

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
                f"[Use __execution_history__[-1]['output'] or context in code for full content]"
            )

    def _extract_code(self, text: str) -> str:
        """Extract code from markdown code blocks if present.

        LLMs often wrap code in ```python ... ``` blocks.
        """
        # Try to extract from code blocks
        code_block_pattern = r"```(?:python)?\s*\n(.*?)```"
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        if matches:
            return "\n".join(matches)
        return text

    def execute(self, code: str) -> str:
        """
        Executes the given Python code in a RestrictedPython sandbox.

        Uses RestrictedPython for safer execution (paper-style).
        Supports FINAL("answer") termination pattern.

        Args:
            code: The Python code to execute.

        Returns:
            The captured stdout or the traceback if an exception occurred.
        """
        # Extract code from markdown blocks if present
        code = self._extract_code(code)

        if not code.strip():
            return "No code to execute"

        # Basic Sanitization (RestrictedPython handles most, but extra safety)
        forbidden = ["os.system", "subprocess", "__builtins__"]
        for pattern in forbidden:
            if pattern in code:
                return f"SecurityError: Forbidden pattern '{pattern}' detected."

        # Save current directory and change to artifacts dir if available
        original_cwd = os.getcwd()
        artifacts_abs_dir = None
        if self.run_context:
            # Use absolute path to avoid issues after chdir
            artifacts_abs_dir = self.run_context.artifacts_dir.absolute()
            os.chdir(str(artifacts_abs_dir))

        try:
            # Compile with RestrictedPython for safer execution
            byte_code = compile_restricted_exec(code)

            if byte_code.errors:
                error_msg = ", ".join(byte_code.errors)
                return f"CompilationError: {error_msg}"

            # Prepare execution environment
            exec_globals = self.globals.copy()
            exec_globals.update(self.locals)

            # Execute the code
            exec(byte_code.code, exec_globals, self.locals)

            # Get output from PrintCollector (RestrictedPython pattern)
            # _print is created during execution when print() is called
            output = ""
            if "_print" in self.locals:
                print_collector = self.locals["_print"]
                # Call the PrintCollector to get output
                if callable(print_collector):
                    output = print_collector()
                elif hasattr(print_collector, "txt"):
                    output = "".join(print_collector.txt)

            # Check if last line was an expression (return its value)
            lines = code.strip().split("\n")
            if lines:
                last_line = lines[-1].strip()
                # If last line is a simple expression (no assignment, no keyword)
                keywords = ["=", "import", "def", "class", "if", "for", "while", "with", "try", "return"]
                if last_line and not any(kw in last_line for kw in keywords):
                    try:
                        result = eval(last_line, exec_globals, self.locals)
                        if result is not None:
                            output += str(result) + "\n"
                    except Exception:
                        pass  # Not an expression, ignore

            # Copy back any new variables to globals for persistence
            for key, value in self.locals.items():
                if not key.startswith("_"):
                    self.globals[key] = value

            if not output.strip():
                output = "Code executed successfully (no output)"

            # Track any files that were created
            if self.run_context and artifacts_abs_dir:
                self._detect_created_files(artifacts_abs_dir)

            return output.strip()

        except Exception as e:
            # Return traceback as string, don't crash
            return f"ExecutionError: {e}\n{traceback.format_exc()}"

        finally:
            # Restore original working directory
            os.chdir(original_cwd)

    def check_for_final(self, output: str) -> str | None:
        """Check if output contains FINAL() termination and extract answer.

        Paper-style termination: when code outputs FINAL("answer"), the
        agent should return immediately.

        Args:
            output: The code execution output

        Returns:
            The final answer if FINAL() detected, None otherwise
        """
        if is_final(output):
            # Combine globals and locals for variable lookup
            env = {**self.globals, **self.locals}
            return parse_response(output, env)
        return None

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
