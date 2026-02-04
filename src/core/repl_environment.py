"""
REPL Environment and Tool Setup.

Handles directory setup and pre-loading of tools into the sandbox.

Phase 3: REPL refactoring
"""

import os
from typing import TYPE_CHECKING, Any

from src.tools.search import search_web
from src.core.llm_query import create_llm_query

if TYPE_CHECKING:
    from src.core.run_context import RunContext
    from src.core.budget import BudgetManager


class EnvironmentSetup:
    """Handles directory and tool setup for REPL execution."""

    @staticmethod
    def setup_directories(
        globals_dict: dict[str, Any],
        run_context: "RunContext | None" = None,
        context_dir: str | None = None,
    ) -> None:
        """Set up input and output directories for code execution.

        Args:
            globals_dict: The globals dictionary to populate
            run_context: Optional run context with artifact tracking
            context_dir: Optional directory for input files
        """
        # Set up output directory (where files are saved)
        if run_context:
            artifacts_dir = run_context.get_working_directory()
            os.makedirs(artifacts_dir, exist_ok=True)
            globals_dict["__artifacts_dir__"] = artifacts_dir
            globals_dict["output_dir"] = artifacts_dir  # Simple alias
            globals_dict["__run_context__"] = run_context

            # Default input_dir to output_dir if no context_dir provided
            if not context_dir:
                globals_dict["__context_dir__"] = artifacts_dir
                globals_dict["input_dir"] = artifacts_dir

        # Set up input directory (where context files are)
        if context_dir:
            globals_dict["__context_dir__"] = context_dir
            globals_dict["input_dir"] = context_dir

    @staticmethod
    def preload_tools(
        globals_dict: dict[str, Any],
        budget_manager: "BudgetManager | None" = None,
        agent_config: Any = None,
        current_depth: int = 0,
        max_depth: int = 5,
    ) -> dict[str, Any]:
        """Pre-load commonly used tools into the sandbox globals.

        Returns a tuple of callables that need to be stored:
        (llm_query_fn, recursive_llm_fn)

        Args:
            globals_dict: The globals dictionary to populate
            budget_manager: Optional budget manager for recursive calls
            agent_config: Optional agent config for recursive calls
            current_depth: Current recursion depth
            max_depth: Maximum recursion depth

        Returns:
            Dictionary with 'llm_query' and 'recursive_llm' functions
        """
        # Make search_web directly available
        globals_dict["search_web"] = search_web

        # Create llm_query for recursive sub-LM calls
        llm_query_fn = create_llm_query(budget_manager=budget_manager)
        globals_dict["llm_query"] = llm_query_fn

        # Create recursive_llm for spawning sub-agents
        recursive_llm_fn = _create_recursive_llm(
            agent_config=agent_config,
            current_depth=current_depth,
            max_depth=max_depth,
            budget_manager=budget_manager,
        )
        globals_dict["recursive_llm"] = recursive_llm_fn

        # Expose execution history placeholder
        globals_dict["__execution_history__"] = []
        globals_dict["history"] = []

        # Context and task placeholders
        globals_dict["context"] = ""
        globals_dict["__task__"] = ""
        globals_dict["task"] = ""

        return {"llm_query": llm_query_fn, "recursive_llm": recursive_llm_fn}


def _create_recursive_llm(
    agent_config: Any = None,
    current_depth: int = 0,
    max_depth: int = 5,
    budget_manager: "BudgetManager | None" = None,
):
    """Create the recursive_llm function for paper-style recursion.

    Args:
        agent_config: Configuration for creating sub-agents
        current_depth: Current recursion depth
        max_depth: Maximum recursion depth
        budget_manager: Budget manager for tracking costs

    Returns:
        Callable function that acts as recursive_llm
    """
    def recursive_llm(sub_query: str, sub_context: str = "") -> str:
        """Spawn a sub-agent to handle a sub-query (paper-style recursion).

        Example:
            result = recursive_llm("Analyze this section", context[0:10000])
            results = [recursive_llm(f"Process: {item}", item) for item in items]

        Args:
            sub_query: The sub-query to process
            sub_context: Context for the sub-query (optional)

        Returns:
            The sub-agent's answer as a string
        """
        # Depth check
        if current_depth >= max_depth:
            return f"[Max recursion depth ({max_depth}) reached. Cannot delegate further.]"

        # If no agent config, return placeholder
        if not agent_config:
            return "[Delegation not configured. Set agent_config to enable recursive_llm.]"

        # Import here to avoid circular imports
        try:
            from src.core.agent import RLMAgent

            # Create sub-agent with increased depth
            sub_agent = RLMAgent(
                config=agent_config,
                budget_manager=budget_manager,
                max_depth=max_depth,
                root_dir=None,
            )

            # Run sub-query
            answer = sub_agent.run(sub_query + "\n\nContext:\n" + sub_context)
            return answer

        except Exception as e:
            return f"[Delegation failed: {str(e)}]"

    return recursive_llm
