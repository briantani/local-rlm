"""
Optimize Architect for clean action extraction.

This optimizer focuses specifically on teaching the model to:
1. Output ONLY the action word (ANSWER or CODE)
2. Never output explanations, numbered lists, or verbose reasoning
3. Make the right decision in one word

Uses strict metrics that penalize any output that isn't exactly one of the two actions.
"""

import argparse
from pathlib import Path

import dspy

from src.modules.architect import Architect
from src.optimization.data import get_architect_data, split_train_val
from src.optimization.optimizer_factory import OptimizerFactory
from src.optimization.metrics import ArchitectMetrics
from src.core.logger import logger


def main():
    parser = argparse.ArgumentParser(description="Optimize Architect for clean action format")
    parser.add_argument(
        "--optimizer",
        choices=["bootstrap", "mipro-light", "mipro-medium", "mipro-heavy"],
        default="bootstrap",
        help="Optimizer to use"
    )
    parser.add_argument(
        "--provider",
        default="ollama",
        help="LLM provider for optimization (ollama, gemini, openai)"
    )
    parser.add_argument(
        "--metric",
        choices=["strict", "format"],
        default="strict",
        help="Metric to use: strict (exact match + partial credit) or format (heavily penalizes verbose)"
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

    project_root = Path(__file__).parent.parent.parent
    save_path = project_root / "src/modules/architect_format_compiled.json"

    # Select metric
    if args.metric == "strict":
        metric_fn = ArchitectMetrics.strict_action_metric
        logger.info("Using strict metric (exact match preferred, partial credit for correct action)")
    else:
        metric_fn = ArchitectMetrics.format_strictness_metric
        logger.info("Using format strictness metric (heavily penalizes verbose outputs)")

    # Run optimization
    if args.optimizer == "bootstrap":
        OptimizerFactory.run_bootstrap(
            Architect,
            full_dataset,
            save_path,
            metric_fn,
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
            metric_fn,
            mode=mode,
        )

    logger.info("Done!")


if __name__ == "__main__":
    main()
