import os
import dspy
from dotenv import load_dotenv
from src.core.budget import BudgetManager, BudgetWrapper

load_dotenv()


def get_config(key: str, default=None, cast_type=None):
    """
    Helper to get configuration from environment variables with type casting.

    Args:
        key: Environment variable name
        default: Default value if not found
        cast_type: Type to cast to (int, float, bool, etc.)

    Returns:
        The configuration value, cast to the appropriate type
    """
    value = os.getenv(key, default)
    if value is None:
        return None
    if cast_type is bool:
        return value.lower() in ("true", "1", "yes")
    if cast_type is not None:
        return cast_type(value)
    return value


def get_lm(provider_name: str, model_name: str = None) -> dspy.LM:
    """
    Factory function to get the Language Model provider.

    Args:
        provider_name: The name of the provider ("gemini" or "ollama").
        model_name: Optional specific model name (e.g., "llama3", "qwen2.5-coder:14b").
                    If NOT provided, defaults are used.

    Returns:
        A dspy.LM instance (wrapped with BudgetWrapper).

    Raises:
        ValueError: If the provider is not supported.
    """
    # Load budget configuration from environment
    max_budget = get_config("MAX_BUDGET_USD", 1.0, float)
    input_price = get_config("INPUT_PRICE_PER_1M", 0.075, float)
    output_price = get_config("OUTPUT_PRICE_PER_1M", 0.30, float)

    # Initialize budget manager with configured values
    budget_manager = BudgetManager(max_budget=max_budget)
    budget_manager.input_price_per_1m = input_price
    budget_manager.output_price_per_1m = output_price

    lm = None

    match provider_name.lower():
        case "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables.")

            # Default to gemini-2.0-flash if not specified
            target_model = model_name if model_name else "gemini-2.0-flash"
            # Ensure prefix format is correct for dspy.LM (gemini/model-name)
            if not target_model.startswith("gemini/"):
                target_model = f"gemini/{target_model}"

            lm = dspy.LM(target_model, api_key=api_key)

        case "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables.")

            # Default to gpt-4o-mini
            target_model = model_name if model_name else "gpt-4o-mini"
             # Ensure prefix format is correct for dspy.LM (openai/model-name)
            if not target_model.startswith("openai/"):
                target_model = f"openai/{target_model}"

            lm = dspy.LM(target_model, api_key=api_key)

        case "ollama":
            # Default to qwen2.5-coder:14b if not specified, as it is superior for coding tasks
            target_model = model_name if model_name else "qwen2.5-coder:14b"
            # Ensure prefix format is correct for dspy.LM (ollama/model-name)
            if not target_model.startswith("ollama/"):
                target_model = f"ollama/{target_model}"

            # dspy.LM is the unified client in DSPy 3.x
            lm = dspy.LM(target_model, api_base="http://localhost:11434")

        case _:
            raise ValueError(f"Unsupported provider: {provider_name}")

    return BudgetWrapper(lm, budget_manager)
