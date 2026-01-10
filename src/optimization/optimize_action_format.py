"""
Optimize Architect for clean action extraction.

This optimizer focuses specifically on teaching the model to:
1. Output ONLY the action word (ANSWER, CODE, or DELEGATE)
2. Never output explanations, numbered lists, or verbose reasoning
3. Make the right decision in one word

Uses a strict metric that penalizes any output that isn't exactly one of the three actions.
"""

import argparse
import os
import re
from pathlib import Path

import dspy
from dspy.teleprompt import BootstrapFewShot, MIPROv2

from dotenv import load_dotenv

from src.modules.architect import ArchitectSignature
from src.optimization.data import get_architect_data, split_train_val
from src.core.logger import logger

load_dotenv()


def create_lm(provider: str) -> dspy.LM:
    """Create LM for optimization."""
    match provider.lower():
        case "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found")
            return dspy.LM("gemini/gemini-2.5-flash", api_key=api_key)
        case "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found")
            return dspy.LM("openai/gpt-4o-mini", api_key=api_key)
        case "ollama":
            return dspy.LM("ollama/qwen2.5-coder:7b", api_base="http://localhost:11434")
        case _:
            raise ValueError(f"Unknown provider: {provider}")


def strict_action_metric(example, prediction, trace=None) -> float:
    """
    Strict metric that only accepts exact action words.
    
    Scoring:
    - 1.0: Exact match (e.g., "ANSWER" == "ANSWER")
    - 0.5: Correct action but with extra text (e.g., "ANSWER: because..." contains "ANSWER")
    - 0.0: Wrong action or no valid action found
    
    This teaches the model to be concise.
    """
    valid_actions = {"ANSWER", "CODE", "DELEGATE"}
    expected = example.action.upper().strip()
    
    # Handle both Prediction object and dict
    if isinstance(prediction, dict):
        predicted_raw = prediction.get("action", "")
    else:
        predicted_raw = getattr(prediction, "action", "")
    
    predicted = predicted_raw.upper().strip()
    
    # Perfect match - exactly one word
    if predicted in valid_actions and predicted == expected:
        return 1.0
    
    # Check if the correct action is at the start
    if predicted.startswith(expected):
        # Penalize for extra content
        return 0.5
    
    # Check if action appears anywhere (very lenient)
    for action in valid_actions:
        if re.search(rf'\b{action}\b', predicted):
            if action == expected:
                return 0.3  # Found it but with noise
            else:
                return 0.0  # Wrong action
    
    # No valid action found at all
    return 0.0


def format_strictness_metric(example, prediction, trace=None) -> float:
    """
    Metric that heavily penalizes verbose outputs.
    
    Returns:
    - 1.0: Single word response matching action
    - 0.7: Correct action at start with minimal extra text
    - 0.3: Correct action buried in explanation
    - 0.0: Wrong or missing action
    """
    valid_actions = {"ANSWER", "CODE", "DELEGATE"}
    expected = example.action.upper().strip()
    
    if isinstance(prediction, dict):
        predicted_raw = prediction.get("action", "")
    else:
        predicted_raw = getattr(prediction, "action", "")
    
    predicted = predicted_raw.strip()
    predicted_upper = predicted.upper()
    
    # Best case: exactly one word
    if predicted_upper in valid_actions:
        return 1.0 if predicted_upper == expected else 0.0
    
    # Check for numbered lists or steps (bad pattern)
    if re.match(r'^\d+\.', predicted) or "STEP" in predicted_upper:
        # This is the verbose failure pattern we want to fix
        return 0.0
    
    # Check if it starts with the action
    if predicted_upper.startswith(expected):
        # How much extra content?
        extra_len = len(predicted) - len(expected)
        if extra_len < 10:
            return 0.8  # Minor extra text
        elif extra_len < 50:
            return 0.5  # Moderate extra text
        else:
            return 0.2  # Way too verbose
    
    # Action appears but not at start
    if re.search(rf'\b{expected}\b', predicted_upper):
        return 0.3
    
    return 0.0


class StrictArchitect(dspy.Module):
    """
    Architect module with reinforced output format instructions.
    """
    def __init__(self):
        super().__init__()
        # Use a signature with very explicit format instructions
        self.decide = dspy.ChainOfThought(ArchitectSignature)
    
    def forward(self, query: str, data_desc: str = "") -> dspy.Prediction:
        prediction = self.decide(query=query, data_desc=data_desc)
        return prediction


def run_optimization(provider: str, optimizer_type: str, num_demos: int = 4):
    """Run the optimization process."""
    logger.info(f"Starting optimization with {provider} using {optimizer_type}")
    
    # Setup LM
    lm = create_lm(provider)
    dspy.settings.configure(lm=lm)
    
    # Load data
    all_data = get_architect_data()
    logger.info(f"Loaded {len(all_data)} training examples")
    
    # Split data
    trainset, valset = split_train_val(all_data, val_ratio=0.3)
    logger.info(f"Train: {len(trainset)}, Val: {len(valset)}")
    
    # Create module to optimize
    architect = StrictArchitect()
    
    # Choose optimizer
    if optimizer_type == "bootstrap":
        optimizer = BootstrapFewShot(
            metric=format_strictness_metric,
            max_bootstrapped_demos=num_demos,
            max_labeled_demos=num_demos,
            max_rounds=2,
        )
        compiled = optimizer.compile(architect, trainset=trainset)
        
    elif optimizer_type == "mipro":
        optimizer = MIPROv2(
            metric=format_strictness_metric,
            num_candidates=5,
            init_temperature=1.0,
        )
        compiled = optimizer.compile(
            architect, 
            trainset=trainset, 
            valset=valset,
            num_batches=10,
            max_bootstrapped_demos=num_demos,
            max_labeled_demos=num_demos,
        )
    else:
        raise ValueError(f"Unknown optimizer: {optimizer_type}")
    
    # Evaluate on validation set
    logger.info("Evaluating on validation set...")
    correct = 0
    perfect = 0
    for example in valset:
        try:
            pred = compiled(query=example.query, data_desc=example.data_desc)
            score = format_strictness_metric(example, pred)
            if score > 0:
                correct += 1
            if score == 1.0:
                perfect += 1
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
    
    accuracy = correct / len(valset) if valset else 0
    perfect_rate = perfect / len(valset) if valset else 0
    logger.info(f"Validation accuracy: {accuracy:.2%}")
    logger.info(f"Perfect format rate: {perfect_rate:.2%}")
    
    # Save compiled module
    output_path = Path("src/modules/compiled_architect.json")
    compiled.save(str(output_path))
    logger.info(f"Saved compiled module to {output_path}")
    
    return compiled, accuracy


def main():
    parser = argparse.ArgumentParser(
        description="Optimize Architect for strict action output format"
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "gemini", "openai"],
        default="ollama",
        help="LLM provider to use"
    )
    parser.add_argument(
        "--optimizer",
        choices=["bootstrap", "mipro"],
        default="bootstrap",
        help="Optimizer type"
    )
    parser.add_argument(
        "--demos",
        type=int,
        default=4,
        help="Number of demo examples"
    )
    
    args = parser.parse_args()
    
    compiled, accuracy = run_optimization(
        provider=args.provider,
        optimizer_type=args.optimizer,
        num_demos=args.demos,
    )
    
    print(f"\n{'='*50}")
    print("Optimization complete!")
    print(f"Accuracy: {accuracy:.2%}")
    print("Saved to: src/modules/compiled_architect.json")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
