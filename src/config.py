import os
import dspy
from dotenv import load_dotenv
from src.core.budget import BudgetManager, BudgetWrapper

load_dotenv()

def get_lm(provider_name: str) -> dspy.LM:
    """
    Factory function to get the Language Model provider.

    Args:
        provider_name: The name of the provider ("gemini" or "ollama").

    Returns:
        A dspy.LM instance (wrapped with BudgetWrapper).

    Raises:
        ValueError: If the provider is not supported.
    """
    budget_manager = BudgetManager()
    lm = None

    match provider_name.lower():
        case "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables.")
            # dspy.LM is the unified client in DSPy 3.x
            lm = dspy.LM("gemini/gemini-2.0-flash", api_key=api_key)

        case "ollama":
            # dspy.LM is the unified client in DSPy 3.x
            # We specify the provider/model format
            lm = dspy.LM("ollama/llama3", api_base="http://localhost:11434")

        case _:
            raise ValueError(f"Unsupported provider: {provider_name}")

    return BudgetWrapper(lm, budget_manager)
