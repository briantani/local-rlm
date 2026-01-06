import threading
from dataclasses import dataclass, field
from functools import wraps
from typing import Any

import dspy


class BudgetExceededError(Exception):
    """Raised when the token budget is exceeded."""
    pass


@dataclass
class ModelUsage:
    """Tracks usage and pricing for a specific model."""
    input_price_per_1m: float
    output_price_per_1m: float
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0


def singleton(cls):
    """Thread-safe singleton decorator."""
    instances = {}
    lock = threading.Lock()

    @wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    # Allow clearing for testing
    get_instance._clear = lambda: instances.pop(cls, None)
    return get_instance


@singleton
class BudgetManager:
    """
    Thread-safe singleton to track token usage and cost.

    Supports per-model pricing: each model is registered with its own pricing,
    and usage is tracked separately. The global budget limit applies to the
    sum of all model costs.

    Call BudgetManager._clear() in tests to reset the singleton.
    """

    def __init__(self, max_budget: float = 1.0):
        """
        Initialize the budget manager.

        Args:
            max_budget: Maximum allowed cost in USD. Default is $1.00.
        """
        self.max_budget = max_budget
        self.current_cost = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._lock = threading.Lock()

        # Per-model tracking (Phase 11)
        self.model_usage: dict[str, ModelUsage] = {}

        # Default pricing for backward compatibility (Gemini 2.5 Flash)
        self.input_price_per_1m = 0.30
        self.output_price_per_1m = 2.50

    def register_model(
        self,
        model_id: str,
        input_price_per_1m: float,
        output_price_per_1m: float
    ) -> None:
        """
        Register a model with its pricing info.

        Args:
            model_id: Unique identifier for the model (e.g., "gpt-5", "gemini-2.5-flash")
            input_price_per_1m: Cost per 1M input tokens in USD
            output_price_per_1m: Cost per 1M output tokens in USD
        """
        with self._lock:
            self.model_usage[model_id] = ModelUsage(
                input_price_per_1m=input_price_per_1m,
                output_price_per_1m=output_price_per_1m,
            )

    def add_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model_id: str | None = None
    ) -> None:
        """
        Thread-safe method to add token usage and update cost.

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            model_id: Optional model identifier. If provided, uses that model's
                      pricing. Otherwise falls back to default pricing.
        """
        with self._lock:
            if model_id and model_id in self.model_usage:
                # Use per-model pricing
                usage = self.model_usage[model_id]
                input_cost = (input_tokens / 1_000_000) * usage.input_price_per_1m
                output_cost = (output_tokens / 1_000_000) * usage.output_price_per_1m
                total_cost = input_cost + output_cost

                usage.total_input_tokens += input_tokens
                usage.total_output_tokens += output_tokens
                usage.total_cost += total_cost
            else:
                # Fall back to default pricing (backward compatibility)
                input_cost = (input_tokens / 1_000_000) * self.input_price_per_1m
                output_cost = (output_tokens / 1_000_000) * self.output_price_per_1m
                total_cost = input_cost + output_cost

            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.current_cost += total_cost

    def get_breakdown(self) -> dict[str, float]:
        """
        Get cost breakdown by model.

        Returns:
            Dictionary mapping model_id to total cost for that model
        """
        with self._lock:
            return {model_id: u.total_cost for model_id, u in self.model_usage.items()}

    def get_model_stats(self, model_id: str) -> ModelUsage | None:
        """
        Get detailed stats for a specific model.

        Args:
            model_id: The model identifier

        Returns:
            ModelUsage dataclass or None if model not registered
        """
        with self._lock:
            return self.model_usage.get(model_id)

    def check_budget(self):
        """
        Checks if the current cost exceeds the maximum budget.
        Raises BudgetExceededError if limit is reached.
        """
        with self._lock:
            if self.current_cost >= self.max_budget:
                raise BudgetExceededError(
                    f"Budget exceeded! Current cost: ${self.current_cost:.6f}, Limit: ${self.max_budget:.6f}"
                )

    def reset(self):
        """Resets the budget counters (useful for testing)."""
        with self._lock:
            self.current_cost = 0.0
            self.total_input_tokens = 0
            self.total_output_tokens = 0
            self.model_usage.clear()


class BudgetWrapper(dspy.BaseLM):
    """
    Wraps a dspy.LM to enforce budget constraints.

    Supports per-model budget tracking when _model_id is set.
    """
    def __init__(
        self,
        lm: Any,
        budget_manager: BudgetManager,
        model_id: str | None = None
    ):
        # Initialize BaseLM with the wrapped model's name or a default
        model_name = getattr(lm, "model", "budget-wrapper")
        super().__init__(model=model_name)

        self.lm = lm
        self.budget_manager = budget_manager
        self._model_id = model_id  # For per-model tracking

    def __call__(self, *args, **kwargs):
        # Check budget before making the call
        self.budget_manager.check_budget()

        # Call the underlying LM
        response = self.lm(*args, **kwargs)

        # Very rough estimation if we can't get real tokens: 1 token ~= 4 chars
        # This is just to ensure the mechanism works for the "Guardrails" phase.
        # In a real implementation, we'd hook into the provider's usage stats.

        # Input estimation
        prompt = str(args) + str(kwargs)
        input_est = len(prompt) // 4

        # Output estimation
        output_text = ""
        if isinstance(response, list):
            output_text = "".join(response)
        else:
            output_text = str(response)
        output_est = len(output_text) // 4

        # Use per-model tracking if model_id is set
        self.budget_manager.add_usage(
            input_tokens=input_est,
            output_tokens=output_est,
            model_id=self._model_id
        )

        return response

    def __getattr__(self, name):
        # Delegate other attribute accesses to the underlying LM
        return getattr(self.lm, name)
