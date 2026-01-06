import argparse
import dspy
from dotenv import load_dotenv
from src.config import get_lm
from src.core.agent import RLMAgent
from src.core.logger import logger

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Run the RLM Agent on a task.")
    parser.add_argument("task", help="The natural language task to perform.")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "gemini"], help="LLM provider to use.")
    parser.add_argument("--model", default=None, help="Specific model name (e.g., 'qwen2.5-coder:14b', 'gemini-1.5-pro').")
    parser.add_argument("--context", default=None, help="Path to a directory containing files to include in the context.")

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

    # 2. Initialize Agent
    agent = RLMAgent(max_steps=5, root_dir=args.context)

    # 3. Run Task
    logger.info(f"Starting Agent with task: '{args.task}'")
    result = agent.run(args.task)

    logger.info("\n" + "="*50)
    logger.info("FINAL RESULT:")
    logger.info(result)
    logger.info("="*50)

if __name__ == "__main__":
    main()
