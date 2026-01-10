import dspy
import ast

class CoderSignature(dspy.Signature):
    """
    Generates Python code to solve a specific task.
    The code should be a valid Python script that prints the final result to stdout.

    CRITICAL RULES:
    1. `search_web(query)` is PRE-LOADED. Do NOT import it. Just call it directly.
    2. `llm_query(question, context)` is PRE-LOADED for recursive LLM calls on chunks.
    3. Do NOT use Jupyter syntax like `!pip install`. Only valid Python allowed.
    4. Do NOT use `subprocess`, `os.system`, or shell commands.
    5. Do NOT use `requests` or `BeautifulSoup` directly - use search_web instead.
    6. Output ONLY executable Python code, no explanatory text.

    AVAILABLE GLOBALS:
    - search_web(query) - Search the web
    - llm_query(question, context_chunk) - Ask LLM about a chunk of text
    - __artifacts_dir__ - Directory to save output files
    - __context_dir__ - Directory with input files
    - __execution_history__ - List of previous execution steps (code, output)
    - __task__ - The original task string

    LARGE CONTEXT STRATEGY (from MIT RLM paper):
    When dealing with large data, use llm_query to process chunks:
        # Process chunks and aggregate
        results = []
        for chunk in large_text.split('\\n\\n'):
            summary = llm_query("Summarize key points", chunk)
            results.append(summary)
        print("\\n".join(results))
    """
    task = dspy.InputField(desc="The task to solve using Python code.")
    context_summary = dspy.InputField(desc="Summary of previous context or variables available.", default="")
    python_code = dspy.OutputField(desc="ONLY executable Python code. No markdown, no comments explaining what you're about to do, no !pip commands.")

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
                python_code="results = search_web('2024 Super Bowl winner')\nprint(results)"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Create a bar chart of sales data and save it",
                context_summary="__artifacts_dir__ = 'runs/20260109_123456'",
                python_code="import matplotlib.pyplot as plt\n\ndata = {'Q1': 100, 'Q2': 150, 'Q3': 120, 'Q4': 180}\nplt.figure(figsize=(10, 6))\nplt.bar(data.keys(), data.values())\nplt.title('Quarterly Sales')\nplt.savefig(f'{__artifacts_dir__}/sales_chart.png')\nplt.close()\nprint('Chart saved')"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Search for latest AI news and summarize",
                context_summary="",
                python_code="results = search_web('latest AI news January 2026')\nfor r in results[:3]:\n    print(f\"- {r['title']}: {r['body'][:100]}...\")"
            ).with_inputs("task", "context_summary"),
            # Paper-inspired: llm_query for processing chunks
            dspy.Example(
                task="Summarize each section of the document",
                context_summary="large_text variable has 50000 characters of document content",
                python_code="sections = large_text.split('\\n\\n')\nsummaries = []\nfor i, section in enumerate(sections[:10]):\n    summary = llm_query(f'Summarize section {i+1}', section)\n    summaries.append(f'Section {i+1}: {summary}')\nprint('\\n'.join(summaries))"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Extract all dates mentioned in the research papers",
                context_summary="papers_text contains 100000 chars of research paper text",
                python_code="# Process in chunks to avoid context overflow\nchunk_size = 10000\nall_dates = []\nfor i in range(0, len(papers_text), chunk_size):\n    chunk = papers_text[i:i+chunk_size]\n    dates = llm_query('List all dates mentioned (YYYY-MM-DD format)', chunk)\n    all_dates.append(dates)\nprint('Found dates:\\n' + '\\n'.join(all_dates))"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Classify each entry in the data",
                context_summary="entries is a list of 1000 text entries to classify",
                python_code="# Batch classify entries using llm_query\nclassifications = []\nfor entry in entries[:20]:  # Process first 20\n    label = llm_query('Classify as: positive, negative, or neutral', entry)\n    classifications.append({'text': entry[:50], 'label': label})\nfor c in classifications:\n    print(f\"{c['label']}: {c['text']}...\")"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Aggregate findings from execution history",
                context_summary="Multiple search results in __execution_history__",
                python_code="# Access previous execution results\nfindings = []\nfor entry in __execution_history__:\n    if 'search' in entry['code'].lower():\n        finding = llm_query('Extract key facts', entry['output'])\n        findings.append(finding)\nprint('Aggregated findings:')\nfor f in findings:\n    print(f'- {f}')"
            ).with_inputs("task", "context_summary"),
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
