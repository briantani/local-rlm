import argparse
from pathlib import Path
import dspy
from dotenv import load_dotenv
from src.config import get_lm_for_role
from src.core.agent import RLMAgent
from src.core.budget import BudgetManager
from src.core.config_loader import load_profile, ProfileConfig
from src.core.logger import logger

# Load environment variables (for API keys only)
load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="Run the RLM Agent on a task using YAML configuration profiles.",
        epilog="Example: uv run python src/main.py 'Calculate fibonacci(20)' --config configs/paper-gpt5.yaml"
    )
    parser.add_argument("task", help="The natural language task to perform.")
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to YAML configuration file (e.g., configs/paper-gpt5.yaml, configs/cost-effective.yaml)"
    )
    parser.add_argument(
        "--context",
        type=Path,
        default=None,
        help="Path to a directory containing files to include in the context."
    )

    args = parser.parse_args()

    # Load configuration profile
    try:
        logger.info(f"Loading configuration profile: {args.config}")
        config = load_profile(args.config)
        logger.info(f"Profile loaded: {config.profile_name}")
        if config.description:
            logger.info(f"Description: {config.description}")

        # Initialize budget manager from config
        BudgetManager._clear()  # Clear singleton for fresh start
        budget_manager = BudgetManager(max_budget=config.budget.max_usd)

        # Configure the root LM from profile
        lm = get_lm_for_role("root", config, budget_manager=budget_manager)
        dspy.settings.configure(lm=lm)

        logger.info(f"Root model: {config.root.provider}/{config.root.model}")
        logger.info(f"Delegate model: {config.delegate.provider}/{config.delegate.model}")
        logger.info(f"Budget limit: ${config.budget.max_usd:.2f}")
        logger.info(f"Max steps: {config.root.max_steps}, Max depth: {config.root.max_depth}")

    except FileNotFoundError as e:
        logger.error(f"Config file not found: {e}")
        logger.error(f"Available profiles in configs/: paper-gpt5.yaml, high-quality.yaml, cost-effective.yaml, hybrid.yaml, local-only.yaml")
        return
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return

    # Initialize Agent with config
    agent = RLMAgent(
        max_steps=config.root.max_steps,
        max_depth=config.root.max_depth,
        root_dir=args.context,
        config=config,
        budget_manager=budget_manager,
    )

    # Run Task
    logger.info(f"Starting Agent with task: '{args.task}'")
    result = agent.run(args.task)

    logger.info("\n" + "="*50)
    logger.info("FINAL RESULT:")
    logger.info(result)
    logger.info("="*50)

    # Print cost breakdown
    breakdown = budget_manager.get_breakdown()
    if breakdown:
        logger.info("\n" + "-"*50)
        logger.info("COST BREAKDOWN:")
        for model_id, cost in breakdown.items():
            logger.info(f"  {model_id}: ${cost:.4f}")
        logger.info(f"  TOTAL: ${budget_manager.current_cost:.4f}")
        logger.info("-"*50)

if __name__ == "__main__":
    main()
