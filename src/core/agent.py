import concurrent.futures
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import dspy

from src.config import get_lm_for_role
from src.core.logger import logger
from src.core.repl import PythonREPL
from src.core.budget import BudgetManager
from src.core.config_loader import ProfileConfig
from src.core.context_summarizer import ContextSummarizer
from src.core.parser import is_final, parse_response  # Paper-style FINAL()
from src.modules.architect import Architect
from src.modules.coder import Coder
from src.modules.responder import Responder
from src.modules.delegator import Delegator
from src.core.explorer import scan_directory

if TYPE_CHECKING:
    from src.core.run_context import RunContext


# Protocol definitions for dependency injection
@runtime_checkable
class CodeExecutor(Protocol):
    """Protocol for code execution backends."""
    def execute(self, code: str) -> str: ...
    def check_for_final(self, output: str) -> str | None: ...


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
        # Run context for artifact management
        run_context: "RunContext | None" = None,
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
        self.run_context = run_context

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
        # Pass run_context so files are saved to artifacts folder
        # Pass root_dir as context_dir so code can access input files
        # Pass budget_manager for llm_query cost tracking
        self.repl = repl if repl else PythonREPL(
            run_context=run_context,
            context_dir=str(self.root_dir.absolute()) if self.root_dir else None,
            budget_manager=budget_manager,
        )
        self.architect = architect if architect else Architect()
        self.coder = coder if coder else Coder()
        self.responder = responder if responder else Responder(run_context=run_context)
        self.delegator = delegator if delegator else Delegator()

        # Context summarizer for RAG-like handling of large contexts
        self.context_summarizer = ContextSummarizer(run_context=run_context)

        # Thread-safe history tracking (Python 3.14t compatibility)
        self._history_lock = threading.Lock()
        self.history: list[tuple[str, str]] = []  # List of (Action/Code, Output)

        # Build initialization context
        init_parts = []

        # Add artifacts directory info if available
        if run_context:
            init_parts.append(
                f"OUTPUT DIRECTORY: {run_context.artifacts_dir}\n"
                "Use __artifacts_dir__ in code to save files (images, reports, data)."
            )

        # Add input files context if root_dir is provided
        if self.root_dir and self.root_dir.exists():
            file_structure = scan_directory(self.root_dir)
            init_parts.append(
                f"INPUT FILES (in {self.root_dir}):\n{file_structure}\n"
                "Use __context_dir__ in code to access these files.\n"
                "Example: open(f'{__context_dir__}/data.csv') or pd.read_csv(f'{__context_dir__}/data.csv')"
            )

        if init_parts:
            self._add_history("System Initialization", "\n\n".join(init_parts))

    def _add_history(self, action: str, output: str) -> None:
        """Thread-safe history append for Python 3.14t compatibility."""
        with self._history_lock:
            self.history.append((action, output))

    def _generate_fallback_answer(self, task: str) -> str:
        """Generate a fallback answer when Responder returns None.

        This happens when context is too long or model fails to produce output.
        Uses execution history to summarize what was accomplished.

        Args:
            task: The original task query

        Returns:
            A summary of what was accomplished based on execution history
        """
        with self._history_lock:
            if not self.history:
                return "Task completed but no summary available."

            # Count artifacts if available
            artifact_info = ""
            if self.run_context:
                images = self.run_context.list_images()
                if images:
                    artifact_info = f"\n\nGenerated {len(images)} visualization(s):\n"
                    for img in images:
                        artifact_info += f"- {img['filename']}\n"

            # Count code executions
            code_count = sum(1 for action, _ in self.history if "Code" in action or "Executed" in action)

            # Get last few outputs (last 3 meaningful ones)
            recent_outputs = []
            for action, output in reversed(self.history[-5:]):
                if output and output.strip() and len(output) < 500:
                    recent_outputs.append(output.strip())
                if len(recent_outputs) >= 2:
                    break

            summary = f"Task completed after {len(self.history)} steps with {code_count} code executions."
            if artifact_info:
                summary += artifact_info
            if recent_outputs:
                summary += "\n\nRecent outputs:\n" + "\n".join(recent_outputs[:2])

            return summary

    def _summarize_with_rag(self, task: str, context: str, indent: str) -> str:
        """Use RAG-like chunked summarization for large contexts.

        This method:
        1. Saves the full context to artifacts (preserves research)
        2. Splits context into chunks
        3. Summarizes each chunk independently
        4. Synthesizes into final response

        Args:
            task: The original task query
            context: The full execution history (potentially very large)
            indent: Log indentation for depth tracking

        Returns:
            Synthesized response from chunked summaries
        """
        # Build artifacts info for the summarizer
        artifacts_info = ""
        if self.run_context:
            images = self.run_context.list_images()
            if images:
                artifacts_info = "Generated visualizations:\n"
                for img in images:
                    artifacts_info += f"- {img['filename']}: {img.get('description', 'Image')}\n"

        try:
            logger.info(f"{indent}Running RAG-like summarization on {len(context)} chars...")
            result = self.context_summarizer(
                query=task,
                context=context,
                artifacts_info=artifacts_info
            )

            response = result.response
            if response:
                # Enhance with artifact images if responder has run_context
                if self.run_context:
                    response = self.responder._enhance_with_artifacts(response)
                return response
            else:
                logger.warning(f"{indent}RAG summarization returned None. Using basic fallback.")
                return self._generate_fallback_answer(task)

        except Exception as e:
            logger.error(f"{indent}RAG summarization failed: {e}")
            return self._generate_fallback_answer(task)

    def format_context(self) -> str:
        """Formats the execution history into a string context.

        DEPRECATED: This returns full context. For paper-style metadata-only
        approach, use format_context_metadata() instead.
        """
        with self._history_lock:
            if not self.history:
                return ""

            context_str = "Execution History:\n"
        for i, (action_or_code, output) in enumerate(self.history, 1):
            context_str += f"--- Step {i} ---\n"
            context_str += f"Input: {action_or_code}\n"
            context_str += f"Output: {output}\n"
        return context_str

    def format_context_metadata(self) -> str:
        """Get metadata about execution history (paper-style approach).

        Paper insight: "Long prompts should not be fed into the neural network
        directly but should instead be treated as part of the environment."

        Returns metadata like step count and char totals, NOT full content.
        The LLM accesses full content via __execution_history__ in code.
        """
        # Use REPL's metadata method if available
        if hasattr(self.repl, 'get_history_metadata'):
            return self.repl.get_history_metadata()

        # Fallback for mocked REPLs in tests
        with self._history_lock:
            if not self.history:
                return "Execution History: 0 steps. No code executed yet."

            total_chars = sum(len(a) + len(o) for a, o in self.history)
            return f"Execution History: {len(self.history)} steps, {total_chars} chars total."

    def get_last_output_preview(self) -> str:
        """Get a preview of the last output for decision making."""
        if hasattr(self.repl, 'get_last_output_preview'):
            return self.repl.get_last_output_preview(max_chars=500)

        # Fallback for mocked REPLs
        with self._history_lock:
            if not self.history:
                return ""
            _, last_output = self.history[-1]
            if len(last_output) <= 500:
                return f"Last output:\n{last_output}"
            return f"Last output ({len(last_output)} chars, truncated):\n{last_output[:500]}..."

    def run(self, task: str) -> str:
        """
        Executes the main loop to solve the task.
        """
        indent = "  " * self.depth
        logger.info(f"{indent}Agent (Depth {self.depth}) received task: {task}")

        # For delegates running in ThreadPoolExecutor threads, we need to use
        # dspy.context() as a context manager which provides thread-local settings.
        # dspy.configure() is restricted to the thread that initially set it up.
        if self.is_delegate and self.config:
            role = "delegate"
            lm = get_lm_for_role(role, self.config, budget_manager=self.budget_manager)
            logger.debug(f"{indent}Configured delegate LM: {self.config.delegate.model}")
            # Use context manager for thread-local LM settings
            with dspy.context(lm=lm):
                return self._run_loop(task, indent)
        else:
            return self._run_loop(task, indent)

    def _run_loop(self, task: str, indent: str) -> str:
        """Internal run loop, separated to support dspy.context() wrapper."""
        # Set the task in REPL so code can access it via __task__
        self.repl.set_task(task)

        for step in range(self.max_steps):
            logger.info(f"{indent}--- Step {step + 1} ---")

            # Paper-style: Pass METADATA to Architect, not full context
            # The LLM can access full history via __execution_history__ in code
            context_metadata = self.format_context_metadata()
            last_output = self.get_last_output_preview()

            # Combine metadata with last output preview for decision making
            architect_context = context_metadata
            if last_output:
                architect_context += f"\n\n{last_output}"

            # 1. Architect decides what to do
            logger.debug(f"{indent}Thinking...")
            try:
                # Pass metadata, not full context (paper-style)
                decision = self.architect(query=task, data_desc=architect_context)
                action = decision.action.upper()
                logger.info(f"{indent}Architect Decision: {action}")
            except Exception as e:
                logger.error(f"{indent}Architect error: {e}")
                action = "ANSWER"

            # 2. Execute Action
            if action == "ANSWER":
                # For Responder, we need to build context from REPL history
                # But use chunked summarization if it's too large
                full_context = self.format_context()

                if self.context_summarizer.should_chunk(full_context):
                    logger.info(f"{indent}Context too large ({len(full_context)} chars). Using RAG-like summarization.")
                    final_answer = self._summarize_with_rag(task, full_context, indent)
                else:
                    response = self.responder(query=task, context=full_context)
                    final_answer = response.response

                    # Handle None response (can happen with context overflow or model issues)
                    if final_answer is None:
                        logger.warning(f"{indent}Responder returned None. Using RAG-like summarization.")
                        final_answer = self._summarize_with_rag(task, full_context, indent)

                logger.info(f"{indent}Final Answer: {final_answer[:200]}..." if len(str(final_answer)) > 200 else f"{indent}Final Answer: {final_answer}")
                return final_answer

            elif action == "CODE":
                logger.info(f"{indent}Generating code...")
                try:
                    # For Coder, pass metadata + hints about available data
                    # The Coder should use __execution_history__ for full content
                    coder_context = context_metadata
                    if last_output:
                        coder_context += f"\n\n{last_output}"

                    code_pred = self.coder(task=task, context_summary=coder_context)
                    code = code_pred.python_code
                    logger.debug(f"{indent}Code Generated:\n{code}")

                    logger.info(f"{indent}Executing code...")
                    output = self.repl.execute(code)
                    log_msg = f"{indent}Execution Output (truncated): {output[:100]}..." if len(output) > 100 else f"{indent}Execution Output: {output}"
                    logger.info(log_msg)

                    # Check for paper-style FINAL() termination
                    if hasattr(self.repl, 'check_for_final'):
                        final_answer = self.repl.check_for_final(output)
                        if final_answer is not None:
                            logger.info(f"{indent}FINAL() detected in output. Returning immediately.")
                            return final_answer
                    elif is_final(output):
                        # Fallback for mocked REPLs
                        final_answer = parse_response(output, {})
                        if final_answer is not None:
                            logger.info(f"{indent}FINAL() detected in output. Returning immediately.")
                            return final_answer

                    # Add to both internal history and REPL-accessible history
                    self._add_history(f"Executed Code:\n{code}", output)
                    self.repl.add_history_entry(code, output, step + 1)

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
                    subtasks = self.delegator(task=task, context=context_metadata)
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
                            # Pass config, run_context, and mark as delegate
                            # Share root_dir so delegates have input_dir defined
                            sub_agent = RLMAgent(
                                max_steps=self.max_steps,
                                max_depth=self.max_depth,
                                depth=self.depth + 1,
                                config=self.config,
                                is_delegate=True,
                                budget_manager=self.budget_manager,
                                run_context=self.run_context,  # Share artifact folder
                                root_dir=self.root_dir,  # Share input directory
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
