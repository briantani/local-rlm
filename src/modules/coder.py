import dspy
import ast

class CoderSignature(dspy.Signature):
    """
    Generates Python code to solve a specific task.
    The code should be a valid Python script that prints the final result to stdout.

    CRITICAL RULES:
    1. Do NOT use `import` statements - ALL modules are PRE-LOADED as globals.
    2. Do NOT use Jupyter syntax like `!pip install`. Only valid Python allowed.
    3. Do NOT use `subprocess`, `os.system`, or shell commands.
    4. Output ONLY executable Python code, no explanatory text.

    PRE-LOADED DATA SCIENCE MODULES (use directly, no import needed):
    - np / numpy - NumPy for numerical operations
    - pd / pandas - Pandas for data manipulation and analysis
    - plt / matplotlib - Matplotlib for plotting (use plt.savefig(), NOT plt.show())
    - sns / seaborn - Seaborn for statistical visualization
    - scipy / scipy_stats - SciPy for scientific computing and statistics
    - sklearn - Scikit-learn (LinearRegression, LogisticRegression, KMeans, StandardScaler, sklearn_metrics)
    - sm / statsmodels - Statsmodels for statistical analysis and regression

    PRE-LOADED DOCUMENT PROCESSING:
    - pdfplumber - Extract text and tables from PDFs: pdfplumber.open(path)
    - pypdf - PDF manipulation and reading
    - docx - Read/write Word documents: docx.Document(path)
    - openpyxl - Read/write Excel files (used by pandas for .xlsx)

    PRE-LOADED UTILITIES:
    - re - Regular expressions
    - json - JSON parsing
    - math - Math functions
    - datetime, timedelta - Date/time handling
    - Counter, defaultdict - Collection utilities
    - Path - pathlib.Path for file path handling
    - os.path.exists(), os.path.isfile(), os.path.join() - File path utilities
    - os.listdir() - List directory contents
    - StringIO, BytesIO - In-memory streams

    PRE-LOADED FUNCTIONS:
    - search_web(query) - Search the web and get results
    - llm_query(question, context_chunk) - Ask LLM about a chunk (~500K char limit per call)

    AVAILABLE VARIABLES:
    - output_dir - Directory to save output files (e.g., plt.savefig(f'{output_dir}/chart.png'))
    - input_dir - Directory with input files (from --context flag)
    - history - List of previous execution steps: [{"step": 1, "code": "...", "output": "...", "output_length": 123}, ...]
    - task - The original task string
    - context - Last execution output (shortcut for history[-1]['output'])

    IMPORTANT: Variables created in previous steps are available directly (shared state).
    If step 1 created 'df = pd.DataFrame(...)', step 2 can use 'df' directly without re-reading files.

    MATPLOTLIB/SEABORN USAGE:
    - Use `plt.savefig(f'{output_dir}/filename.png')` to save charts
    - Always call `plt.close()` after saving to free memory
    - Backend is 'Agg' (non-interactive, file-only)

    PANDAS/DATAFRAME TIPS:
    - Use `df.to_markdown()` to format DataFrames as markdown tables (tabulate is installed)
    - AVOID augmented assignment on DataFrame slices (e.g., `df.loc[...] *= 2`)
    - Instead use: `df['col'] = df['col'] * 2` or create new columns
    - Use `pd.concat()` instead of deprecated `df.append()`

    EXAMPLE - Data Analysis with Visualization:
        # Generate data
        data = pd.DataFrame({'x': np.random.randn(100), 'y': np.random.randn(100)})

        # Create visualization with seaborn
        plt.figure(figsize=(10, 6))
        sns.scatterplot(data=data, x='x', y='y')
        plt.title('Scatter Plot')
        plt.savefig(f'{output_dir}/scatter.png')
        plt.close()

        # Statistical analysis
        correlation = scipy_stats.pearsonr(data['x'], data['y'])
        print(f'Correlation: {correlation[0]:.3f}, p-value: {correlation[1]:.3f}')

    EXAMPLE - Machine Learning:
        # Simple linear regression
        X = np.array([[1], [2], [3], [4]])
        y = np.array([2, 4, 6, 8])
        model = LinearRegression()
        model.fit(X, y)
        print(f'Coefficient: {model.coef_[0]:.2f}, Intercept: {model.intercept_:.2f}')
    """
    task = dspy.InputField(desc="The task to solve using Python code.")
    context_summary = dspy.InputField(desc="Metadata about execution history (step count, output sizes). Use history variable in code for full content.", default="")
    python_code = dspy.OutputField(desc="ONLY executable Python code. No markdown, no import statements, no comments explaining what you're about to do, no !pip commands.")

class Coder(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate_code = dspy.ChainOfThought(CoderSignature)

        # Add examples for file handling and paper-style patterns
        # IMPORTANT: Use simple variable names (output_dir, history, task) not underscored versions
        # IMPORTANT: No import statements - modules are pre-loaded
        self.generate_code.demos = [
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
                python_code="data = {'Q1': 100, 'Q2': 150, 'Q3': 120, 'Q4': 180}\nplt.figure(figsize=(10, 6))\nplt.bar(data.keys(), data.values())\nplt.title('Quarterly Sales')\nplt.savefig(f'{output_dir}/sales_chart.png')\nplt.close()\nprint('Chart saved to output_dir')"
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

        return dspy.Prediction(python_code=code)

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
