import os
import dspy
from dotenv import load_dotenv
from src.core.budget import BudgetManager, BudgetWrapper
from src.core.config_loader import (
    ProfileConfig,
    get_model_config_for_role,
)

load_dotenv()


def get_lm_for_role(
    role: str,
    config: ProfileConfig,
    budget_manager: BudgetManager | None = None,
    is_delegate: bool = False,
) -> dspy.LM:
    """
    Get a Language Model for a specific role using ProfileConfig.

    Resolution order:
    1. Per-module override (config.modules.{role})
    2. Delegate config (if is_delegate=True)
    3. Root config (default)

    The model is automatically registered with the BudgetManager using its
    per-model pricing from the config.

    Args:
        role: The role name ("architect", "coder", "responder", "delegator", "root", "delegate")
        config: The ProfileConfig containing model configurations
        budget_manager: Optional BudgetManager instance. If None, uses singleton.
        is_delegate: Whether this is for a delegate agent

    Returns:
        A dspy.LM instance wrapped with BudgetWrapper

    Raises:
        ValueError: If provider is not supported or API key is missing
    """
    # Get the model config for this role
    if role == "root":
        model_config = config.root.to_model_config()
    elif role == "delegate":
        model_config = config.delegate.to_model_config()
    else:
        model_config = get_model_config_for_role(role, config, is_delegate)

    # Get or create budget manager
    if budget_manager is None:
        budget_manager = BudgetManager(max_budget=config.budget.max_usd)

    # Register the model with its pricing
    budget_manager.register_model(
        model_id=model_config.model_id,
        input_price_per_1m=model_config.pricing.input_per_1m,
        output_price_per_1m=model_config.pricing.output_per_1m,
    )

    # Create the LM using the existing factory logic
    return _create_lm(
        provider=model_config.provider,
        model=model_config.model,
        budget_manager=budget_manager,
        model_id=model_config.model_id,
    )


def _create_lm(
    provider: str,
    model: str,
    budget_manager: BudgetManager,
    model_id: str | None = None,
) -> dspy.LM:
    """
    Internal factory to create a dspy.LM instance.

    Args:
        provider: Provider name (gemini, openai, ollama)
        model: Model name
        budget_manager: BudgetManager instance
        model_id: Optional model ID for budget tracking

    Returns:
        A dspy.LM instance wrapped with BudgetWrapper
    """
    lm = None

    match provider.lower():
        case "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables.")

            target_model = model
            if not target_model.startswith("gemini/"):
                target_model = f"gemini/{target_model}"

            lm = dspy.LM(target_model, api_key=api_key)

        case "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables.")

            target_model = model
            if not target_model.startswith("openai/"):
                target_model = f"openai/{target_model}"

            # Support custom base URL (for Fireworks, Together, etc.)
            base_url = os.getenv("OPENAI_BASE_URL")
            if base_url:
                lm = dspy.LM(target_model, api_key=api_key, api_base=base_url)
            else:
                lm = dspy.LM(target_model, api_key=api_key)

        case "ollama":
            target_model = model
            if not target_model.startswith("ollama/"):
                target_model = f"ollama/{target_model}"

            lm = dspy.LM(target_model, api_base="http://localhost:11434")

        case _:
            raise ValueError(f"Unsupported provider: {provider}")

    # Wrap with budget tracking
    wrapper = BudgetWrapper(lm, budget_manager)
    wrapper._model_id = model_id  # Store for tracking
    return wrapper
