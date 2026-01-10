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

    AVAILABLE GLOBALS (Paper-style Environment):
    - search_web(query) - Search the web
    - llm_query(question, context_chunk) - Ask LLM about a chunk (~500K char limit per call)
    - __artifacts_dir__ - Directory to save output files
    - __context_dir__ - Directory with input files
    - __execution_history__ - List of dicts: [{"step": 1, "code": "...", "output": "...", "output_length": 123}, ...]
    - __task__ - The original task string

    ACCESSING PREVIOUS RESULTS (MIT RLM Paper Pattern):
    The context_summary shows METADATA only. Access FULL content via __execution_history__:
        # Get all previous outputs
        for entry in __execution_history__:
            print(f"Step {entry['step']}: {entry['output'][:100]}...")

        # Analyze a large output with llm_query (chunking pattern)
        big_output = __execution_history__[-1]['output']
        chunk_size = 10000
        for i in range(0, len(big_output), chunk_size):
            chunk = big_output[i:i+chunk_size]
            result = llm_query("Extract key facts from this chunk", chunk)
            print(result)

    LARGE CONTEXT STRATEGY (from MIT RLM paper - handles 10M+ tokens):
    NEVER try to process huge strings directly. Use llm_query on chunks:
        # Bad: print(huge_text)  # Will overflow context
        # Good: Process in chunks
        results = []
        for i in range(0, len(huge_text), 50000):  # 50K char chunks
            chunk = huge_text[i:i+50000]
            summary = llm_query("Summarize key points", chunk)
            results.append(summary)
        final = llm_query("Combine these summaries into final answer", '\\n'.join(results))
        print(final)
    """
    task = dspy.InputField(desc="The task to solve using Python code.")
    context_summary = dspy.InputField(desc="Metadata about execution history (step count, output sizes). Use __execution_history__ in code for full content.", default="")
    python_code = dspy.OutputField(desc="ONLY executable Python code. No markdown, no comments explaining what you're about to do, no !pip commands.")

class Coder(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate_code = dspy.ChainOfThought(CoderSignature)

        # Add examples for file handling and paper-style patterns
        self.generate_code.demos = [
            # Basic file operations
            dspy.Example(
                task="Read the CSV file 'data/sales.csv' and show the first 5 rows",
                context_summary="AVAILABLE FILES: [FILE] data/sales.csv",
                python_code="import pandas as pd\ndf = pd.read_csv('data/sales.csv')\nprint(df.head())"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Create a bar chart of sales data and save it",
                context_summary="__artifacts_dir__ = 'runs/20260109_123456'",
                python_code="import matplotlib.pyplot as plt\n\ndata = {'Q1': 100, 'Q2': 150, 'Q3': 120, 'Q4': 180}\nplt.figure(figsize=(10, 6))\nplt.bar(data.keys(), data.values())\nplt.title('Quarterly Sales')\nplt.savefig(f'{__artifacts_dir__}/sales_chart.png')\nplt.close()\nprint('Chart saved')"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Search for latest AI news",
                context_summary="",
                python_code="results = search_web('latest AI news January 2026')\nfor r in results[:3]:\n    print(f\"- {r['title']}: {r['body'][:100]}...\")"
            ).with_inputs("task", "context_summary"),
            # Paper-style: Accessing __execution_history__
            dspy.Example(
                task="Analyze the search results from previous steps",
                context_summary="Execution History: 3 steps, 15000 chars total. Last output: search results...",
                python_code="# Access full content via __execution_history__ (paper pattern)\nfor entry in __execution_history__:\n    if 'search' in entry['code'].lower():\n        print(f\"Step {entry['step']} found {entry['output_length']} chars\")\n        # Analyze with llm_query for large outputs\n        summary = llm_query('Extract key findings', entry['output'][:10000])\n        print(f\"Key findings: {summary}\")"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Combine all findings from research into a final summary",
                context_summary="Execution History: 8 steps, 85000 chars total.",
                python_code="# Gather all outputs and summarize in chunks (paper pattern)\nall_content = '\\n\\n'.join(e['output'] for e in __execution_history__)\nchunk_size = 20000\nsummaries = []\nfor i in range(0, len(all_content), chunk_size):\n    chunk = all_content[i:i+chunk_size]\n    summary = llm_query('Summarize the key findings in this section', chunk)\n    summaries.append(summary)\n# Final aggregation\nfinal = llm_query(f'Combine these summaries into a comprehensive answer for: {__task__}', '\\n\\n'.join(summaries))\nprint(final)"
            ).with_inputs("task", "context_summary"),
            # Paper-style: Processing large documents in chunks
            dspy.Example(
                task="Extract all dates from the document",
                context_summary="Execution History: 1 step, 100000 chars. Last output: PDF text content...",
                python_code="# Get the large output from history\nbig_text = __execution_history__[-1]['output']\n\n# Process in chunks (paper pattern for 10M+ token handling)\nchunk_size = 15000\nall_dates = []\nfor i in range(0, len(big_text), chunk_size):\n    chunk = big_text[i:i+chunk_size]\n    dates = llm_query('List all dates mentioned in YYYY-MM-DD format', chunk)\n    if dates.strip():\n        all_dates.append(dates)\nprint('Found dates:')\nprint('\\n'.join(all_dates))"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Answer the original question using collected data",
                context_summary="Execution History: 5 steps, 45000 chars. Use __execution_history__ for full content.",
                python_code="# Build answer from execution history (paper pattern)\n# Collect relevant outputs\nrelevant_data = []\nfor entry in __execution_history__:\n    if entry['output_length'] > 100:  # Skip empty/error outputs\n        relevant_data.append(f\"Step {entry['step']}:\\n{entry['output'][:5000]}\")\n\n# Use llm_query to synthesize answer\ncontext = '\\n\\n---\\n\\n'.join(relevant_data)\nanswer = llm_query(f'Based on this research, answer: {__task__}', context[:50000])\nprint(answer)"
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
