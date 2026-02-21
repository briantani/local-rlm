from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import TYPE_CHECKING

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
from src.core.explorer import scan_directory

# Import extracted modules
from src.core.agent_protocols import CodeExecutor, TaskRouter, CodeGenerator, VisualizationCritic
from src.core.agent_context import AgentContext
from src.core.agent_artifacts import AgentArtifacts
from src.core.agent_fallbacks import AgentFallbacks

if TYPE_CHECKING:
    from src.core.run_context import RunContext


class RLMAgent:
    """
    The main Recursive Language Model Agent.
    Orchestrates the Architect, Coder, and REPL to solve tasks.

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
        # Root LM to use within worker threads (thread-local contexts)
        root_lm: dspy.LM | None = None,
        # Dependency injection parameters
        repl: CodeExecutor | None = None,
        architect: TaskRouter | None = None,
        coder: CodeGenerator | None = None,
        responder: object | None = None,
        critic: VisualizationCritic | None = None,  # Optional vision-capable critic
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
        # Pass config and depth for recursive_llm sub-agent spawning
        self.repl = repl if repl else PythonREPL(
            run_context=run_context,
            context_dir=str(self.root_dir.absolute()) if self.root_dir else None,
            budget_manager=budget_manager,
            agent_config=config,
            current_depth=depth,
            max_depth=self.max_depth,
        )
        self.architect = architect if architect else Architect()
        self.coder = coder if coder else Coder()
        self.responder = responder if responder else Responder(run_context=run_context)
        self.critic = critic  # Optional - may be None

        # LM to be injected into worker threads via dspy.context
        self._thread_lm = root_lm

        # Context summarizer for RAG-like handling of large contexts
        self.context_summarizer = ContextSummarizer(run_context=run_context)

        # Extracted modules for better organization
        self._context = AgentContext()
        self._artifacts = AgentArtifacts(run_context=run_context)
        self._fallbacks = AgentFallbacks(
            run_context=run_context,
            context_summarizer=self.context_summarizer,
            responder=self.responder,
        )

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
            self._context.add_history("System Initialization", "\n\n".join(init_parts))

    def _add_history(self, action: str, output: str) -> None:
        """Thread-safe history append for Python 3.14t compatibility."""
        self._context.add_history(action, output)

    def _call_in_context(self, fn, *args, _lm_override=None, **kwargs):
        """Call a function inside a thread-local dspy context.

        Uses _lm_override if provided (for delegates), otherwise uses root LM.
        Ensures worker threads created by ThreadPoolExecutor have the same
        LM configuration as the main thread.

        Args:
            fn: Function to call
            *args: Positional arguments for fn
            _lm_override: Override LM to use (for delegates)
            **kwargs: Keyword arguments for fn
        """
        lm = _lm_override if _lm_override is not None else self._thread_lm
        if lm is not None:
            with dspy.context(lm=lm):
                return fn(*args, **kwargs)
        return fn(*args, **kwargs)

    def get_artifacts(self) -> list[dict]:
        """Return the list of tracked artifacts for this run."""
        return self._artifacts.get_artifacts()

    def _scan_and_register_artifacts(self) -> None:
        """Scan the run's artifacts directory and register any new files."""
        self._artifacts.scan_and_register()

    def _generate_fallback_answer(self, task: str) -> str:
        """Generate a fallback answer when Responder returns None."""
        history = self._context.get_history_copy()
        return self._fallbacks.generate_fallback_answer(task, history)

    def _summarize_with_rag(self, task: str, context: str, indent: str) -> str:
        """Use RAG-like chunked summarization for large contexts."""
        result = self._fallbacks.summarize_with_rag(task, context, indent)
        if not result:
            # If RAG returns empty, use fallback
            history = self._context.get_history_copy()
            return self._fallbacks.generate_fallback_answer(task, history)
        return result

    def _check_expected_artifacts(self, expected: list[str]) -> list[str]:
        """Return list of expected filenames that are missing from run_context.artifacts."""
        return self._artifacts.check_expected_artifacts(expected)

    def format_context(self) -> str:
        """Formats the execution history into a string context.

        DEPRECATED: This returns full context. For paper-style metadata-only
        approach, use format_context_metadata() instead.
        """
        return self._context.format_context()

    def format_context_metadata(self) -> str:
        """Get metadata about execution history (paper-style approach).

        Paper insight: "Long prompts should not be fed into the neural network
        directly but should instead be treated as part of the environment."

        Returns metadata like step count and char totals, NOT full content.
        The LLM accesses full content via __execution_history__ in code.
        """
        return self._context.format_context_metadata(self.repl)

    def get_last_output_preview(self, max_chars: int = 500) -> str:
        """Get a preview of the last output for decision making."""
        return self._context.get_last_output_preview(self.repl, max_chars=max_chars)

    @property
    def history(self) -> list[tuple[str, str]]:
        """Get the execution history of this agent.

        Returns:
            List of (action, output) tuples
        """
        return self._context.history

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
            # Use _call_in_context to wrap delegate execution with proper LM context
            return self._call_in_context(self._run_loop, task, indent, _lm_override=lm)
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

            # Build artifacts_info summary for modules that accept artifact context
            artifacts_info = ""
            if self.run_context and getattr(self.run_context, 'artifacts', None):
                parts = []
                for a in self.run_context.artifacts:
                    fname = a.get('filename', '')
                    section = a.get('section') or ''
                    desc = a.get('description') or ''
                    parts.append(f"{fname} | {a.get('type','')} | {section} | {desc}")
                artifacts_info = "\n".join(parts)

            # 1. Architect decides what to do
            logger.debug(f"{indent}Thinking...")
            try:
                # Call architect with a short timeout to avoid hangs if LM is unresponsive
                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(
                        self._call_in_context,
                        self.architect,
                        query=task,
                        data_desc=architect_context,
                        artifacts_info=artifacts_info,
                    )
                    try:
                        # Increased timeout for local models
                        decision = future.result(timeout=120)
                        action = decision.action.upper()
                        logger.info(f"{indent}Architect Decision: {action}")
                    except FuturesTimeoutError:
                        future.cancel()
                        raise TimeoutError("Architect call timed out")
            except Exception as e:
                logger.error(f"{indent}Architect error: {e}")
                action = "ANSWER"

            # 2. Execute Action
            if action == "ANSWER":
                # For Responder, pass the last output as findings (concrete data for the report).
                # Don't pass full context to avoid redundant narration of the process.
                findings = self.get_last_output_preview(max_chars=2000)

                try:
                    with ThreadPoolExecutor(max_workers=1) as ex:
                        future = ex.submit(
                            self._call_in_context,
                            self.responder,
                            query=task,
                            findings=findings,
                            artifacts_info=artifacts_info,
                        )
                        try:
                            # Increased timeout for local models
                            response = future.result(timeout=120)
                            final_answer = response.response
                        except FuturesTimeoutError:
                            future.cancel()
                            raise TimeoutError("Responder call timed out")
                except TimeoutError:
                    logger.error(f"{indent}Responder call timed out")
                    final_answer = self._generate_fallback_answer(task)
                except Exception as e:
                    logger.error(f"{indent}Responder error: {e}")
                    final_answer = self._generate_fallback_answer(task)

                # Handle None response (can happen with model issues)
                if final_answer is None:
                    logger.warning(f"{indent}Responder returned None. Using fallback.")
                    final_answer = self._generate_fallback_answer(task)

                logger.info(f"{indent}Final Answer: {final_answer[:200]}..." if len(str(final_answer)) > 200 else f"{indent}Final Answer: {final_answer}")

                # Add final answer to report and perform final assembly to ensure
                # all artifacts are referenced and summarized.
                if self.run_context:
                    try:
                        self.run_context.add_to_report(str(final_answer))
                        assembly = self.run_context.finalize_report()
                        if assembly.get("added"):
                            logger.warning(f"{indent}Final assembly added missing artifacts: {assembly.get('added')}")
                        # Save finalized report
                        report_path = self.run_context.save_report()
                        logger.info(f"{indent}Saved final report to {report_path}")
                    except Exception as e:
                        logger.exception(f"{indent}Final assembly failed: {e}")

                return final_answer

            elif action == "CODE":
                logger.info(f"{indent}Generating code...")
                try:
                    # For Coder, pass metadata + hints about available data
                    # The Coder should use __execution_history__ for full content
                    coder_context = context_metadata
                    if last_output:
                        coder_context += f"\n\n{last_output}"

                    # Run coder with timeout guard to prevent long LLM hangs
                    try:
                        with ThreadPoolExecutor(max_workers=1) as ex:
                            future = ex.submit(
                                self._call_in_context,
                                self.coder,
                                task=task,
                                context_summary=coder_context,
                            )
                            # 600s (10 min) timeout for code generation—accounts for slow local models,
                            # large context processing, and complex task reasoning
                            code_pred = future.result(timeout=600)
                    except FuturesTimeoutError:
                        future.cancel()
                        raise TimeoutError("Coder call timed out")
                    code = code_pred.python_code
                    logger.debug(f"{indent}Code Generated:\n{code}")

                    logger.info(f"{indent}Executing code...")
                    output = self.repl.execute(code)
                    log_msg = f"{indent}Execution Output (truncated): {output[:100]}..." if len(output) > 100 else f"{indent}Execution Output: {output}"
                    logger.info(log_msg)

                    # NEW: Critic refinement loop for visualizations
                    if self._should_refine_visualization(output, code):
                        logger.info(f"{indent}Visualization detected. Running critic refinement...")
                        code, output = self._refine_visualization_loop(
                            task=task,
                            initial_code=code,
                            initial_output=output,
                            base_context=coder_context,
                            indent=indent
                        )
                        # Update history with final refined version
                        self._add_history(f"Refined Code (final):\n{code}", output)
                        self.repl.add_history_entry(code, output, step + 1)

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

                    # After executing code, scan the artifacts directory and register new files
                    try:
                        self._scan_and_register_artifacts()
                    except Exception:
                        logger.exception("Artifact scanning failed after code execution")

                    # If coder declared expected artifacts, validate and retry if missing
                    expected = []
                    if hasattr(code_pred, "expected_artifacts") and code_pred.expected_artifacts:
                        expected = list(code_pred.expected_artifacts)

                    if expected:
                        missing = self._check_expected_artifacts(expected)
                        retries = 0
                        max_retries = getattr(code_pred, "max_retries", 2)
                        while missing and retries < max_retries:
                            retries += 1
                            logger.warning(f"{indent}Missing artifacts after execution: {missing}. Retry {retries}/{max_retries}.")
                            # Ask coder to regenerate or correct; re-run coder to get new code
                            try:
                                code_pred = self.coder(task=task, context_summary=coder_context)
                                code = code_pred.python_code
                                logger.debug(f"{indent}Retry Code Generated:\n{code}")
                                output = self.repl.execute(code)
                                self._add_history(f"Executed Code (retry {retries}):\n{code}", output)
                                self.repl.add_history_entry(code, output, step + 1 + retries)
                                self._scan_and_register_artifacts()
                                missing = self._check_expected_artifacts(expected)
                            except Exception as e:
                                logger.error(f"{indent}Retry failed: {e}")
                                break

                        if missing:
                            logger.error(f"{indent}Artifacts still missing after {retries} retries: {missing}")
                            # Optionally, add to history for debugging
                            self._add_history("Missing Artifacts", ", ".join(missing))
                    # After executing code, scan the artifacts directory and register new files
                    try:
                        self._scan_and_register_artifacts()
                    except Exception:
                        logger.exception("Artifact scanning failed after code execution")

                except Exception as e:
                    error_msg = f"Error during coding/execution: {e}"
                    logger.error(f"{indent}{error_msg}")
                    self._add_history("Attempted Code Generation", error_msg)

            else:
                logger.warning(f"{indent}Unknown action: {action}")
                return f"Agent confused: Unknown action {action}"

        return "Max steps reached without definitive answer."

    def _should_refine_visualization(self, output: str, code: str) -> bool:
        """Check if code execution created a visualization that needs refinement.

        Triggers refinement if BOTH:
        1. Code contains visualization keywords (plt.savefig, seaborn, etc.)
        2. Image artifacts were actually created

        This catches both successful plots and failed attempts.
        """
        if not self.critic:
            return False

        # Check if code contains visualization keywords
        viz_keywords = ["plt.savefig", "plt.show", "seaborn", "sns.", ".plot(", "plt.figure"]
        has_viz_code = any(kw in code for kw in viz_keywords)

        # Check if artifacts were created
        if self.run_context:
            images = self.run_context.list_images()
            has_viz_artifact = len(images) > 0
        else:
            has_viz_artifact = False

        return has_viz_code and has_viz_artifact

    def _get_latest_visualization(self) -> Path | None:
        """Get path to most recently created visualization.

        Returns:
            Path to the latest image artifact, or None if no images exist
        """
        if not self.run_context:
            return None

        images = self.run_context.list_images()
        if not images:
            return None

        # Return most recent (last in list)
        latest = images[-1]
        return self.run_context.artifacts_dir / latest["filename"]

    def _refine_visualization_loop(
        self,
        task: str,
        initial_code: str,
        initial_output: str,
        base_context: str,
        indent: str
    ) -> tuple[str, str]:
        """Run up to 3 rounds of refinement with critic feedback.

        Uses cumulative feedback where each round builds on previous critiques.
        Follows Paperbanana's three-round refinement pattern.

        Args:
            task: Original user task
            initial_code: Initial code that generated the visualization
            initial_output: Initial execution output
            base_context: Base context for coder (metadata + last output)
            indent: Logging indentation string

        Returns:
            Tuple of (final_code, final_output)
        """
        MAX_ROUNDS = 3
        code = initial_code
        output = initial_output
        cumulative_feedback = ""

        for round_num in range(1, MAX_ROUNDS + 1):
            # Find latest image artifact
            image_path = self._get_latest_visualization()
            if not image_path:
                logger.warning(f"{indent}No visualization found for critic validation")
                break

            # Run critic
            try:
                critique = self.critic(
                    task=task,
                    code=code,
                    image_path=str(image_path),
                    execution_output=output,
                    previous_feedback=cumulative_feedback
                )
            except Exception as e:
                logger.error(f"{indent}Critic failed: {e}")
                break

            if critique.is_valid:
                logger.info(f"{indent}✓ Visualization validated on round {round_num}")
                logger.info(f"{indent}  Confidence: {critique.confidence:.2f}")
                if critique.feedback:
                    logger.info(f"{indent}  Final feedback: {critique.feedback[:200]}")
                break

            # Accumulate feedback
            cumulative_feedback += f"\n\n=== Round {round_num} Critique ===\n{critique.feedback}"
            logger.info(f"{indent}↻ Refining visualization (round {round_num}/{MAX_ROUNDS})")
            logger.info(f"{indent}  Critique: {critique.feedback[:300]}{'...' if len(critique.feedback) > 300 else ''}")
            logger.info(f"{indent}  Confidence: {critique.confidence:.2f}")

            # Don't refine on the last round - accept what we have
            if round_num >= MAX_ROUNDS:
                logger.info(f"{indent}✓ Refinement complete ({MAX_ROUNDS} rounds)")
                break

            # Regenerate with enhanced context
            enhanced_context = f"{base_context}\n\n🎨 VISUALIZATION CRITIQUE:{cumulative_feedback}"

            try:
                code_pred = self.coder(task=task, context_summary=enhanced_context)
                code = code_pred.python_code
                logger.debug(f"{indent}Refined Code (round {round_num}):\n{code}")
                output = self.repl.execute(code)
                self._add_history(f"Refined Code (round {round_num}):\n{code}", output)
                self.repl.add_history_entry(code, output, f"refine_{round_num}")

                # Scan for new artifacts after refinement
                self._scan_and_register_artifacts()
            except Exception as e:
                logger.error(f"{indent}Refinement failed: {e}")
                break

        return code, output
