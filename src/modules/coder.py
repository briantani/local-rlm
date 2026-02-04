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
    - Use simple assignments: x = 5 (NOT complex attribute access)

    COMMON ERROR FIXES:
    ❌ "{}".format(x) -> ✅ f"{x}"
    ❌ import pandas -> ✅ pd (already available)
    ❌ df['col'] += 1 -> ✅ df['col'] = df['col'] + 1 (for complex cases)

    VARIABLES: output_dir, input_dir, history, task, context

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
            dspy.Example(
                task="Read the CSV file 'data/sales.csv' and show the first 5 rows",
                context_summary="AVAILABLE FILES: [FILE] data/sales.csv",
                python_code="df = pd.read_csv('data/sales.csv')\nprint(df.head())"
            ).with_inputs("task", "context_summary"),
            # Chart creation - use output_dir, not __artifacts_dir__
            dspy.Example(
                task="Create a bar chart of sales data and save it",
                context_summary="output_dir = 'runs/20260109_123456'",
                python_code="data = {'Q1': 100, 'Q2': 150, 'Q3': 120, 'Q4': 180}\nplt.figure(figsize=(10, 6))\nplt.bar(data.keys(), data.values())\nplt.title('Quarterly Sales')\nplt.savefig(f'{output_dir}/sales_chart.png')\nplt.close()\nprint(f'Chart saved to {output_dir}/sales_chart.png')"
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
