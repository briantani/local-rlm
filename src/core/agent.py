import concurrent.futures
import threading
from pathlib import Path
from typing import Protocol, runtime_checkable

from src.core.logger import logger
from src.core.repl import PythonREPL
from src.core.budget import BudgetManager
from src.core.config_loader import ProfileConfig
from src.modules.architect import Architect
from src.modules.coder import Coder
from src.modules.responder import Responder
from src.modules.delegator import Delegator
from src.core.explorer import scan_directory


# Protocol definitions for dependency injection
@runtime_checkable
class CodeExecutor(Protocol):
    """Protocol for code execution backends."""
    def execute(self, code: str) -> str: ...


@runtime_checkable
class TaskRouter(Protocol):
    """Protocol for task routing/decision making."""
    def __call__(self, query: str, data_desc: str) -> object: ...


@runtime_checkable
class CodeGenerator(Protocol):
    """Protocol for code generation modules."""
    def __call__(self, task: str, context_summary: str) -> object: ...


class RLMAgent:
    """
    The main Recursive Language Model Agent.
    Orchestrates the Architect, Coder, and REPL to solve tasks.
    Supports recursive delegation handling.

    Supports dependency injection for all components to enable testing.
    Supports YAML-based configuration profiles via ProfileConfig.
    """
    def __init__(
        self,
        max_steps: int = 10,
        max_depth: int = 3,
        depth: int = 0,
        root_dir: str | Path | None = None,
        # Configuration profile (Phase 11)
        config: ProfileConfig | None = None,
        is_delegate: bool = False,
        budget_manager: BudgetManager | None = None,
        # Dependency injection parameters
        repl: CodeExecutor | None = None,
        architect: TaskRouter | None = None,
        coder: CodeGenerator | None = None,
        responder: object | None = None,
        delegator: object | None = None,
    ):
        self.config = config
        self.is_delegate = is_delegate
        self.budget_manager = budget_manager

        # Use config settings if provided, otherwise use parameters
        if config:
            agent_config = config.delegate if is_delegate else config.root
            self.max_steps = agent_config.max_steps
            self.max_depth = agent_config.max_depth
        else:
            self.max_steps = max_steps
            self.max_depth = max_depth

        self.depth = depth
        self.root_dir = Path(root_dir) if root_dir else None

        # Use injected dependencies or create defaults
        self.repl = repl if repl else PythonREPL()
        self.architect = architect if architect else Architect()
        self.coder = coder if coder else Coder()
        self.responder = responder if responder else Responder()
        self.delegator = delegator if delegator else Delegator()

        # Thread-safe history tracking (Python 3.14t compatibility)
        self._history_lock = threading.Lock()
        self.history: list[tuple[str, str]] = []  # List of (Action/Code, Output)

        # Initialize context with file listing if root_dir is provided
        if self.root_dir and self.root_dir.exists():
            file_structure = scan_directory(self.root_dir)
            initial_context = (
                f"AVAILABLE FILES (Use Python code to read them):\n{file_structure}\n"
                f"NOTE: To access file content, you MUST generate Python code using open(), pd.read_csv(), etc."
            )
            self._add_history("System Initialization", initial_context)

    def _add_history(self, action: str, output: str) -> None:
        """Thread-safe history append for Python 3.14t compatibility."""
        with self._history_lock:
            self.history.append((action, output))

    def format_context(self) -> str:
        """Formats the execution history into a string context."""
        with self._history_lock:
            if not self.history:
                return ""

            context_str = "Execution History:\n"
        for i, (action_or_code, output) in enumerate(self.history, 1):
            context_str += f"--- Step {i} ---\n"
            context_str += f"Input: {action_or_code}\n"
            context_str += f"Output: {output}\n"
        return context_str

    def run(self, task: str) -> str:
        """
        Executes the main loop to solve the task.
        """
        indent = "  " * self.depth
        logger.info(f"{indent}Agent (Depth {self.depth}) received task: {task}")

        for step in range(self.max_steps):
            logger.info(f"{indent}--- Step {step + 1} ---")
            context = self.format_context()

            # 1. Architect decides what to do
            logger.debug(f"{indent}Thinking...")
            try:
                # We interpret 'data_desc' as the current context/state
                decision = self.architect(query=task, data_desc=context)
                action = decision.action.upper()
                logger.info(f"{indent}Architect Decision: {action}")
            except Exception as e:
                logger.error(f"{indent}Architect error: {e}")
                action = "ANSWER"

            # 2. Execute Action
            if action == "ANSWER":
                response = self.responder(query=task, context=context)
                final_answer = response.response
                logger.info(f"{indent}Final Answer: {final_answer}")
                return final_answer

            elif action == "CODE":
                logger.info(f"{indent}Generating code...")
                try:
                    code_pred = self.coder(task=task, context_summary=context)
                    code = code_pred.python_code
                    logger.debug(f"{indent}Code Generated:\n{code}")

                    logger.info(f"{indent}Executing code...")
                    output = self.repl.execute(code)
                    log_msg = f"{indent}Execution Output (truncated): {output[:100]}..." if len(output) > 100 else f"{indent}Execution Output: {output}"
                    logger.info(log_msg)

                    self._add_history(f"Executed Code:\n{code}", output)

                except Exception as e:
                    error_msg = f"Error during coding/execution: {e}"
                    logger.error(f"{indent}{error_msg}")
                    self._add_history("Attempted Code Generation", error_msg)

            elif action == "DELEGATE":
                if self.depth >= self.max_depth:
                    logger.warning(f"{indent}Max depth reached. Cannot delegate further. Returning to Answer mode.")
                    # Force answer in next step or use responder now?
                    # Let's add instruction to history to guide Architect
                    self._add_history("Action: DELEGATE", "FAILED: Max recursion saturation reached. You must solve this yourself using CODE or ANSWER.")
                    continue

                logger.info(f"{indent}Delegating task...")
                try:
                    # 1. Break down task
                    subtasks = self.delegator(task=task, context=context)
                    logger.info(f"{indent}Subtasks identified: {subtasks}")

                    if not subtasks:
                        logger.warning(f"{indent}No subtasks found. Aborting delegation.")
                        self._add_history("Action: DELEGATE", "FAILED: Could not split task.")
                        continue

                    # 2. Execute in parallel
                    results = []
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # Create sub-agents
                        futures = {}
                        for i, subtask in enumerate(subtasks):
                            # Instantiate new agent for each subtask
                            # Pass config and mark as delegate
                            sub_agent = RLMAgent(
                                max_steps=self.max_steps,
                                max_depth=self.max_depth,
                                depth=self.depth + 1,
                                config=self.config,
                                is_delegate=True,
                                budget_manager=self.budget_manager,
                            )
                            futures[executor.submit(sub_agent.run, subtask)] = subtask

                        for future in concurrent.futures.as_completed(futures):
                            original_subtask = futures[future]
                            try:
                                res = future.result()
                                results.append(f"Subtask '{original_subtask}': {res}")
                            except Exception as exc:
                                results.append(f"Subtask '{original_subtask}' generated an exception: {exc}")

                    # 3. Aggregate results into history
                    combined_results = "\n".join(results)
                    logger.info(f"{indent}Delegation Complete. Results:\n{combined_results}")
                    self._add_history(f"Delegated Subtasks: {subtasks}", f"Results from sub-agents:\n{combined_results}")

                except Exception as e:
                    logger.error(f"{indent}Delegation error: {e}")
                    self._add_history("Action: DELEGATE", f"Error: {e}")

            else:
                logger.warning(f"{indent}Unknown action: {action}")
                return f"Agent confused: Unknown action {action}"

        return "Max steps reached without definitive answer."
