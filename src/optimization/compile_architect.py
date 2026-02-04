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
import dspy

from src.modules.architect import Architect
from src.optimization.data import get_architect_data, split_train_val
from src.optimization.optimizer_factory import OptimizerFactory
from src.optimization.metrics import ArchitectMetrics
from src.core.logger import logger


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
        lm = OptimizerFactory.create_lm(args.provider)
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

    # Run optimization based on selected optimizer
    if args.optimizer == "bootstrap":
        OptimizerFactory.run_bootstrap(
            Architect,
            full_dataset,
            save_path,
            ArchitectMetrics.validate_action,
        )
    elif args.optimizer == "simba":
        OptimizerFactory.run_simba(
            Architect,
            full_dataset,
            save_path,
            ArchitectMetrics.validate_action,
        )
    elif args.optimizer.startswith("mipro-"):
        trainset, valset = split_train_val(full_dataset)
        logger.info(f"Split: {len(trainset)} train, {len(valset)} val")
        mode = args.optimizer.replace("mipro-", "")
        OptimizerFactory.run_mipro(
            Architect,
            trainset,
            valset,
            save_path,
            ArchitectMetrics.validate_action,
            mode=mode,
        )
    elif args.optimizer.startswith("gepa-"):
        trainset, valset = split_train_val(full_dataset)
        logger.info(f"Split: {len(trainset)} train, {len(valset)} val")
        mode = args.optimizer.replace("gepa-", "")
        OptimizerFactory.run_gepa(
            Architect,
            trainset,
            valset,
            save_path,
            ArchitectMetrics.validate_action_with_feedback,
            mode=mode,
        )

    logger.info("Done!")


if __name__ == "__main__":
    main()
