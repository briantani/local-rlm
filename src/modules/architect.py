import re

import dspy

from src.core.module_loader import load_compiled_module


class ArchitectSignature(dspy.Signature):
    """
    decides the best action to take for a given query.
    1. 'CODE': For math, data processing, logic puzzles, or whenever the user asks for code/Python. CRITICAL: If the user asks about the *content* of a file listed in 'data_desc', you MUST choose 'CODE' to read it. You cannot know the content otherwise.
    2. 'ANSWER': For general knowledge, chit-chat, or IF the answer is EXPLICITLY visible in 'data_desc' (e.g. under "Output:"). Do NOT generate code if the output is already there.
    3. 'DELEGATE': Exclusively when the user's task explicitly asks to "run in parallel", "split the task", or "delegate", AND the subtasks have not been executed yet.
    """
    query = dspy.InputField(desc="The user's query or task.")
    data_desc = dspy.InputField(desc="Description of available data or context.", default="")
    action = dspy.OutputField(desc="Reply with exactly one word: ANSWER, CODE, or DELEGATE.")

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

    def _extract_action(self, raw_action: str) -> str:
        """Extract a valid action from potentially verbose model output.

        Handles cases where the model outputs instructions or explanations
        instead of just the action word.

        Args:
            raw_action: The raw model output that may contain verbose text.

        Returns:
            One of "ANSWER", "CODE", or "DELEGATE". Defaults to "ANSWER" for
            ambiguous cases since the model has provided some response.
        """
        # Handle empty/whitespace input
        if not raw_action or not raw_action.strip():
            return "ANSWER"

        text = raw_action.upper().strip()

        # If it's already a clean action, return it
        valid_actions = ["ANSWER", "CODE", "DELEGATE"]
        if text in valid_actions:
            return text

        # Try to find a valid action word at the start (most common pattern)
        for action in valid_actions:
            if text.startswith(action):
                return action

        # Search for action words anywhere in the text using word boundaries
        # Prioritize ANSWER > CODE > DELEGATE in case of multiple matches
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

        # Check for patterns indicating DELEGATE
        delegate_keywords = ["SPLIT", "PARALLEL", "SUBTASK", "BREAK DOWN",
                            "DIVIDE", "DIVIDED", "MULTIPLE TASKS", "DECOMPOSE"]
        if any(word in text for word in delegate_keywords):
            return "DELEGATE"

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
