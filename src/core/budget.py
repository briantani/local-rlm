import threading
from functools import wraps
from typing import Any

import dspy


class BudgetExceededError(Exception):
    """Raised when the token budget is exceeded."""
    pass


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

    Uses a decorator-based singleton pattern for cleaner implementation.
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

        # Pricing for Gemini 1.5 Flash (approximate)
        # Input: $0.075 / 1M tokens
        # Output: $0.30 / 1M tokens
        self.input_price_per_1m = 0.075
        self.output_price_per_1m = 0.30

    def add_usage(self, input_tokens: int, output_tokens: int):
        """
        Thread-safe method to add token usage and update cost.
        """
        input_cost = (input_tokens / 1_000_000) * self.input_price_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_price_per_1m
        total_cost = input_cost + output_cost

        with self._lock:
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.current_cost += total_cost

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


class BudgetWrapper(dspy.BaseLM):
    """
    Wraps a dspy.LM to enforce budget constraints.
    """
    def __init__(self, lm: Any, budget_manager: BudgetManager):
        # Initialize BaseLM with the wrapped model's name or a default
        model_name = getattr(lm, "model", "budget-wrapper")
        super().__init__(model=model_name)

        self.lm = lm
        self.budget_manager = budget_manager

    def __call__(self, *args, **kwargs):
        # Check budget before making the call
        self.budget_manager.check_budget()

        # Call the underlying LM
        # We assume the LM returns a list of strings or a string,
        # but for usage tracking we might need to inspect the response object if available.
        # DSPy 3.x LMs usually return a list of strings (completions).
        # Tracking exact usage is tricky without the raw response object.
        # For now, we will estimate or rely on dspy's history if possible,
        # but dspy.LM.__call__ returns the text.

        # TODO: Improve usage tracking. DSPy LMs often have a `history` or `inspect_history`
        # but getting the usage from the immediate call return is provider-specific.
        # For this phase, we will implement the *check* primarily.
        # We will try to estimate usage based on string length as a fallback
        # if we can't get real token counts easily from the wrapper return.

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

        self.budget_manager.add_usage(input_est, output_est)

        return response

    def __getattr__(self, name):
        # Delegate other attribute accesses to the underlying LM
        return getattr(self.lm, name)
