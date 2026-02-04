"""
Validation metrics for DSPy optimization.

Consolidates metric functions that were duplicated across optimization scripts.
All metrics follow DSPy's signature: (example, prediction, trace=None) -> float
GEPA metrics return {"score": float, "feedback": str} instead.
"""

import re
from typing import Any, Callable

import dspy

from src.core.repl import PythonREPL


class ArchitectMetrics:
    """Metrics for validating Architect module outputs."""

    @staticmethod
    def validate_action(example: dspy.Example, prediction: Any, trace: Any = None) -> float:
        """
        Metric: Check if the predicted action exactly matches the expected label.

        Compatible with both BootstrapFewShot (prediction=Prediction) and SIMBA (prediction=dict).

        Args:
            example: Example with expected action
            prediction: Prediction object or dict with action field
            trace: Optional execution trace (unused)

        Returns:
            1.0 if exact match, 0.0 otherwise
        """
        # Handle both Prediction object and dict
        if isinstance(prediction, dict):
            predicted = prediction.get("action", "").upper().strip()
        else:
            predicted = prediction.action.upper().strip()

        expected = example.action.upper().strip()
        return 1.0 if predicted == expected else 0.0

    @staticmethod
    def validate_action_with_feedback(
        example: dspy.Example,
        prediction: Any,
        trace: Any = None,
        pred_name: Any = None,
        pred_trace: Any = None
    ) -> dict[str, Any]:
        """
        GEPA-compatible metric with textual feedback.

        Returns dict with score and feedback for GEPA's reflective optimization.

        Args:
            example: Example with expected action
            prediction: Prediction object or dict with action field
            trace: Optional execution trace
            pred_name: Optional predictor name (GEPA-specific)
            pred_trace: Optional prediction trace (GEPA-specific)

        Returns:
            Dict with "score" (float) and "feedback" (str)
        """
        # Handle both Prediction object and dict
        if isinstance(prediction, dict):
            predicted = prediction.get("action", "").upper().strip()
        else:
            predicted = prediction.action.upper().strip()

        expected = example.action.upper().strip()

        if predicted == expected:
            return {"score": 1.0, "feedback": f"Correct! Action '{predicted}' matches expected."}
        else:
            feedback = f"Incorrect. Expected '{expected}' but got '{predicted}'. "
            if expected == "ANSWER" and predicted == "CODE":
                feedback += "The output was already available in data_desc - no need for more code."
            elif expected == "CODE" and predicted == "ANSWER":
                feedback += "The task required computation or file reading - should have generated code."
            return {"score": 0.0, "feedback": feedback}

    @staticmethod
    def strict_action_metric(example: dspy.Example, prediction: Any, trace: Any = None) -> float:
        """
        Strict metric that only accepts exact action words.

        Scoring:
        - 1.0: Exact match (e.g., "ANSWER" == "ANSWER")
        - 0.5: Correct action but with extra text (e.g., "ANSWER: because..." contains "ANSWER")
        - 0.0: Wrong action or no valid action found

        This teaches the model to be concise.

        Args:
            example: Example with expected action
            prediction: Prediction object or dict
            trace: Optional trace

        Returns:
            Float score based on strictness criteria
        """
        valid_actions = {"ANSWER", "CODE"}
        expected = example.action.upper().strip()

        # Handle both Prediction object and dict
        if isinstance(prediction, dict):
            predicted_raw = prediction.get("action", "")
        else:
            predicted_raw = getattr(prediction, "action", "")

        predicted = predicted_raw.upper().strip()

        # Perfect match - exactly one word
        if predicted in valid_actions and predicted == expected:
            return 1.0

        # Check if the correct action is at the start
        if predicted.startswith(expected):
            # Penalize for extra content
            return 0.5

        # Check if action appears anywhere (very lenient)
        for action in valid_actions:
            if re.search(rf'\b{action}\b', predicted):
                if action == expected:
                    return 0.3  # Found it but with noise
                else:
                    return 0.0  # Wrong action

        # No valid action found at all
        return 0.0

    @staticmethod
    def format_strictness_metric(example: dspy.Example, prediction: Any, trace: Any = None) -> float:
        """
        Metric that heavily penalizes verbose outputs.

        Returns:
        - 1.0: Single word response matching action
        - 0.7: Correct action at start with minimal extra text
        - 0.3: Correct action buried in explanation
        - 0.0: Wrong or missing action

        Args:
            example: Example with expected action
            prediction: Prediction object or dict
            trace: Optional trace

        Returns:
            Float score based on format strictness
        """
        valid_actions = {"ANSWER", "CODE"}
        expected = example.action.upper().strip()

        if isinstance(prediction, dict):
            predicted_raw = prediction.get("action", "")
        else:
            predicted_raw = getattr(prediction, "action", "")

        predicted = predicted_raw.upper().strip()

        # Perfect: Single word
        if predicted in valid_actions:
            if predicted == expected:
                return 1.0
            else:
                return 0.0

        # Good: Starts with action
        if predicted.startswith(expected + " ") or predicted.startswith(expected + ":"):
            return 0.7

        # Acceptable: Contains action somewhere
        if re.search(rf'\b{expected}\b', predicted):
            return 0.3

        return 0.0


class CoderMetrics:
    """Metrics for validating Coder module outputs."""

    @staticmethod
    def _setup_test_globals(repl: PythonREPL) -> None:
        """
        Set up paper-style globals for code validation.

        Creates mock versions of execution history, llm_query, etc.
        so that code examples can execute during optimization.
        """
        # Mock execution history with sample data
        mock_history = [
            {
                "step": 1,
                "code": "results = search_web('AI research')",
                "output": "Found 5 articles about AI advancements...",
                "output_length": 500,
            },
            {
                "step": 2,
                "code": "print(len(results))",
                "output": "5",
                "output_length": 1,
            },
        ]

        # Set both underscore and simple alias versions
        repl.globals["__execution_history__"] = mock_history
        repl.globals["history"] = mock_history

        # Mock llm_query function
        def mock_llm_query(query: str, context: str = "") -> str:
            """Mock llm_query that returns a reasonable placeholder."""
            return f"[LLM Response to: {query[:50]}...]"

        repl.globals["llm_query"] = mock_llm_query

        # Task variable
        repl.globals["__task__"] = "Test task for optimization"
        repl.globals["task"] = "Test task for optimization"

        # Output directory
        repl.globals["__artifacts_dir__"] = "/tmp/test_artifacts"
        repl.globals["output_dir"] = "/tmp/test_artifacts"

        # Input/context directory
        repl.globals["__context_dir__"] = "/tmp/test_context"
        repl.globals["input_dir"] = "/tmp/test_context"

        # Context variable (empty by default)
        repl.globals["context"] = ""

    @staticmethod
    def validate_code_execution(example: dspy.Example, prediction: Any, trace: Any = None) -> float:
        """
        Metric: Validate that generated code executes successfully.

        Compatible with both BootstrapFewShot (prediction=Prediction) and SIMBA (prediction=dict).

        Scoring:
        - 0.0: Syntax error or execution error
        - 0.5: Executes but output doesn't match expected
        - 1.0: Executes and matches expected output (if provided)

        Args:
            example: Example with optional expected_output field
            prediction: Prediction object or dict with python_code field
            trace: Optional trace

        Returns:
            Float score based on execution result
        """
        repl = PythonREPL()
        CoderMetrics._setup_test_globals(repl)

        try:
            # Handle both Prediction object and dict
            if isinstance(prediction, dict):
                code = prediction.get("python_code", prediction.get("code", ""))
            else:
                code = prediction.python_code

            if not code:
                return 0.0

            output = repl.execute(code)

            # Check for errors
            if "Traceback" in output or "Error" in output:
                return 0.0

            # Check expected output if provided
            if hasattr(example, "expected_output") and example.expected_output:
                if example.expected_output in output:
                    return 1.0
                return 0.5  # Executed but wrong output

            return 1.0  # No expected output, execution success is enough

        except Exception:
            return 0.0

    @staticmethod
    def validate_code_with_feedback(
        example: dspy.Example,
        prediction: Any,
        trace: Any = None,
        pred_name: Any = None,
        pred_trace: Any = None
    ) -> dict[str, Any]:
        """
        GEPA-compatible metric with textual feedback.

        Returns dict with score and feedback for GEPA's reflective optimization.

        Args:
            example: Example with optional expected_output field
            prediction: Prediction object or dict with python_code field
            trace: Optional trace
            pred_name: Optional predictor name (GEPA-specific)
            pred_trace: Optional prediction trace (GEPA-specific)

        Returns:
            Dict with "score" (float) and "feedback" (str)
        """
        repl = PythonREPL()
        CoderMetrics._setup_test_globals(repl)

        try:
            # Handle both Prediction object and dict
            if isinstance(prediction, dict):
                code = prediction.get("python_code", prediction.get("code", ""))
            else:
                code = prediction.python_code

            if not code:
                return {
                    "score": 0.0,
                    "feedback": "No code generated"
                }

            output = repl.execute(code)

            if "Traceback" in output or "Error" in output:
                return {
                    "score": 0.0,
                    "feedback": f"Code execution failed with error: {output[:200]}"
                }

            if hasattr(example, "expected_output") and example.expected_output:
                if example.expected_output in output:
                    return {"score": 1.0, "feedback": "Code executed correctly with expected output."}
                return {
                    "score": 0.5,
                    "feedback": f"Code executed but output '{output[:100]}' doesn't contain expected '{example.expected_output}'"
                }

            return {"score": 1.0, "feedback": "Code executed successfully without errors."}

        except Exception as e:
            return {"score": 0.0, "feedback": f"Exception during execution: {str(e)}"}


def create_custom_metric(validation_fn: Callable) -> Callable:
    """
    Wrapper to create custom metrics with consistent signature.

    Args:
        validation_fn: Function that takes (example, prediction) and returns bool or float

    Returns:
        Metric function compatible with DSPy optimizers
    """
    def metric(example: dspy.Example, prediction: Any, trace: Any = None) -> float:
        """Generic metric wrapper."""
        result = validation_fn(example, prediction)
        return float(result) if isinstance(result, bool) else result

    return metric
