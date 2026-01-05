import dspy
import os
from typing import Literal

class ArchitectSignature(dspy.Signature):
    """
    decides the best action to take for a given query.
    1. 'CODE': For math, data processing, logic puzzles, or whenever the user asks for code/Python. CRITICAL: If the user asks about the *content* of a file listed in 'data_desc', you MUST choose 'CODE' to read it. You cannot know the content otherwise.
    2. 'ANSWER': For general knowledge, chit-chat, or IF the answer is EXPLICITLY visible in 'data_desc' (e.g. under "Output:"). Do NOT generate code if the output is already there.
    3. 'DELEGATE': Exclusively when the user's task explicitly asks to "run in parallel", "split the task", or "delegate", AND the subtasks have not been executed yet.
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
        ]

        # Load compiled weights if available
        compiled_path = os.path.join(os.path.dirname(__file__), "compiled_architect.json")
        if os.path.exists(compiled_path):
            # print(f"Loading optimized Architect from {compiled_path}")
            self.load(compiled_path)

    def forward(self, query: str, data_desc: str = "") -> dspy.Prediction:
        prediction = self.decide(query=query, data_desc=data_desc)

        # Normalize action
        action = prediction.action.upper().strip()

        # HEURISTIC OVERRIDE (Temporary Fix for Loop):
        # If the Architect keeps modifying code but result is static, it's stuck.
        # But more simply: If data_desc contains "Output:" and the query is simple,
        # it might be time to ANSWER.
        # However, let's rely on the prompt. If the prompt fails, we debug the prompt.

        # Forced loop break for file reading task:
        if "Output:" in data_desc and "README.md" in query and action == "CODE":
             # Debugging:
             # print(f"DEBUG: Context has output, but action is still CODE. Rationale: {prediction.rationale}")
             pass

        # DSPy Assertion: Ensure action is one of the valid enums
        valid_actions = ["ANSWER", "CODE", "DELEGATE"]
        if action not in valid_actions:
            raise ValueError(f"Invalid action '{action}'. Must be one of {valid_actions}")

        return dspy.Prediction(action=action)
