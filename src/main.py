import argparse
import dspy
from dotenv import load_dotenv
from src.config import get_lm, get_config
from src.core.agent import RLMAgent
from src.core.logger import logger

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Run the RLM Agent on a task.")
    parser.add_argument("task", help="The natural language task to perform.")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "gemini", "openai"], help="LLM provider to use.")
    parser.add_argument("--model", default=None, help="Specific model name (e.g., 'qwen2.5-coder:14b', 'gemini-1.5-pro').")
    parser.add_argument("--context", default=None, help="Path to a directory containing files to include in the context.")
    parser.add_argument("--max-steps", type=int, default=None, help="Maximum steps per agent execution (overrides .env)")
    parser.add_argument("--max-depth", type=int, default=None, help="Maximum recursion depth (overrides .env)")

    args = parser.parse_args()

    # 1. Configure the LLM
    try:
        model_display = args.model if args.model else "default"
        logger.info(f"Initializing LLM provider: {args.provider} (Model: {model_display})...")
        lm = get_lm(args.provider, model_name=args.model)
        dspy.settings.configure(lm=lm)
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        return

    # 2. Load agent configuration from .env or use defaults/CLI args
    max_steps = args.max_steps if args.max_steps else get_config("MAX_AGENT_STEPS", 10, int)
    max_depth = args.max_depth if args.max_depth else get_config("MAX_RECURSION_DEPTH", 3, int)

    logger.info(f"Agent Configuration: max_steps={max_steps}, max_depth={max_depth}")

    # 3. Initialize Agent
    agent = RLMAgent(max_steps=max_steps, max_depth=max_depth, root_dir=args.context)

    # 3. Run Task
    logger.info(f"Starting Agent with task: '{args.task}'")
    result = agent.run(args.task)

    logger.info("\n" + "="*50)
    logger.info("FINAL RESULT:")
    logger.info(result)
    logger.info("="*50)

if __name__ == "__main__":
    main()
