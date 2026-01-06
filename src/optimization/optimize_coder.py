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
from dspy.teleprompt import LabeledFewShot, BootstrapFewShot, MIPROv2, SIMBA

from src.modules.coder import Coder
from src.core.repl import PythonREPL
from src.core.logger import logger
from src.optimization.data import get_coder_data, split_train_val
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


def validate_code_execution(example, prediction, trace=None) -> float:
    """
    Metric: Validate that generated code executes successfully.

    Compatible with both BootstrapFewShot (prediction=Prediction) and SIMBA (prediction=dict).

    Scoring:
    - 0.0: Syntax error or execution error
    - 0.5: Executes but output doesn't match expected
    - 1.0: Executes and matches expected output (if provided)

    Returns:
        Float score for the prediction
    """
    repl = PythonREPL()

    try:
        # Handle both Prediction object and dict
        if isinstance(prediction, dict):
            code = prediction.get("python_code", prediction.get("code", ""))
        else:
            code = prediction.python_code

        if not code:
            return 0.0

        output = repl.execute(code)

        # Check for errors
        if "Traceback" in output or "Error" in output:
            return 0.0

        # Check expected output if provided
        if hasattr(example, "expected_output") and example.expected_output:
            if example.expected_output in output:
                return 1.0
            return 0.5  # Executed but wrong output

        return 1.0  # No expected output, execution success is enough

    except Exception:
        return 0.0


def validate_code_with_feedback(example, prediction, trace=None, pred_name=None, pred_trace=None):
    """
    GEPA-compatible metric with textual feedback.

    Returns dict with score and feedback for GEPA's reflective optimization.
    """
    repl = PythonREPL()

    try:
        # Handle both Prediction object and dict
        if isinstance(prediction, dict):
            code = prediction.get("python_code", prediction.get("code", ""))
        else:
            code = prediction.python_code

        if not code:
            return {
                "score": 0.0,
                "feedback": "No code generated"
            }

        output = repl.execute(code)

        if "Traceback" in output or "Error" in output:
            return {
                "score": 0.0,
                "feedback": f"Code execution failed with error: {output[:200]}"
            }

        if hasattr(example, "expected_output") and example.expected_output:
            if example.expected_output in output:
                return {"score": 1.0, "feedback": "Code executed correctly with expected output."}
            return {
                "score": 0.5,
                "feedback": f"Code executed but output '{output[:100]}' doesn't contain expected '{example.expected_output}'"
            }

        return {"score": 1.0, "feedback": "Code executed successfully without errors."}

    except Exception as e:
        return {"score": 0.0, "feedback": f"Exception during execution: {str(e)}"}


def optimize_with_labeled_fewshot(trainset: list, save_path: str, k: int = 5):
    """
    Optimize using LabeledFewShot.

    Simplest optimizer: Just selects k examples as demos.
    No bootstrapping, no validation. Fast but less powerful.
    """
    logger.info(f"Using LabeledFewShot optimizer (k={k})...")

    teleprompter = LabeledFewShot(k=k)

    coder = Coder()
    compiled = teleprompter.compile(coder, trainset=trainset)

    compiled.save(save_path)
    logger.info(f"Saved to {save_path}")


def optimize_with_bootstrap(trainset: list, save_path: str):
    """
    Optimize using BootstrapFewShot.

    Creates mock files, runs code, validates output.
    Keeps only examples that pass the metric.
    """
    logger.info("Using BootstrapFewShot optimizer...")

    setup_mock_files()

    try:
        teleprompter = BootstrapFewShot(
            metric=validate_code_execution,
            max_bootstrapped_demos=4,
            max_labeled_demos=4,
        )

        coder = Coder()
        compiled = teleprompter.compile(coder, trainset=trainset)

        compiled.save(save_path)
        logger.info(f"Saved to {save_path}")
    finally:
        cleanup_mock_files()


def optimize_with_mipro(trainset: list, valset: list, save_path: str, mode: str = "light"):
    """
    Optimize using MIPROv2.

    Full optimization: instructions + demos via Bayesian optimization.
    Requires more examples and compute but produces best results.
    """
    logger.info(f"Using MIPROv2 optimizer (mode={mode})...")

    setup_mock_files()

    try:
        teleprompter = MIPROv2(
            metric=validate_code_execution,
            auto=mode,
            num_threads=4,
            verbose=True,
        )

        coder = Coder()
        compiled = teleprompter.compile(
            coder,
            trainset=trainset,
            valset=valset,
            max_bootstrapped_demos=3,
            max_labeled_demos=3,
        )

        compiled.save(save_path)
        logger.info(f"Saved to {save_path}")
    finally:
        cleanup_mock_files()


def optimize_with_simba(trainset: list, save_path: str):
    """
    Optimize using SIMBA (Stochastic Introspective Mini-Batch Ascent).

    LLM analyzes its own code generation failures and generates improvement rules.
    Good for learning from execution errors.
    """
    logger.info("Using SIMBA optimizer...")

    setup_mock_files()

    try:
        teleprompter = SIMBA(
            metric=validate_code_execution,
            bsize=min(32, len(trainset)),
            num_candidates=6,
            max_steps=8,
            max_demos=4,
            num_threads=4,
        )

        coder = Coder()
        compiled = teleprompter.compile(coder, trainset=trainset)

        compiled.save(save_path)
        logger.info(f"Saved to {save_path}")
    finally:
        cleanup_mock_files()


def optimize_with_gepa(trainset: list, valset: list, save_path: str, mode: str = "light"):
    """
    Optimize using GEPA (Genetic-Pareto Reflective Optimizer).

    Uses execution traces and error messages as feedback for reflective improvement.
    Particularly good for code generation where errors are informative.
    """
    try:
        from dspy.teleprompt import GEPA
    except ImportError:
        logger.error("GEPA requires the 'gepa' package. Install with: pip install gepa")
        return

    logger.info(f"Using GEPA optimizer (mode={mode})...")

    setup_mock_files()

    try:
        teleprompter = GEPA(
            metric=validate_code_with_feedback,
            auto=mode,
            num_threads=4,
            track_stats=True,
        )

        coder = Coder()
        compiled = teleprompter.compile(
            coder,
            trainset=trainset,
            valset=valset,
        )

        compiled.save(save_path)
        logger.info(f"Saved to {save_path}")
    finally:
        cleanup_mock_files()


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
        lm = create_lm_for_optimization(args.provider)
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

    if args.optimizer == "labeled":
        optimize_with_labeled_fewshot(full_dataset, str(save_path), k=args.k)
    elif args.optimizer == "bootstrap":
        optimize_with_bootstrap(full_dataset, str(save_path))
    elif args.optimizer == "simba":
        optimize_with_simba(full_dataset, str(save_path))
    elif args.optimizer.startswith("mipro-"):
        trainset, valset = split_train_val(full_dataset)
        logger.info(f"Split: {len(trainset)} train, {len(valset)} val")
        mode = args.optimizer.replace("mipro-", "")
        optimize_with_mipro(trainset, valset, str(save_path), mode)
    elif args.optimizer.startswith("gepa-"):
        trainset, valset = split_train_val(full_dataset)
        logger.info(f"Split: {len(trainset)} train, {len(valset)} val")
        mode = args.optimizer.replace("gepa-", "")
        optimize_with_gepa(trainset, valset, str(save_path), mode)

    logger.info("Done!")


if __name__ == "__main__":
    main()
