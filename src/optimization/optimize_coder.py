"""
Compile/Optimize the Coder module using DSPy optimizers.

The Coder module generates Python code for tasks. Optimization focuses on:
1. Correct syntax (validated by ast.parse)
2. Successful execution (no tracebacks)
3. Expected output matching (when available)

Optimization Strategy:
=====================
- LabeledFewShot: Simple, just uses examples as demos (no bootstrapping)
- BootstrapFewShot: Generates rationales, validates execution
- MIPROv2: Full instruction + demo optimization (requires more data)
- SIMBA: Self-reflective improvement through failure analysis
- GEPA: Evolutionary optimization with rich textual feedback
"""

import argparse
import os
from pathlib import Path

import dspy

from src.modules.coder import Coder
from src.optimization.data import get_coder_data, split_train_val
from src.optimization.optimizer_factory import OptimizerFactory
from src.optimization.metrics import CoderMetrics
from src.core.logger import logger


def setup_mock_files():
    """Create mock files needed for validation."""
    # Excel file
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["E5"] = "=SUM(A1:A5)"
        wb.save("dataset.xlsx")
    except ImportError:
        pass

    # CSV file
    with open("data.csv", "w") as f:
        f.write("col1,col2,value\n1,2,10\n3,4,20")


def cleanup_mock_files():
    """Remove mock files after validation."""
    for f in ["dataset.xlsx", "data.csv"]:
        if os.path.exists(f):
            os.remove(f)


def main():
    parser = argparse.ArgumentParser(description="Optimize the Coder module")
    parser.add_argument(
        "--optimizer",
        choices=[
            "labeled", "bootstrap",
            "mipro-light", "mipro-medium", "mipro-heavy",
            "simba",
            "gepa-light", "gepa-medium", "gepa-heavy"
        ],
        default="labeled",
        help="Optimizer to use. labeled is fastest, mipro/simba/gepa are most powerful."
    )
    parser.add_argument(
        "--provider",
        default="ollama",
        help="LLM provider for optimization (ollama, gemini, openai)"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of demos for LabeledFewShot (default: 5)"
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
    full_dataset = get_coder_data()
    logger.info(f"Loaded {len(full_dataset)} examples")

    project_root = Path(__file__).parent.parent.parent
    save_path = project_root / "src/modules/coder_compiled.json"

    # Run optimization based on selected optimizer
    if args.optimizer == "labeled":
        OptimizerFactory.run_labeled_fewshot(
            Coder,
            full_dataset,
            save_path,
            k=args.k,
        )
    elif args.optimizer == "bootstrap":
        OptimizerFactory.run_bootstrap(
            Coder,
            full_dataset,
            save_path,
            CoderMetrics.validate_code_execution,
            setup_fn=setup_mock_files,
            cleanup_fn=cleanup_mock_files,
        )
    elif args.optimizer == "simba":
        OptimizerFactory.run_simba(
            Coder,
            full_dataset,
            save_path,
            CoderMetrics.validate_code_execution,
        )
    elif args.optimizer.startswith("mipro-"):
        trainset, valset = split_train_val(full_dataset)
        logger.info(f"Split: {len(trainset)} train, {len(valset)} val")
        mode = args.optimizer.replace("mipro-", "")
        OptimizerFactory.run_mipro(
            Coder,
            trainset,
            valset,
            save_path,
            CoderMetrics.validate_code_execution,
            mode=mode,
        )
    elif args.optimizer.startswith("gepa-"):
        trainset, valset = split_train_val(full_dataset)
        logger.info(f"Split: {len(trainset)} train, {len(valset)} val")
        mode = args.optimizer.replace("gepa-", "")
        OptimizerFactory.run_gepa(
            Coder,
            trainset,
            valset,
            save_path,
            CoderMetrics.validate_code_with_feedback,
            mode=mode,
        )

    logger.info("Done!")


if __name__ == "__main__":
    main()
