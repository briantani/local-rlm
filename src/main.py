"""
RLM Agent CLI Entry Point.

This module provides the command-line interface for the RLM Agent.
It uses the service layer (Phase 12) for all business logic.
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.core.logger import logger
import logging
from src.rlm.services import ConfigService, SessionService, TaskService

# Load environment variables (for API keys)
load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Run the RLM Agent on a task using YAML configuration profiles.",
        epilog=(
            "Examples:\n"
            "  uv run python src/main.py 'Calculate fibonacci(20)' --config configs/paper-gpt5.yaml\n"
            "  uv run python src/main.py --prompt-file tasks/research.txt --config configs/high-quality.yaml"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Make task and prompt-file mutually exclusive
    task_group = parser.add_mutually_exclusive_group(required=True)
    task_group.add_argument(
        "task",
        nargs="?",
        help="The natural language task to perform (or use --prompt-file for longer tasks)."
    )
    task_group.add_argument(
        "--prompt-file",
        type=Path,
        help="Path to a text file containing the task description (for verbose/complex prompts)."
    )

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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed execution logs (DEBUG level)"
    )

    args = parser.parse_args()

    # Read task from file if --prompt-file is provided
    if args.prompt_file:
        try:
            task = args.prompt_file.read_text(encoding="utf-8").strip()
            if not task:
                logger.error(f"Prompt file is empty: {args.prompt_file}")
                return
            logger.info(f"Loaded task from: {args.prompt_file}")
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {args.prompt_file}")
            return
        except Exception as e:
            logger.error(f"Failed to read prompt file: {e}")
            return
    else:
        task = args.task

    # Configure logger based on verbose flag
    if args.verbose:
        logger.set_level(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    else:
        logger.set_level(logging.INFO)

    # Initialize services (Phase 12 pattern)
    config_service = ConfigService()
    session_service = SessionService()

    # Create session and load API keys from environment
    session = session_service.create_session()

    # Load API keys from environment into session
    if os.getenv("GEMINI_API_KEY"):
        session.set_api_key("gemini", os.getenv("GEMINI_API_KEY"))
    if os.getenv("OPENAI_API_KEY"):
        session.set_api_key("openai", os.getenv("OPENAI_API_KEY"))
    if os.getenv("ANTHROPIC_API_KEY"):
        session.set_api_key("anthropic", os.getenv("ANTHROPIC_API_KEY"))

    # Create task service with session
    task_service = TaskService(config_service, session)

    # Determine config name from path
    config_name = str(args.config)

    # Log configuration info
    try:
        summary = config_service.get_profile_summary(args.config.stem)
        if summary:
            logger.info(f"Profile: {summary.name}")
            if summary.description:
                logger.info(f"Description: {summary.description}")
            logger.info(f"Root model: {summary.root_provider}/{summary.root_model}")
            logger.info(f"Delegate model: {summary.delegate_provider}/{summary.delegate_model}")
            logger.info(f"Budget limit: ${summary.max_budget:.2f}")
            logger.info(f"Max steps: {summary.max_steps}, Max depth: {summary.max_depth}")
    except Exception as e:
        logger.debug(f"Could not get profile summary: {e}")

    # Run task using service
    try:
        logger.info(f"Starting Agent with task: '{task[:100]}{'...' if len(task) > 100 else ''}'")

        # Define step callback for logging
        def on_step(step_info):
            logger.debug(f"Step {step_info.step_number}: {step_info.action}")

        result = task_service.run_task(
            task=task,
            config_name=config_name,
            context_path=args.context,
            on_step=on_step,
        )

        # Print results
        print("\n" + "="*60)
        print("FINAL RESULT")
        print("="*60)
        print(result.answer)
        print("="*60)

        # Print artifacts info
        if result.artifacts_folder:
            print(f"\n📁 Artifacts: {result.artifacts_folder}")
            if result.generated_images:
                print(f"   🖼️  Images: {len(result.generated_images)}")
                for img in result.generated_images:
                    print(f"      - {img['filename']}")
            print(f"   📄 Report: {result.artifacts_folder / 'report.md'}")

        # Print cost breakdown
        if result.model_breakdown:
            print("\n" + "-"*60)
            print("COST BREAKDOWN")
            print("-"*60)
            for model_id, cost in result.model_breakdown.items():
                print(f"  {model_id}: ${cost:.4f}")
            print(f"\n  TOTAL: ${result.total_cost:.4f}")
            print(f"  Duration: {result.duration_seconds:.2f}s")
            print(f"  Steps: {result.step_count}")
            print("-"*60)

    except FileNotFoundError as e:
        logger.error(f"Config file not found: {e}")
        logger.error("Available profiles in configs/: " +
                    ", ".join(config_service.get_profile_names()))
        return
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        raise

if __name__ == "__main__":
    main()