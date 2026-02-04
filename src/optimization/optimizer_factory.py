"""
Optimizer factory for DSPy module compilation.

Consolidates LM creation, teleprompter setup, and optimization orchestration
that was previously duplicated across compile_architect.py, optimize_coder.py,
and optimize_action_format.py.
"""

import os
from pathlib import Path
from typing import Callable

import dspy
from dspy.teleprompt import BootstrapFewShot, LabeledFewShot, MIPROv2, SIMBA

from src.core.logger import logger
from dotenv import load_dotenv

load_dotenv()


class OptimizerFactory:
    """Factory for creating LMs and running DSPy optimizations."""

    @staticmethod
    def create_lm(provider: str, model: str | None = None) -> dspy.LM:
        """
        Create a DSPy LM for optimization.

        Unlike the full agent which uses ProfileConfig and BudgetWrapper,
        optimization scripts just need a basic LM connection.

        Args:
            provider: LLM provider (gemini, openai, ollama)
            model: Optional model override. If None, uses sensible defaults.

        Returns:
            Configured DSPy LM instance

        Raises:
            ValueError: If provider is unsupported or API key is missing
        """
        match provider.lower():
            case "gemini":
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY not found in environment variables.")
                model_name = model or "gemini/gemini-2.5-flash"
                return dspy.LM(model_name, api_key=api_key)

            case "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment variables.")
                model_name = model or "openai/gpt-4o-mini"
                return dspy.LM(model_name, api_key=api_key)

            case "ollama":
                model_name = model or "ollama/qwen2.5-coder:7b"
                return dspy.LM(model_name, api_base="http://localhost:11434")

            case _:
                raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def run_labeled_fewshot(
        module_class: type,
        trainset: list,
        save_path: str | Path,
        k: int = 5,
    ) -> None:
        """
        Run LabeledFewShot optimization.

        Simplest optimizer: Just selects k examples as demos.
        No bootstrapping, no validation. Fast but less powerful.

        Args:
            module_class: DSPy module class to optimize
            trainset: Training examples
            save_path: Path to save compiled module
            k: Number of examples to use as demos
        """
        logger.info(f"Using LabeledFewShot optimizer (k={k})...")

        teleprompter = LabeledFewShot(k=k)
        module = module_class()
        compiled = teleprompter.compile(module, trainset=trainset)

        compiled.save(str(save_path))
        logger.info(f"Saved to {save_path}")

    @staticmethod
    def run_bootstrap(
        module_class: type,
        trainset: list,
        save_path: str | Path,
        metric_fn: Callable,
        max_bootstrapped_demos: int = 4,
        max_labeled_demos: int = 4,
        setup_fn: Callable | None = None,
        cleanup_fn: Callable | None = None,
    ) -> None:
        """
        Run BootstrapFewShot optimization.

        Best for: Small datasets (10-20 examples)
        How it works: Generates Chain-of-Thought rationales for examples,
        validates with metric, keeps successful demos.

        Args:
            module_class: DSPy module class to optimize
            trainset: Training examples
            save_path: Path to save compiled module
            metric_fn: Validation metric (signature: (example, prediction, trace=None) -> float)
            max_bootstrapped_demos: Max synthetic demos to generate
            max_labeled_demos: Max demos to use from trainset directly
            setup_fn: Optional function to call before optimization (e.g., create mock files)
            cleanup_fn: Optional function to call after optimization (e.g., remove mock files)
        """
        logger.info("Using BootstrapFewShot optimizer...")

        if setup_fn:
            setup_fn()

        try:
            teleprompter = BootstrapFewShot(
                metric=metric_fn,
                max_bootstrapped_demos=max_bootstrapped_demos,
                max_labeled_demos=max_labeled_demos,
            )

            module = module_class()
            compiled = teleprompter.compile(module, trainset=trainset)

            compiled.save(str(save_path))
            logger.info(f"Saved to {save_path}")
        finally:
            if cleanup_fn:
                cleanup_fn()

    @staticmethod
    def run_mipro(
        module_class: type,
        trainset: list,
        valset: list,
        save_path: str | Path,
        metric_fn: Callable,
        mode: str = "light",
        max_bootstrapped_demos: int = 4,
        max_labeled_demos: int = 4,
        num_threads: int = 4,
    ) -> None:
        """
        Run MIPROv2 optimization.

        Best for: Larger datasets (50+ examples)
        How it works:
        1. Bootstraps few-shot candidates
        2. Proposes instruction candidates (data-aware, program-aware)
        3. Uses Bayesian Optimization to find best combo

        Args:
            module_class: DSPy module class to optimize
            trainset: Training examples
            valset: Validation examples (critical to prevent overfitting)
            save_path: Path to save compiled module
            metric_fn: Validation metric
            mode: Optimization intensity ("light", "medium", "heavy")
            max_bootstrapped_demos: Max synthetic demos
            max_labeled_demos: Max labeled demos
            num_threads: Number of threads for parallel evaluation
        """
        logger.info(f"Using MIPROv2 optimizer (mode={mode})...")

        teleprompter = MIPROv2(
            metric=metric_fn,
            auto=mode,
            num_threads=num_threads,
            verbose=True,
        )

        module = module_class()
        compiled = teleprompter.compile(
            module,
            trainset=trainset,
            valset=valset,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
        )

        compiled.save(str(save_path))
        logger.info(f"Saved to {save_path}")

    @staticmethod
    def run_simba(
        module_class: type,
        trainset: list,
        save_path: str | Path,
        metric_fn: Callable,
        bsize: int | None = None,
        num_candidates: int = 6,
        max_steps: int = 8,
        max_demos: int = 4,
        num_threads: int = 4,
    ) -> None:
        """
        Run SIMBA (Stochastic Introspective Mini-Batch Ascent) optimization.

        Best for: Self-improvement through LLM reflection
        How it works:
        1. Samples mini-batches
        2. Identifies challenging examples with high output variability
        3. LLM analyzes its own failures and generates improvement rules
        4. Adds successful examples as demonstrations

        Args:
            module_class: DSPy module class to optimize
            trainset: Training examples
            save_path: Path to save compiled module
            metric_fn: Validation metric
            bsize: Mini-batch size (if None, defaults to min(32, len(trainset)))
            num_candidates: New candidates per iteration
            max_steps: Optimization steps
            max_demos: Max demos per predictor
            num_threads: Number of threads
        """
        logger.info("Using SIMBA optimizer...")

        if bsize is None:
            bsize = min(32, len(trainset))

        teleprompter = SIMBA(
            metric=metric_fn,
            bsize=bsize,
            num_candidates=num_candidates,
            max_steps=max_steps,
            max_demos=max_demos,
            num_threads=num_threads,
        )

        module = module_class()
        compiled = teleprompter.compile(module, trainset=trainset)

        compiled.save(str(save_path))
        logger.info(f"Saved to {save_path}")

    @staticmethod
    def run_gepa(
        module_class: type,
        trainset: list,
        valset: list,
        save_path: str | Path,
        metric_fn: Callable,
        mode: str = "light",
        num_threads: int = 4,
    ) -> None:
        """
        Run GEPA (Genetic-Pareto Reflective Optimizer) optimization.

        Best for: Complex tasks with rich textual feedback
        How it works:
        1. Evolutionary optimization with Pareto frontier
        2. LLM reflects on execution traces and feedback
        3. Proposes new instructions based on failure analysis
        4. Maintains diverse candidate pool

        Note: Requires 'gepa' package (pip install gepa)
        Note: metric_fn must return {"score": float, "feedback": str} for GEPA

        Args:
            module_class: DSPy module class to optimize
            trainset: Training examples
            valset: Validation examples
            save_path: Path to save compiled module
            metric_fn: Feedback metric (returns dict with score and feedback)
            mode: Optimization intensity ("light", "medium", "heavy")
            num_threads: Number of threads
        """
        try:
            from dspy.teleprompt import GEPA
        except ImportError:
            logger.error("GEPA requires the 'gepa' package. Install with: pip install gepa")
            return

        logger.info(f"Using GEPA optimizer (mode={mode})...")

        teleprompter = GEPA(
            metric=metric_fn,
            auto=mode,
            num_threads=num_threads,
            track_stats=True,
        )

        module = module_class()
        compiled = teleprompter.compile(
            module,
            trainset=trainset,
            valset=valset,
        )

        compiled.save(str(save_path))
        logger.info(f"Saved to {save_path}")
