import dspy
import ast

class CoderSignature(dspy.Signature):
    """
    Generates Python code to solve a specific task.
    The code should be a valid Python script that prints the final result to stdout.
    IMPORTANT:
    - To search the web, you MUST import `src.tools.search` and use `search_web(query)`.
    - Do NOT use `requests` or `BeautifulSoup` directly.
    """
    task = dspy.InputField(desc="The task to solve using Python code.")
    context_summary = dspy.InputField(desc="Summary of previous context or variables available.", default="")
    python_code = dspy.OutputField(desc="Executable Python code. Do not use markdown backticks. Prefer using installed tools like src.tools.search.")

class Coder(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate_code = dspy.ChainOfThought(CoderSignature)

        # Add examples for file handling
        self.generate_code.demos = [
             dspy.Example(
                task="Read the CSV file 'data/sales.csv' and show the first 5 rows",
                context_summary="AVAILABLE FILES: [FILE] data/sales.csv",
                python_code="import pandas as pd\ndf = pd.read_csv('data/sales.csv')\nprint(df.head())"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="What is the text in 'document.pdf'?",
                context_summary="AVAILABLE FILES: [FILE] document.pdf",
                python_code="from pypdf import PdfReader\nreader = PdfReader('document.pdf')\ntext = ''\nfor page in reader.pages:\n    text += page.extract_text()\nprint(text[:500])"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Extract the first table from 'report.pdf'.",
                context_summary="AVAILABLE FILES: [FILE] report.pdf",
                python_code="import pdfplumber\nwith pdfplumber.open('report.pdf') as pdf:\n    page = pdf.pages[0]\n    table = page.extract_table()\n    print(table)"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Check the formula in cell E5 of 'dataset.xlsx'.",
                context_summary="AVAILABLE FILES: [FILE] dataset.xlsx",
                python_code="import openpyxl\nwb = openpyxl.load_workbook('dataset.xlsx', data_only=False)\nws = wb.active\nprint(f'Formula in E5: {ws[\"E5\"].value}')"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Google who won the 2024 Super Bowl.",
                context_summary="",
                python_code="from src.tools.search import search_web\nresults = search_web('2024 Super Bowl winner')\nprint(results)"
            ).with_inputs("task", "context_summary")
        ]

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
