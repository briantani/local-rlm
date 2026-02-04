"""
Python REPL for RLM Agent.

A stateful, secure Python sandbox for executing generated code.

Uses RestrictedPython for safer execution (paper-style). Provides key variables
to generated code for interacting with the problem space and the agent itself.

Phase 12: Core Library Refactoring
Phase 3: Refactored to use repl_sandbox, repl_history, repl_environment, repl_executor
"""

import os
import logging
from typing import TYPE_CHECKING, Any

# Data science libraries (pre-loaded for code execution)
try:
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
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

# Import refactored components
from src.core.repl_sandbox import SandboxGuards
from src.core.repl_history import ExecutionHistory
from src.core.repl_environment import EnvironmentSetup
from src.core.repl_executor import CodeExecutor

if TYPE_CHECKING:
    from src.core.run_context import RunContext
    from src.core.budget import BudgetManager


logger = logging.getLogger(__name__)


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

    Phase 3: Refactored to delegate to repl_sandbox, repl_history, repl_environment, repl_executor
    """

    def __init__(
        self,
        run_context: "RunContext | None" = None,
        context_dir: str | None = None,
        budget_manager: "BudgetManager | None" = None,
        agent_config: "Any" = None,
        current_depth: int = 0,
        max_depth: int = 5,
    ):
        """Initialize the REPL sandbox.

        Args:
            run_context: Optional run context for artifact tracking
            context_dir: Optional directory for input files
            budget_manager: Optional budget manager for tracking costs
            agent_config: Optional agent config for recursive_llm
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth
        """
        self.run_context = run_context
        self.context_dir = context_dir
        self.budget_manager = budget_manager
        self.agent_config = agent_config
        self.current_depth = current_depth
        self.max_depth = max_depth

        # Execution history
        self._history = ExecutionHistory()

        # Build restricted globals using sandbox module
        self.globals = self._build_globals()
        self.locals: dict[str, Any] = {}

        # Set up directories
        EnvironmentSetup.setup_directories(
            self.globals, run_context, context_dir
        )

        # Pre-load tools
        EnvironmentSetup.preload_tools(
            self.globals,
            budget_manager=budget_manager,
            agent_config=agent_config,
            current_depth=current_depth,
            max_depth=max_depth,
        )

        # Set execution history to be accessible
        self.globals["__execution_history__"] = self._history.get_all()
        self.globals["history"] = self._history.get_all()

    def _build_globals(self) -> dict[str, Any]:
        """Build restricted globals with safe builtins and libraries."""
        restricted = SandboxGuards.build_restricted_globals()

        # Add standard library modules
        import re
        import json
        import math
        from datetime import timedelta
        from collections import Counter, defaultdict
        from pathlib import Path
        import io

        restricted.update({
            "re": re,
            "json": json,
            "math": math,
            "timedelta": timedelta,
            "Counter": Counter,
            "defaultdict": defaultdict,
            "Path": Path,
            "StringIO": io.StringIO,
            "BytesIO": io.BytesIO,
        })

        # Add safe os.path subset
        class SafeOsPath:
            """Safe subset of os.path."""
            exists = staticmethod(os.path.exists)
            isfile = staticmethod(os.path.isfile)
            isdir = staticmethod(os.path.isdir)
            join = staticmethod(os.path.join)
            basename = staticmethod(os.path.basename)
            dirname = staticmethod(os.path.dirname)
            splitext = staticmethod(os.path.splitext)

        class SafeOs:
            """Safe subset of os."""
            path = SafeOsPath()
            listdir = staticmethod(os.listdir)

        restricted["os"] = SafeOs()

        # Add data science libraries
        if HAS_DATA_SCIENCE_LIBS:
            restricted.update({
                "np": np,
                "numpy": np,
                "pd": pd,
                "pandas": pd,
                "plt": plt,
                "matplotlib": matplotlib,
            })

        if HAS_SEABORN:
            restricted.update({"sns": sns, "seaborn": sns})

        if HAS_SCIPY:
            restricted.update({
                "scipy": scipy,
                "scipy_stats": scipy_stats,
            })

        if HAS_SKLEARN:
            restricted.update({
                "sklearn": sklearn,
                "LinearRegression": sklearn_linear.LinearRegression if sklearn_linear else None,
                "LogisticRegression": sklearn_linear.LogisticRegression if sklearn_linear else None,
                "KMeans": sklearn_cluster.KMeans if sklearn_cluster else None,
                "StandardScaler": sklearn_preprocessing.StandardScaler if sklearn_preprocessing else None,
                "sklearn_metrics": sklearn_metrics,
            })

        if HAS_STATSMODELS:
            restricted.update({"statsmodels": statsmodels, "sm": sm})

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

    def set_task(self, task: str) -> None:
        """Set the task description for the REPL.

        Args:
            task: The task/query string
        """
        self.globals["__task__"] = task
        self.globals["task"] = task
        logger.debug(f"Task set: {task[:100]}...")

    def add_history_entry(self, code: str, output: str, step: int) -> None:
        """Add an execution entry to history.

        Args:
            code: The code that was executed
            output: The output from execution
            step: The step number
        """
        self._history.add_entry(code, output, step)
        # Update globals with latest history
        self.globals["__execution_history__"] = self._history.get_all()
        self.globals["history"] = self._history.get_all()
        # Update context with last output (just the output, no labels)
        self.globals["context"] = self._history.get_last_output()

    def get_history_metadata(self) -> str:
        """Get formatted execution history as metadata.

        Returns:
            Formatted history string
        """
        return self._history.get_metadata_str()

    def get_last_output_preview(self, max_chars: int = 500) -> str:
        """Get preview of last execution output.

        Args:
            max_chars: Maximum characters to include

        Returns:
            Last output preview
        """
        return self._history.get_last_output_preview(max_chars)

    def execute(self, code: str) -> str:
        """Execute Python code in the sandbox.

        Args:
            code: Python code to execute

        Returns:
            Captured stdout or error traceback
        """
        output = CodeExecutor.execute(
            code, self.globals, self.locals, self.run_context
        )
        return output

    def check_for_final(self, output: str) -> str | None:
        """Check for FINAL() termination and extract answer.

        Args:
            output: Code execution output

        Returns:
            Final answer if FINAL() detected, None otherwise
        """
        return CodeExecutor.check_for_final(output, self.globals, self.locals)
