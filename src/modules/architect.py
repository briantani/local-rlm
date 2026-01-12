import re

import dspy

from src.core.module_loader import load_compiled_module


class ArchitectSignature(dspy.Signature):
    """
    Decides the best action to take for a given query.

    You receive METADATA about execution history, not full content.
    Full content is accessible in code via __execution_history__ variable.

    Actions:
    1. 'CODE': For math, data processing, file reading, web search, visualizations, or to analyze data.
       Use llm_query() in code to analyze large chunks of data.
       Variables persist between CODE steps - use multiple CODE steps for complex tasks.
    2. 'ANSWER': ONLY when the answer is clearly visible in the last output preview,
       OR you have enough information from previous steps to formulate a complete response.

    IMPORTANT: If data_desc shows execution history but you need to PROCESS or ANALYZE
    the outputs (not just report them), choose CODE to work with __execution_history__.
    """
    query = dspy.InputField(desc="The user's query or task.")
    data_desc = dspy.InputField(desc="Metadata about execution history (step count, char totals) and last output preview. Full data accessible via __execution_history__ in code.", default="")
    action = dspy.OutputField(desc="Reply with exactly one word: ANSWER or CODE.")

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

        # Load compiled weights if available (using centralized loader)
        load_compiled_module(self, "architect")

    def forward(self, query: str, data_desc: str = "") -> dspy.Prediction:
        prediction = self.decide(query=query, data_desc=data_desc)

        # Normalize and extract action from potentially verbose output
        action = self._extract_action(prediction.action)

        # DSPy Assertion: Ensure action is one of the valid enums
        valid_actions = ["ANSWER", "CODE"]
        if action not in valid_actions:
            raise ValueError(f"Invalid action '{action}'. Must be one of {valid_actions}")

        return dspy.Prediction(action=action)

    def _extract_action(self, raw_action: str) -> str:
        """Extract a valid action from potentially verbose model output.

        Handles cases where the model outputs instructions or explanations
        instead of just the action word.

        Args:
            raw_action: The raw model output that may contain verbose text.

        Returns:
            One of "ANSWER" or "CODE". Defaults to "ANSWER" for
            ambiguous cases since the model has provided some response.
        """
        # Handle empty/whitespace input
        if not raw_action or not raw_action.strip():
            return "ANSWER"

        text = raw_action.upper().strip()

        # If it's already a clean action, return it
        valid_actions = ["ANSWER", "CODE"]
        if text in valid_actions:
            return text

        # Try to find a valid action word at the start (most common pattern)
        for action in valid_actions:
            if text.startswith(action):
                return action

        # Search for action words anywhere in the text using word boundaries
        found_actions = []
        for action in valid_actions:
            # Use word boundary matching to find complete words
            if re.search(rf'\b{action}\b', text):
                found_actions.append(action)

        if len(found_actions) == 1:
            return found_actions[0]
        elif len(found_actions) > 1:
            # Multiple actions found - prioritize based on position (first one wins)
            positions = {}
            for action in found_actions:
                match = re.search(rf'\b{action}\b', text)
                if match:
                    positions[action] = match.start()
            # Return the action that appears first
            return min(positions, key=positions.get)

        # No explicit action found - use heuristic keyword matching
        # Check for patterns indicating CODE
        code_keywords = ["CALCULATE", "COMPUTE", "PYTHON", "SCRIPT", "EXECUTE",
                        "RUN CODE", "PROGRAM", "ALGORITHM", "ANALYZE"]
        if any(word in text for word in code_keywords):
            return "CODE"

        # Check for patterns indicating ANSWER
        answer_keywords = ["EXPLAIN", "DESCRIBE", "SUMMARIZE", "THE ANSWER IS",
                          "RESPOND", "STRAIGHTFORWARD", "DIRECTLY"]
        if any(word in text for word in answer_keywords):
            return "ANSWER"

        # Default: if output contains steps/numbered instructions, it's trying to answer
        if re.search(r'^\d+\.', text) or "STEP" in text:
            return "ANSWER"

        # Final fallback: default to ANSWER for any unhandled case
        # This is safer than returning invalid text that will cause errors
        return "ANSWER"
