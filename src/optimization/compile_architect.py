"""
Compile/Optimize the Architect module using DSPy optimizers.

Optimization Strategy:
=====================
- With few examples (<20): Use BootstrapFewShot (generates rationales)
- With more data (50+): Use MIPROv2 for instruction + demo optimization
- For self-improvement: Use SIMBA (LLM analyzes its own failures)
- For rich feedback: Use GEPA (evolutionary, reflection-based)

This script supports multiple optimizers via --optimizer flag.
"""

import argparse
import os
import dspy
from dspy.teleprompt import BootstrapFewShot, MIPROv2, SIMBA
from src.modules.architect import Architect
from src.optimization.data import get_architect_data, split_train_val
from src.core.logger import logger
from dotenv import load_dotenv

load_dotenv()


def create_lm_for_optimization(provider: str) -> dspy.LM:
    """
    Simple LM factory for optimization scripts.

    Unlike the full agent which uses ProfileConfig and BudgetWrapper,
    optimization scripts just need a basic LM connection.
    """
    match provider.lower():
        case "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables.")
            return dspy.LM("gemini/gemini-2.5-flash", api_key=api_key)

        case "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables.")
            return dspy.LM("openai/gpt-4o-mini", api_key=api_key)

        case "ollama":
            return dspy.LM("ollama/qwen2.5-coder:7b", api_base="http://localhost:11434")

        case _:
            raise ValueError(f"Unsupported provider: {provider}")


def validate_action(example, prediction, trace=None) -> float:
    """
    Metric: Check if the predicted action exactly matches the expected label.

    Compatible with both BootstrapFewShot (prediction=Prediction) and SIMBA (prediction=dict).

    Returns float for finer-grained optimization:
    - 1.0: Exact match
    - 0.0: No match
    """
    # Handle both Prediction object and dict
    if isinstance(prediction, dict):
        predicted = prediction.get("action", "").upper().strip()
    else:
        predicted = prediction.action.upper().strip()

    expected = example.action.upper().strip()
    return 1.0 if predicted == expected else 0.0


def validate_action_with_feedback(example, prediction, trace=None, pred_name=None, pred_trace=None):
    """
    GEPA-compatible metric with textual feedback.

    Returns dict with score and feedback for GEPA's reflective optimization.
    """
    # Handle both Prediction object and dict
    if isinstance(prediction, dict):
        predicted = prediction.get("action", "").upper().strip()
    else:
        predicted = prediction.action.upper().strip()

    expected = example.action.upper().strip()

    if predicted == expected:
        return {"score": 1.0, "feedback": f"Correct! Action '{predicted}' matches expected."}
    else:
        feedback = f"Incorrect. Expected '{expected}' but got '{predicted}'. "
        if expected == "ANSWER" and predicted == "CODE":
            feedback += "The output was already available in data_desc - no need for more code."
        elif expected == "CODE" and predicted == "ANSWER":
            feedback += "The task required computation or file reading - should have generated code."
        return {"score": 0.0, "feedback": feedback}


def optimize_with_bootstrap(trainset: list, save_path: str):
    """
    Optimize using BootstrapFewShot.

    Best for: Small datasets (10-20 examples)
    How it works: Generates Chain-of-Thought rationales for examples,
    validates with metric, keeps successful demos.
    """
    logger.info("Using BootstrapFewShot optimizer...")

    teleprompter = BootstrapFewShot(
        metric=validate_action,
        max_bootstrapped_demos=4,  # Generate up to 4 synthetic demos
        max_labeled_demos=4,       # Use up to 4 from trainset directly
    )

    architect = Architect()
    compiled = teleprompter.compile(architect, trainset=trainset)

    compiled.save(save_path)
    logger.info(f"Saved to {save_path}")


def optimize_with_mipro(trainset: list, valset: list, save_path: str, mode: str = "light"):
    """
    Optimize using MIPROv2.

    Best for: Larger datasets (50+ examples)
    How it works:
    1. Bootstraps few-shot candidates
    2. Proposes instruction candidates (data-aware, program-aware)
    3. Uses Bayesian Optimization to find best combo

    Modes:
    - light: ~10 trials, quick iteration
    - medium: ~25 trials, balanced
    - heavy: ~50+ trials, best quality (expensive)
    """
    logger.info(f"Using MIPROv2 optimizer (mode={mode})...")

    teleprompter = MIPROv2(
        metric=validate_action,
        auto=mode,  # "light", "medium", or "heavy"
        num_threads=4,
        verbose=True,
    )

    architect = Architect()
    compiled = teleprompter.compile(
        architect,
        trainset=trainset,
        valset=valset,  # Critical: prevents overfitting
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
    )

    compiled.save(save_path)
    logger.info(f"Saved to {save_path}")


def optimize_with_simba(trainset: list, save_path: str):
    """
    Optimize using SIMBA (Stochastic Introspective Mini-Batch Ascent).

    Best for: Self-improvement through LLM reflection
    How it works:
    1. Samples mini-batches
    2. Identifies challenging examples with high output variability
    3. LLM analyzes its own failures and generates improvement rules
    4. Adds successful examples as demonstrations
    """
    logger.info("Using SIMBA optimizer...")

    teleprompter = SIMBA(
        metric=validate_action,
        bsize=min(32, len(trainset)),  # Mini-batch size
        num_candidates=6,              # New candidates per iteration
        max_steps=8,                   # Optimization steps
        max_demos=4,                   # Max demos per predictor
        num_threads=4,
    )

    architect = Architect()
    compiled = teleprompter.compile(architect, trainset=trainset)

    compiled.save(save_path)
    logger.info(f"Saved to {save_path}")


def optimize_with_gepa(trainset: list, valset: list, save_path: str, mode: str = "light"):
    """
    Optimize using GEPA (Genetic-Pareto Reflective Optimizer).

    Best for: Complex tasks with rich textual feedback
    How it works:
    1. Evolutionary optimization with Pareto frontier
    2. LLM reflects on execution traces and feedback
    3. Proposes new instructions based on failure analysis
    4. Maintains diverse candidate pool

    Requires: gepa package (pip install gepa)
    """
    try:
        from dspy.teleprompt import GEPA
    except ImportError:
        logger.error("GEPA requires the 'gepa' package. Install with: pip install gepa")
        return

    logger.info(f"Using GEPA optimizer (mode={mode})...")

    teleprompter = GEPA(
        metric=validate_action_with_feedback,
        auto=mode,
        num_threads=4,
        track_stats=True,
    )

    architect = Architect()
    compiled = teleprompter.compile(
        architect,
        trainset=trainset,
        valset=valset,
    )

    compiled.save(save_path)
    logger.info(f"Saved to {save_path}")


def main():
    parser = argparse.ArgumentParser(description="Optimize the Architect module")
    parser.add_argument(
        "--optimizer",
        choices=[
            "bootstrap",
            "mipro-light", "mipro-medium", "mipro-heavy",
            "simba",
            "gepa-light", "gepa-medium", "gepa-heavy"
        ],
        default="bootstrap",
        help="Optimizer to use. bootstrap for small data, mipro/simba/gepa for larger datasets."
    )
    parser.add_argument(
        "--provider",
        default="ollama",
        help="LLM provider for optimization (ollama, gemini, openai)"
    )
    args = parser.parse_args()

    # Configure LM
    logger.info(f"Initializing LLM ({args.provider}) for optimization...")
    try:
        lm = create_lm_for_optimization(args.provider)
        dspy.settings.configure(lm=lm)
        logger.info(f"LM configured: {lm.model}")
    except Exception as e:
        logger.error(f"Error setting up LLM: {e}")
        return

    # Load data
    logger.info("Loading training data...")
    full_dataset = get_architect_data()
    logger.info(f"Loaded {len(full_dataset)} examples")

    save_path = "src/modules/compiled_architect.json"

    if args.optimizer == "bootstrap":
        optimize_with_bootstrap(full_dataset, save_path)
    elif args.optimizer == "simba":
        optimize_with_simba(full_dataset, save_path)
    elif args.optimizer.startswith("mipro-"):
        trainset, valset = split_train_val(full_dataset)
        logger.info(f"Split: {len(trainset)} train, {len(valset)} val")
        mode = args.optimizer.replace("mipro-", "")
        optimize_with_mipro(trainset, valset, save_path, mode)
    elif args.optimizer.startswith("gepa-"):
        trainset, valset = split_train_val(full_dataset)
        logger.info(f"Split: {len(trainset)} train, {len(valset)} val")
        mode = args.optimizer.replace("gepa-", "")
        optimize_with_gepa(trainset, valset, save_path, mode)

    logger.info("Done!")


if __name__ == "__main__":
    main()
