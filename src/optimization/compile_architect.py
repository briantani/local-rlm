import dspy
import os
from dspy.teleprompt import BootstrapFewShot
from src.modules.architect import Architect, ArchitectSignature
from src.optimization.data import get_architect_data
from src.config import get_lm
from dotenv import load_dotenv

# Load env for LLM
load_dotenv()

def validate_action(example, prediction, trace=None):
    """
    Metric: Check if the predicted action exactly matches the expected label.
    """
    return example.action == prediction.action

def optimize_architect():
    print("Initializing LLM for optimization...")
    # Use a capable model for the teacher ideally, but we use what we have configured
    try:
        # Try to use a configured model if possible, or fall back to default
        lm = get_lm("ollama")
        dspy.settings.configure(lm=lm)
    except Exception as e:
        print(f"Error setting up LLM: {e}")
        return

    print("Loading training data...")
    trainset = get_architect_data()

    print("Setting up Teleprompter...")
    # BootstrapFewShot will generate rationales (ChainOfThought) for our examples
    # and select the best few-shot demos.
    teleprompter = BootstrapFewShot(metric=validate_action, max_bootstrapped_demos=4, max_labeled_demos=4)

    print("Compiling Architect...")
    architect = Architect()

    # Compile!
    compiled_architect = teleprompter.compile(architect, trainset=trainset)

    # Save
    save_path = "src/modules/compiled_architect.json"
    print(f"Saving compiled program to {save_path}...")
    compiled_architect.save(save_path)
    print("Done!")

if __name__ == "__main__":
    optimize_architect()
