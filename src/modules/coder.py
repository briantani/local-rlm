import dspy
import ast

class CoderSignature(dspy.Signature):
    """
    Generates Python code to solve a specific task.
    The code should be a valid Python script that prints the final result to stdout.
    """
    task = dspy.InputField(desc="The task to solve using Python code.")
    context_summary = dspy.InputField(desc="Summary of previous context or variables available.", default="")
    python_code = dspy.OutputField(desc="Executable Python code. Do not use markdown backticks.")

class Coder(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate_code = dspy.ChainOfThought(CoderSignature)

    def forward(self, task: str, context_summary: str = "") -> dspy.Prediction:
        # Generate code
        prediction = self.generate_code(task=task, context_summary=context_summary)
        code = prediction.python_code

        # Clean up markdown code blocks if present (common LLM behavior)
        if code.startswith("```python"):
            code = code.replace("```python", "", 1)
        if code.startswith("```"):
            code = code.replace("```", "", 1)
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]

        code = code.strip()

        # DSPy Assertion: Verify that the generated code is valid Python syntax
        # If ast.parse fails, DSPy will backtrack and retry with the error message
        try:
            ast.parse(code)
        except SyntaxError as e:
            # This assertion failure triggers a retry
            raise ValueError(f"Generated code has syntax error: {e}. Code was:\n{code}")

        return dspy.Prediction(python_code=code)
