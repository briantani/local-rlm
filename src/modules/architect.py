import dspy
from typing import Literal

class ArchitectSignature(dspy.Signature):
    """
    Decides the best action to take for a given query.
    1. 'CODE': For math, data processing, logic puzzles, or whenever the user asks for code/Python.
    2. 'ANSWER': For general knowledge, chit-chat, or IF the necessary information/result is already present in 'data_desc'.
    3. 'DELEGATE': For extremely large or parallelizable tasks.
    """
    query = dspy.InputField(desc="The user's query or task.")
    data_desc = dspy.InputField(desc="Description of available data or context.", default="")
    action = dspy.OutputField(desc="The best action to take: 'ANSWER', 'CODE', or 'DELEGATE'.")

class Architect(dspy.Module):
    def __init__(self):
        super().__init__()
        self.decide = dspy.ChainOfThought(ArchitectSignature)

        # Few-shot examples (for future compilation/optimization)
        self.examples = [
            dspy.Example(
                query="What is the capital of France?",
                data_desc="",
                action="ANSWER"
            ).with_inputs("query", "data_desc"),
            dspy.Example(
                query="Calculate the 100th Fibonacci number.",
                data_desc="",
                action="CODE"
            ).with_inputs("query", "data_desc"),
            dspy.Example(
                query="Calculate the sum of 1 to 50 using Python.",
                data_desc="",
                action="CODE"
            ).with_inputs("query", "data_desc"),
            dspy.Example(
                query="Calculate the sum of 1 to 50 using Python.",
                data_desc="Step 1 Output: 1275",
                action="ANSWER"
            ).with_inputs("query", "data_desc"),
            dspy.Example(
                query="Analyze this large dataset of sales figures.",
                data_desc="sales.csv with columns date, amount",
                action="CODE"
            ).with_inputs("query", "data_desc"),
             dspy.Example(
                query="Who won the super bowl in 2024?",
                data_desc="",
                action="DELEGATE" # Assuming DELEGATE implies search or external tool
            ).with_inputs("query", "data_desc")
        ]

    def forward(self, query: str, data_desc: str = "") -> dspy.Prediction:
        prediction = self.decide(query=query, data_desc=data_desc)

        # Normalize action
        action = prediction.action.upper().strip()

        # DSPy Assertion: Ensure action is one of the valid enums
        valid_actions = ["ANSWER", "CODE", "DELEGATE"]
        if action not in valid_actions:
            raise ValueError(f"Invalid action '{action}'. Must be one of {valid_actions}")

        return dspy.Prediction(action=action)
