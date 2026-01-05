import argparse
import dspy
import os
from dotenv import load_dotenv
from src.config import get_lm
from src.core.agent import RLMAgent

# Load environment variables
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Run the RLM Agent on a task.")
    parser.add_argument("task", help="The natural language task to perform.")
    parser.add_argument("--provider", default="ollama", choices=["ollama", "gemini"], help="LLM provider to use.")

    args = parser.parse_args()

    # 1. Configure the LLM
    try:
        print(f"Initializing LLM provider: {args.provider}...")
        lm = get_lm(args.provider)
        dspy.settings.configure(lm=lm)
    except Exception as e:
        print(f"Failed to initialize LLM: {e}")
        return

    # 2. Initialize Agent
    agent = RLMAgent(max_steps=5)

    # 3. Run Task
    print(f"Starting Agent with task: '{args.task}'")
    result = agent.run(args.task)

    print("\n" + "="*50)
    print("FINAL RESULT:")
    print(result)
    print("="*50)

if __name__ == "__main__":
    main()
