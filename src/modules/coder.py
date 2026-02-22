import dspy
import ast

class CoderSignature(dspy.Signature):
    """
    Generate Python code to solve the task. Print results to stdout.

    CRITICAL RESTRICTEDPYTHON RULES:
    - NO import statements (all pre-loaded: np, pd, plt, sns, re, json, math, datetime, Path)
    - NO .format() string method - use f-strings: f"{x}" not "{}".format(x)
    - NO underscore variables (__name__, __file__, __dict__)
    - NO getattr, setattr, eval, exec
    - NO open() for files (RestrictedPython). Use Path.read_text/write_text.
    - Use simple assignments: x = 5 (NOT complex attribute access)
    - NO line continuations with backslash inside f-strings or long expressions
      (Use parentheses instead: df['col'] = (condition1 and condition2))

    COMMON ERROR FIXES:
    ❌ "{}".format(x) -> ✅ f"{x}"
    ❌ import pandas -> ✅ pd (already available)
    ❌ df['col'] += 1 -> ✅ df['col'] = df['col'] + 1 (for complex cases)
    ❌ open('file.csv').read() -> ✅ Path(f"{input_dir}/file.csv").read_text()
    ❌ datetime.now() -> ✅ datetime.datetime.now() or pd.to_datetime(...)
    ❌ region_sales = \\
           df.groupby('Region')['Sales'].sum() -> ✅ use parentheses for line breaks
    ✅ region_sales = (
        df.groupby('Region')['Sales'].sum()
       )

    PRE-LOADED VARIABLES:
    - output_dir: Directory for saving output files (use this!)
    - input_dir: Directory containing input files from --context (use this!)
    - history: Execution history from previous steps
    - task: The original task description
    - context: Last output from previous steps

    IMPORTANT FOR FILE ACCESS:
    When reading files from context, ALWAYS use input_dir:
      ❌ pd.read_csv('sales_data.csv')  # FAILS - file not found
      ❌ pd.read_csv(f'{__context_dir__}/sales_data.csv')  # RestrictedPython blocks __ names
      ✅ pd.read_csv(f'{input_dir}/sales_data.csv')  # CORRECT

    When saving files to output, use output_dir:
      ✅ plt.savefig(f'{output_dir}/chart.png')
      ✅ df.to_csv(f'{output_dir}/results.csv')

    FUNCTIONS:
    - search_web(query) - Search the web
    - llm_query(question, text) - Ask LLM about text chunk
    - recursive_llm(sub_query, sub_context) - Spawn sub-agent for complex sub-tasks

    Variables from previous steps persist - reuse them directly.
    """
    task = dspy.InputField(desc="The task to solve with Python code.")
    context_summary = dspy.InputField(desc="Execution history metadata.", default="")
    python_code = dspy.OutputField(desc="Executable Python code only. No markdown, no imports.")
    # Optional: the coder can declare filenames it expects to generate.
    # Format as a comma-separated string or list in the prediction.
    expected_artifacts = dspy.OutputField(desc="Comma-separated filenames the code will generate (optional)", default="")

class Coder(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate_code = dspy.ChainOfThought(CoderSignature)

        # Add examples for file handling and paper-style patterns
        # IMPORTANT: Use simple variable names (output_dir, history, task) not underscored versions
        # IMPORTANT: No import statements - modules are pre-loaded
        # IMPORTANT: RestrictedPython-safe patterns (no .format(), use f-strings)
        self.generate_code.demos = [
            # RestrictedPython-safe string formatting - CRITICAL PATTERN
            dspy.Example(
                task="Generate a greeting message with the user's name",
                context_summary="user_name = 'Alice'",
                python_code="user_name = 'Alice'\n# Use f-strings (safe), NOT .format() (blocked)\nmessage = f'Hello, {user_name}! Welcome to RLM.'\nprint(message)"
            ).with_inputs("task", "context_summary"),
            # Basic file operations - NO IMPORTS needed
            # CRITICAL: Use input_dir (not __context_dir__) to read files!
            dspy.Example(
                task="Read the CSV file 'sales.csv' and show the first 5 rows",
                context_summary="AVAILABLE FILES: [FILE] sales_data.csv",
                python_code="# Use input_dir (no underscores) to read context files\ndf = pd.read_csv(f'{input_dir}/sales_data.csv')\nprint(df.head())"
            ).with_inputs("task", "context_summary"),
            # Chart creation - use output_dir, not __artifacts_dir__
            dspy.Example(
                task="Create a bar chart of sales data and save it",
                context_summary="output_dir = 'runs/20260109_123456'",
                python_code="data = {'Q1': 100, 'Q2': 150, 'Q3': 120, 'Q4': 180}\nplt.figure(figsize=(10, 6))\nplt.bar(data.keys(), data.values())\nplt.title('Quarterly Sales')\nplt.savefig(f'{output_dir}/sales_chart.png')\nplt.close()\nprint(f'Chart saved to {output_dir}/sales_chart.png')"
            ).with_inputs("task", "context_summary"),
            # Complete data analysis workflow with context + output
            dspy.Example(
                task="Analyze sales data from a CSV file in context folder and create visualizations",
                context_summary="AVAILABLE FILES: [FILE] sales_data.csv",
                python_code="# Step 1: Read data from input_dir (where context files are)\ndf = pd.read_csv(f'{input_dir}/sales_data.csv')\nprint(f'Loaded {len(df)} rows')\nprint(f'Columns: {list(df.columns)}')\n\n# Step 2: Find sales column (may have different names)\nsales_col = None\nfor col in df.columns:\n    if 'sales' in col.lower() or 'revenue' in col.lower() or 'amount' in col.lower():\n        sales_col = col\n        break\nif sales_col:\n    print(f'Found sales column: {sales_col}')\n    print(f'Total: {df[sales_col].sum()}')\nelse:\n    print('No sales column found. Available columns: ' + ', '.join(df.columns))\n\n# Step 3: Create visualization and save to output_dir\nplt.figure(figsize=(12, 6))\ndf.plot(kind='bar')\nplt.title('Sales Data')\nplt.tight_layout()\nplt.savefig(f'{output_dir}/sales_plot.png')\nplt.close()\nprint(f'Saved plot to {output_dir}/sales_plot.png')"
            ).with_inputs("task", "context_summary"),
            # DataFrame operations - safe assignment patterns
            dspy.Example(
                task="Calculate total sales from price and quantity columns",
                context_summary="DataFrame has 'price' and 'qty' columns",
                python_code="# Safe pattern: simple column assignment\ndf['total'] = df['price'] * df['qty']\nprint(f'Total sales: ${df[\"total\"].sum():.2f}')\nprint(df[['price', 'qty', 'total']].head())"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Search for latest AI news",
                context_summary="",
                python_code="results = search_web('latest AI news January 2026')\nfor r in results[:3]:\n    print(f\"- {r['title']}: {r['body'][:100]}...\")"
            ).with_inputs("task", "context_summary"),
            # Paper-style: Accessing history (simple alias)
            dspy.Example(
                task="Analyze the search results from previous steps",
                context_summary="Execution History: 3 steps, 15000 chars total. Last output: search results...",
                python_code="# Access full content via history variable\nfor entry in history:\n    if 'search' in entry['code'].lower():\n        print(f\"Step {entry['step']} found {entry['output_length']} chars\")\n        # Analyze with llm_query for large outputs\n        summary = llm_query('Extract key findings', entry['output'][:10000])\n        print(f\"Key findings: {summary}\")"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Combine all findings from research into a final summary",
                context_summary="Execution History: 8 steps, 85000 chars total.",
                python_code="# Gather all outputs and summarize in chunks\nall_content = '\\n\\n'.join(e['output'] for e in history)\nchunk_size = 20000\nsummaries = []\nfor i in range(0, len(all_content), chunk_size):\n    chunk = all_content[i:i+chunk_size]\n    summary = llm_query('Summarize the key findings in this section', chunk)\n    summaries.append(summary)\n# Final aggregation\nfinal = llm_query(f'Combine these summaries into a comprehensive answer for: {task}', '\\n\\n'.join(summaries))\nprint(final)"
            ).with_inputs("task", "context_summary"),
            # Data visualization - complete example
            dspy.Example(
                task="Create synthetic sales data and visualize it",
                context_summary="output_dir = 'runs/20260110_123456'",
                python_code="# Generate data with numpy\ndata = {'Q1': np.random.randint(100, 200), 'Q2': np.random.randint(150, 250), 'Q3': np.random.randint(120, 220), 'Q4': np.random.randint(180, 280)}\n\n# Create DataFrame\ndf = pd.DataFrame([data], index=['Sales ($K)'])\nprint(df.to_markdown())\n\n# Create and save chart\nplt.figure(figsize=(10, 6))\nplt.bar(data.keys(), data.values(), color='steelblue')\nplt.title('Quarterly Sales')\nplt.ylabel('Sales ($K)')\nplt.savefig(f'{output_dir}/sales_chart.png', dpi=100)\nplt.close()\nprint(f'Chart saved to {output_dir}/sales_chart.png')"
            ).with_inputs("task", "context_summary"),
            dspy.Example(
                task="Answer the original question using collected data",
                context_summary="Execution History: 5 steps, 45000 chars. Use history for full content.",
                python_code="# Build answer from execution history\nrelevant_data = []\nfor entry in history:\n    if entry['output_length'] > 100:  # Skip empty/error outputs\n        relevant_data.append(f\"Step {entry['step']}:\\n{entry['output'][:5000]}\")\n\n# Use llm_query to synthesize answer\ncontext = '\\n\\n---\\n\\n'.join(relevant_data)\nanswer = llm_query(f'Based on this research, answer: {task}', context[:50000])\nprint(answer)"
            ).with_inputs("task", "context_summary"),
            # BONUS: Comprehensive sales analysis with robust column detection
            dspy.Example(
                task="Create a thorough report with sales information",
                context_summary="AVAILABLE FILES: [FILE] sales_data.csv",
                python_code="import pandas as pd\nimport matplotlib.pyplot as plt\nfrom pathlib import Path\n\n# Load data\ndf = pd.read_csv(f'{input_dir}/sales_data.csv')\nprint(f'=== Data Loaded ===')\nprint(f'Rows: {len(df)}, Columns: {len(df.columns)}')\nprint(f'Column names: {list(df.columns)}')\n\n# Detect sales column - try common patterns (with/without underscore)\nsales_col = None\nfor candidate in ['Sales_Amount', 'sales_amount', 'Sales', 'sales', 'Revenue', 'revenue', 'Amount', 'amount']:\n    if candidate in df.columns:\n        sales_col = candidate\n        break\n\nif not sales_col:\n    # Fallback: any column with 'sales' or 'revenue'\n    for col in df.columns:\n        col_lower = col.lower()\n        if 'sale' in col_lower or 'revenue' in col_lower or 'amount' in col_lower:\n            sales_col = col\n            break\n\nif sales_col:\n    print(f'Sales column: {sales_col}')\n    print(f'Total Sales: ${df[sales_col].sum():,.2f}')\n    \n    # Create summary statistics\n    print(f'\\n=== Sales Summary ===')\n    print(f'Average: ${df[sales_col].mean():,.2f}')\n    print(f'Min: ${df[sales_col].min():,.2f}')\n    print(f'Max: ${df[sales_col].max():,.2f}')\n    \n    # Save results\n    summary = f'''Sales Report\n=============\nTotal Sales: ${df[sales_col].sum():,.2f}\nAverage Sale: ${df[sales_col].mean():,.2f}\nNumber of Records: {len(df)}\n'''\n    Path(f'{output_dir}/sales_summary.txt').write_text(summary)\n    print(f'\\nReport saved to {output_dir}/sales_summary.txt')\nelse:\n    print('ERROR: Could not find sales column. Available columns:')\n    print(', '.join(df.columns))"
            ).with_inputs("task", "context_summary"),
        ]

    def forward(self, task: str, context_summary: str = "") -> dspy.Prediction:
        # Generate code
        prediction = self.generate_code(task=task, context_summary=context_summary)
        code = prediction.python_code

        if not isinstance(code, str):
            raise ValueError("Generated code is empty or not a string.")

        # Clean up markdown code blocks if present (common LLM behavior)
        if code.startswith("```python"):
            code = code.replace("```python", "", 1)
        if code.startswith("```"):
            code = code.replace("```", "", 1)
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]

        code = code.strip()

        # Strip import statements (modules are pre-loaded in REPL)
        # This handles models that insist on writing imports despite instructions
        code = self._strip_imports(code)

        # DSPy Assertion: Verify that the generated code is valid Python syntax
        # If ast.parse fails, DSPy will backtrack and retry with the error message
        try:
            ast.parse(code)
        except SyntaxError as e:
            # This assertion failure triggers a retry
            raise ValueError(f"Generated code has syntax error: {e}. Code was:\n{code}")

        # Parse special inline annotation for expected artifacts, e.g.
        #  # EXPECTED_ARTIFACTS: sales_chart.png, data.csv
        expected = ""
        for line in code.splitlines():
            line = line.strip()
            if line.upper().startswith("# EXPECTED_ARTIFACTS:"):
                expected = line.split(":", 1)[1].strip()
                break

        pred = dspy.Prediction(python_code=code)
        if expected:
            # Normalize to list-like string or list depending on dspy expectations
            pred.expected_artifacts = [p.strip() for p in expected.split(",") if p.strip()]
        else:
            pred.expected_artifacts = []

        return pred

    def _strip_imports(self, code: str) -> str:
        """Remove import statements from generated code.

        Pre-loaded modules in REPL: np, numpy, pd, pandas, plt, matplotlib,
        re, json, math, datetime, timedelta, Counter, defaultdict.

        This handles LLMs that insist on writing imports despite DSPy instructions.
        """
        lines = code.split('\n')
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip import and from...import statements
            if stripped.startswith('import ') or stripped.startswith('from '):
                continue
            filtered_lines.append(line)

        # Remove leading blank lines that might result from stripping
        while filtered_lines and not filtered_lines[0].strip():
            filtered_lines.pop(0)

        return '\n'.join(filtered_lines)
