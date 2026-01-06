"""
Task Service for RLM.

Orchestrates agent execution, providing a clean interface for running tasks
that can be shared between CLI and Web interfaces.

Phase 12: Core Library Refactoring
"""

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

import dspy

from src.config import get_lm_for_role
from src.core.agent import RLMAgent
from src.core.budget import BudgetManager
from src.core.config_loader import ProfileConfig
from src.core.repl import PythonREPL
from src.rlm.services.config_service import ConfigService
from src.rlm.services.session_service import Session


logger = logging.getLogger(__name__)


@dataclass
class StepInfo:
    """Information about a single execution step."""
    step_number: int
    action: str  # "CODE", "ANSWER", "DELEGATE"
    input_text: str
    output_text: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResult:
    """
    Result of a task execution.

    Contains the final answer, execution history, and cost information.
    """
    answer: str
    execution_history: list[StepInfo]
    total_cost: float
    model_breakdown: dict[str, float]
    started_at: datetime
    completed_at: datetime
    config_name: str
    task_text: str

    @property
    def duration_seconds(self) -> float:
        """Get the duration of the task in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def step_count(self) -> int:
        """Get the number of execution steps."""
        return len(self.execution_history)


# Type alias for step callbacks
StepCallback = Callable[[StepInfo], None]


class TaskService:
    """
    Orchestrates agent execution.

    Provides a clean interface for running tasks that can be shared
    between CLI and Web interfaces. Handles:
    - Configuration loading with runtime API keys
    - Budget management
    - Agent creation and execution
    - Step-by-step progress callbacks
    - REPL state persistence for follow-up queries
    """

    # Class-level REPL storage (in-memory, per task_id)
    _repl_storage: dict[str, PythonREPL] = {}
    _storage_lock = threading.Lock()

    def __init__(
        self,
        config_service: ConfigService,
        session: Session | None = None,
    ):
        """
        Initialize the task service.

        Args:
            config_service: Service for loading configuration profiles
            session: Optional session with API keys (if None, uses env vars)
        """
        self.config_service = config_service
        self.session = session

    def run_task(
        self,
        task: str,
        config_name: str,
        context_path: Path | None = None,
        on_step: StepCallback | None = None,
        task_id: str | None = None,
    ) -> TaskResult:
        """
        Execute a task with the RLM agent.

        Args:
            task: The task/query to execute
            config_name: Name of config profile (e.g., "cost-effective")
            context_path: Optional directory for file context
            on_step: Callback for streaming progress updates
            task_id: Optional task ID for REPL state persistence

        Returns:
            TaskResult with answer, history, and cost breakdown

        Raises:
            FileNotFoundError: If config profile doesn't exist
            ValueError: If required API keys are missing
        """
        started_at = datetime.now()

        # Get API keys from session or environment
        api_keys = self._get_api_keys()

        # Load config with API keys
        config = self._load_config_with_keys(config_name, api_keys)

        # Validate required API keys
        self._validate_api_keys(config, api_keys)

        # Set up API keys in environment for DSPy
        self._configure_environment(api_keys)

        # Initialize budget manager
        BudgetManager._clear()  # Clear singleton for fresh start
        budget_manager = BudgetManager(max_budget=config.budget.max_usd)

        # Configure DSPy with root LM
        lm = get_lm_for_role("root", config, budget_manager=budget_manager)
        dspy.settings.configure(lm=lm)

        logger.info(f"Running task with config: {config_name}")
        logger.info(f"Root model: {config.root.provider}/{config.root.model}")
        logger.info(f"Budget limit: ${config.budget.max_usd:.2f}")

        # Create agent
        agent = RLMAgent(
            max_steps=config.root.max_steps,
            max_depth=config.root.max_depth,
            root_dir=context_path,
            config=config,
            budget_manager=budget_manager,
        )

        # Track execution history for callbacks
        execution_history: list[StepInfo] = []
        original_history_append = agent.history.append
        step_counter = [0]  # Use list for closure mutability

        def tracked_append(item: tuple[str, str]):
            """Wrapper to track history additions and call callback."""
            original_history_append(item)
            step_counter[0] += 1

            action_or_code, output = item

            # Determine action type
            if action_or_code.startswith("Executed Code"):
                action = "CODE"
            elif "Delegated" in action_or_code or "DELEGATE" in action_or_code:
                action = "DELEGATE"
            elif "System" in action_or_code:
                action = "INIT"
            else:
                action = "OTHER"

            step_info = StepInfo(
                step_number=step_counter[0],
                action=action,
                input_text=action_or_code,
                output_text=output,
            )
            execution_history.append(step_info)

            if on_step:
                try:
                    on_step(step_info)
                except Exception as e:
                    logger.warning(f"Step callback error: {e}")

        # Monkey-patch the history append method
        agent.history.append = tracked_append  # type: ignore

        # Run task
        answer = agent.run(task)
        completed_at = datetime.now()

        # Store REPL state for follow-up queries
        if task_id:
            with self._storage_lock:
                self._repl_storage[task_id] = agent.repl
                logger.info(f"Stored REPL state for task {task_id}")

        # Get cost breakdown
        breakdown = budget_manager.get_breakdown()
        total_cost = budget_manager.current_cost

        return TaskResult(
            answer=answer,
            execution_history=execution_history,
            total_cost=total_cost,
            model_breakdown=breakdown,
            started_at=started_at,
            completed_at=completed_at,
            config_name=config_name,
            task_text=task,
        )

    def _get_api_keys(self) -> dict[str, str]:
        """
        Get API keys from session or environment variables.

        Priority:
        1. Session API keys (if session exists)
        2. Environment variables (fallback)

        Returns:
            Dict mapping provider names to API keys
        """
        api_keys: dict[str, str] = {}

        # Try session first
        if self.session:
            api_keys.update(self.session.api_keys)

        # Fill in missing keys from environment
        env_mappings = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }

        for provider, env_var in env_mappings.items():
            if provider not in api_keys:
                value = os.getenv(env_var)
                if value:
                    api_keys[provider] = value

        return api_keys

    def _load_config_with_keys(
        self,
        config_name: str,
        api_keys: dict[str, str]
    ) -> ProfileConfig:
        """
        Load configuration and attach API keys.

        Args:
            config_name: Profile name or path
            api_keys: Dict of API keys

        Returns:
            ProfileConfig with api_keys attached
        """
        # Check if it's a path or a name
        if "/" in config_name or config_name.endswith(".yaml"):
            config = self.config_service.load_profile_from_path(config_name)
        else:
            config = self.config_service.load_with_keys(config_name, api_keys)

        return config

    def _validate_api_keys(
        self,
        config: ProfileConfig,
        api_keys: dict[str, str]
    ) -> None:
        """
        Validate that required API keys are present.

        Args:
            config: The profile configuration
            api_keys: Available API keys

        Raises:
            ValueError: If required keys are missing
        """
        required_providers = set()

        # Check root and delegate providers
        for provider in [config.root.provider, config.delegate.provider]:
            provider = provider.lower()
            if provider != "ollama":  # Ollama is local, no key needed
                required_providers.add(provider)

        # Check module overrides
        if config.modules:
            for module in [config.modules.architect, config.modules.coder,
                          config.modules.responder, config.modules.delegator]:
                if module and module.provider.lower() != "ollama":
                    required_providers.add(module.provider.lower())

        # Find missing keys
        missing = [p for p in required_providers if p not in api_keys]

        if missing:
            raise ValueError(
                f"Missing API keys for providers: {', '.join(missing)}. "
                f"Set them in the session or environment variables."
            )

    def _configure_environment(self, api_keys: dict[str, str]) -> None:
        """
        Configure environment variables for DSPy.

        DSPy reads API keys from environment, so we need to set them
        from our session/runtime keys.

        Args:
            api_keys: Dict of API keys
        """
        env_mappings = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }

        for provider, env_var in env_mappings.items():
            if provider in api_keys:
                os.environ[env_var] = api_keys[provider]

    def estimate_cost(
        self,
        config_name: str,
        estimated_input_tokens: int = 10000,
        estimated_output_tokens: int = 2000,
        estimated_steps: int = 5,
    ) -> dict[str, float]:
        """
        Estimate the cost for running a task with a given config.

        Args:
            config_name: Profile name
            estimated_input_tokens: Expected input tokens per step
            estimated_output_tokens: Expected output tokens per step
            estimated_steps: Expected number of steps

        Returns:
            Dict with cost estimates
        """
        config = self.config_service.load_profile(config_name)

        # Calculate root agent cost
        root_input = (estimated_input_tokens * estimated_steps / 1_000_000)
        root_output = (estimated_output_tokens * estimated_steps / 1_000_000)
        root_cost = (
            root_input * config.root.pricing.input_per_1m +
            root_output * config.root.pricing.output_per_1m
        )

        return {
            "estimated_cost": root_cost,
            "max_budget": config.budget.max_usd,
            "root_model": f"{config.root.provider}/{config.root.model}",
            "estimated_steps": estimated_steps,
        }

    def run_followup(
        self,
        task_id: str,
        query: str,
        config_name: str,
    ) -> str:
        """
        Execute a follow-up query using stored REPL state.

        Args:
            task_id: Task identifier with stored REPL state
            query: Follow-up query to execute
            config_name: Config profile to use

        Returns:
            Agent's response to the query

        Raises:
            ValueError: If no REPL state found for task_id
        """
        # Retrieve stored REPL
        with self._storage_lock:
            repl = self._repl_storage.get(task_id)

        if not repl:
            raise ValueError(
                f"No REPL state found for task {task_id}. "
                "The task may not have completed or was cleaned up."
            )

        # Get API keys and load config
        api_keys = self._get_api_keys()
        config = self._load_config_with_keys(config_name, api_keys)
        self._validate_api_keys(config, api_keys)
        self._configure_environment(api_keys)

        # Initialize budget manager
        BudgetManager._clear()
        budget_manager = BudgetManager(max_budget=config.budget.max_usd)

        # Configure DSPy
        lm = get_lm_for_role("root", config, budget_manager=budget_manager)
        dspy.settings.configure(lm=lm)

        logger.info(f"Running follow-up query for task {task_id}")
        logger.info(f"REPL has {len(repl.globals)} globals, {len(repl.locals)} locals")

        # Create agent with existing REPL
        agent = RLMAgent(
            max_steps=config.root.max_steps,
            max_depth=config.root.max_depth,
            config=config,
            budget_manager=budget_manager,
            repl=repl,  # Pass existing REPL
        )

        # Run follow-up query
        answer = agent.run(query)

        # Update stored REPL (it may have new variables)
        with self._storage_lock:
            self._repl_storage[task_id] = agent.repl

        return answer

    def clear_repl_state(self, task_id: str) -> None:
        """
        Clear stored REPL state for a task.

        Args:
            task_id: Task identifier
        """
        with self._storage_lock:
            if task_id in self._repl_storage:
                del self._repl_storage[task_id]
                logger.info(f"Cleared REPL state for task {task_id}")

    def has_repl_state(self, task_id: str) -> bool:
        """
        Check if REPL state exists for a task.

        Args:
            task_id: Task identifier

        Returns:
            True if REPL state exists
        """
        with self._storage_lock:
            return task_id in self._repl_storage
