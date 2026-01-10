"""
Training data for DSPy module optimization.

Best Practices for DSPy Training Examples:
==========================================
1. DIVERSITY: Cover edge cases, not just happy paths. Include examples that
   represent different decision boundaries (e.g., when to CODE vs ANSWER).

2. CONTRASTIVE PAIRS: Include pairs that show the same query with different
   contexts leading to different outputs. This teaches the model decision logic.

3. REALISTIC CONTEXT: Use `data_desc` that mirrors actual runtime state.
   **IMPORTANT (Paper-Style)**: data_desc contains METADATA only, not full content.
   - Step count and char totals
   - Last output preview (truncated)
   - Full content is accessed via __execution_history__ in code

4. MINIMUM SIZE:
   - LabeledFewShot: 5-10 examples (just uses them as demos)
   - BootstrapFewShot: 10-20 examples (validates with metric)
   - MIPROv2: 50+ examples for instruction optimization, 200+ for full runs

5. INPUT MARKERS: Always call `.with_inputs()` to specify which fields are inputs.
   This is REQUIRED for optimization to work correctly.

6. VALIDATION SET: For MIPROv2, split data into trainset (70%) and valset (30%).
   The optimizer uses valset to prevent overfitting.

MIT RLM Paper Context Handling:
==============================
The key insight from arXiv:2512.24601v1 is that "long prompts should not be fed
into the neural network directly but should instead be treated as part of the
environment." This means:

- Architect receives METADATA (step count, char totals), not full content
- Coder accesses full content via __execution_history__ in generated code
- Large outputs are processed with llm_query() in chunks
"""

import dspy


def get_architect_data() -> list[dspy.Example]:
    """
    Returns training examples for the Architect module.

    The Architect decides: ANSWER, CODE, or DELEGATE.
    Examples are organized as contrastive pairs to teach decision boundaries.

    IMPORTANT: data_desc uses paper-style METADATA format, not full content.
    Full execution history is available via __execution_history__ in code.

    Returns:
        List of dspy.Example objects with query, data_desc, and action fields.
    """
    dataset = [
        # =====================================================================
        # PAIR 1: Simple Math - CODE vs ANSWER
        # =====================================================================
        # Before execution: Need to compute
        dspy.Example(
            query="What is 2 + 2?",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="CODE"
        ).with_inputs("query", "data_desc"),

        # After execution: Result available, now ANSWER
        dspy.Example(
            query="What is 2 + 2?",
            data_desc="Execution History: 1 step, 25 chars total.\nLast output (10 chars): 4",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # PAIR 2: File Reading - CODE vs ANSWER
        # =====================================================================
        # File exists but not read yet
        dspy.Example(
            query="What is the first line of test.txt?",
            data_desc="AVAILABLE FILES:\n[FILE] test.txt\nExecution History: 0 steps. No code executed yet.",
            action="CODE"
        ).with_inputs("query", "data_desc"),

        # File has been read, content in history
        dspy.Example(
            query="What is the first line of test.txt?",
            data_desc="AVAILABLE FILES:\n[FILE] test.txt\nExecution History: 1 step, 150 chars total.\nLast output (15 chars): # Hello World...",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # PAIR 3: Data Analysis - CODE vs ANSWER
        # =====================================================================
        # CSV exists, need to analyze
        dspy.Example(
            query="What is the average sales in sales.csv?",
            data_desc="AVAILABLE FILES:\n[FILE] sales.csv\nExecution History: 0 steps. No code executed yet.",
            action="CODE"
        ).with_inputs("query", "data_desc"),

        # Analysis complete
        dspy.Example(
            query="What is the average sales in sales.csv?",
            data_desc="AVAILABLE FILES:\n[FILE] sales.csv\nExecution History: 1 step, 200 chars total.\nLast output (25 chars): Average sales: 1523.45",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # PAIR 4: Delegation - DELEGATE vs ANSWER
        # =====================================================================
        # Explicit parallel request
        dspy.Example(
            query="Process these 5 items in parallel.",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="DELEGATE"
        ).with_inputs("query", "data_desc"),

        # Delegation complete
        dspy.Example(
            query="Process these 5 items in parallel.",
            data_desc="Execution History: 1 step, 5000 chars total.\nLast output (500 chars, truncated): Results from sub-agents:\nItem 1: Done\nItem 2: Done...",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # PURE ANSWER CASES (No computation needed)
        # =====================================================================
        # General knowledge - no code needed
        dspy.Example(
            query="What is the capital of France?",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # Greeting/chitchat
        dspy.Example(
            query="Hello, how are you?",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # Explain a concept
        dspy.Example(
            query="What is recursion in programming?",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Error Recovery
        # =====================================================================
        # Code failed, need to retry with different approach
        dspy.Example(
            query="Read the Excel file report.xlsx",
            data_desc="AVAILABLE FILES:\n[FILE] report.xlsx\nExecution History: 1 step, 350 chars total.\nLast output (100 chars, truncated): Traceback: ModuleNotFoundError: No module named 'openpyxl'...",
            action="CODE"  # Should try again with openpyxl import
        ).with_inputs("query", "data_desc"),

        # Successful retry
        dspy.Example(
            query="Read the Excel file report.xlsx",
            data_desc="AVAILABLE FILES:\n[FILE] report.xlsx\nExecution History: 2 steps, 500 chars total.\nLast output (50 chars): ['Sheet1', 'Summary']",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Web Search
        # =====================================================================
        # Need current information
        dspy.Example(
            query="What is the current price of Bitcoin?",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="CODE"  # Needs web search tool
        ).with_inputs("query", "data_desc"),

        # Search complete
        dspy.Example(
            query="What is the current price of Bitcoin?",
            data_desc="Execution History: 1 step, 800 chars total.\nLast output (100 chars, truncated): Bitcoin is trading at $98,432 as of January 6, 2026...",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Complex Multi-Step (Paper-style large context)
        # =====================================================================
        # Multi-step task, first step done
        dspy.Example(
            query="Load data.csv, calculate the mean, and plot a histogram",
            data_desc="AVAILABLE FILES:\n[FILE] data.csv\nExecution History: 1 step, 500 chars total.\nLast output (100 chars, truncated): Loaded DataFrame with 1000 rows...",
            action="CODE"  # Still need to calculate mean and plot
        ).with_inputs("query", "data_desc"),

        # All steps complete
        dspy.Example(
            query="Load data.csv, calculate the mean, and plot a histogram",
            data_desc="AVAILABLE FILES:\n[FILE] data.csv\nExecution History: 2 steps, 1200 chars total.\nLast output (50 chars): Mean: 15.0, Saved histogram.png",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # PAPER-STYLE: Large Context Scenarios
        # These teach the model that metadata means content exists but isn't shown
        # =====================================================================
        # Large search results collected, need to analyze
        dspy.Example(
            query="Summarize the AI research findings",
            data_desc="Execution History: 5 steps, 85000 chars total.\nLast output (500 chars, truncated): [Search results about AI research...]...\n[Use __execution_history__ for full content]",
            action="CODE"  # Should use llm_query on chunks from __execution_history__
        ).with_inputs("query", "data_desc"),

        # Analysis complete
        dspy.Example(
            query="Summarize the AI research findings",
            data_desc="Execution History: 8 steps, 95000 chars total.\nLast output (300 chars): Final Summary: AI has advanced significantly...",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # Multiple documents processed
        dspy.Example(
            query="Extract key dates from all documents",
            data_desc="Execution History: 10 steps, 150000 chars total.\nLast output (200 chars, truncated): Processed 5 documents, extracted 47 dates...",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Empty/No Output
        # =====================================================================
        # Code ran but no output (might need to check result)
        dspy.Example(
            query="Save the data to output.csv",
            data_desc="Execution History: 1 step, 100 chars total.\nLast output (0 chars): [empty]",
            action="ANSWER"  # Empty output is fine for file save operations
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: SecurityError
        # =====================================================================
        # Code was blocked by REPL security
        dspy.Example(
            query="Run a shell command to list files",
            data_desc="Execution History: 1 step, 200 chars total.\nLast output (60 chars): SecurityError: Forbidden module or function usage.",
            action="ANSWER"  # Should explain the security restriction
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Ambiguous Queries
        # =====================================================================
        # User asks about code but doesn't need it run
        dspy.Example(
            query="How do I read a CSV file in Python?",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="ANSWER"  # This is a knowledge question, not execution
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Image Generation
        # =====================================================================
        # Need to generate a visualization
        dspy.Example(
            query="Create a pie chart showing the distribution of categories",
            data_desc="Execution History: 1 step, 3000 chars total.\nLast output (100 chars, truncated): df loaded with columns: ['category', 'value']...",
            action="CODE"  # Needs matplotlib to create chart
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: API/Web Requests
        # =====================================================================
        # Need live data from web
        dspy.Example(
            query="What are today's top news headlines?",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="CODE"  # Needs web search tool
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # COMPLEX: Multi-file Operations
        # =====================================================================
        dspy.Example(
            query="Compare the schemas of data1.csv and data2.csv",
            data_desc="AVAILABLE FILES:\n[FILE] data1.csv\n[FILE] data2.csv\nExecution History: 0 steps. No code executed yet.",
            action="CODE"  # Need to read both files
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # FAILURE CASES: Verbose Output Prevention
        # =====================================================================
        # Research task that should ANSWER (not output steps)
        dspy.Example(
            query="Analyze the current state of AI research and summarize key trends",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="ANSWER"  # NOT "1. CATEGORIZE THE ARTICLES..."
        ).with_inputs("query", "data_desc"),

        # Complex request but just needs direct answer
        dspy.Example(
            query="Summarize the key findings from the research papers",
            data_desc="Execution History: 3 steps, 25000 chars total.\nLast output (200 chars, truncated): Web search returned 5 articles about LLMs...",
            action="ANSWER"  # NOT "First, I will analyze each paper..."
        ).with_inputs("query", "data_desc"),

        # Multi-part question that tempts verbose response
        dspy.Example(
            query="Explain 1) Language model trends, 2) Computer vision advances",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="DELEGATE"  # Should delegate, not list steps
        ).with_inputs("query", "data_desc"),

        # After delegation complete
        dspy.Example(
            query="Explain 1) Language model trends, 2) Computer vision advances",
            data_desc="Execution History: 1 step, 8000 chars total.\nLast output (500 chars, truncated): Delegated to 2 sub-agents.\nResults:\n- LLM: Scaling laws continue...",
            action="ANSWER"  # Combine results, don't re-delegate
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # FAILURE CASES: Action Word Clarity
        # =====================================================================
        # Should be CODE not "I will calculate"
        dspy.Example(
            query="Calculate the sum of numbers from 1 to 100",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="CODE"  # NOT "First, I will calculate..."
        ).with_inputs("query", "data_desc"),

        # Should be ANSWER not "I will explain"
        dspy.Example(
            query="What is machine learning?",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="ANSWER"  # NOT "I will explain machine learning..."
        ).with_inputs("query", "data_desc"),

        # Should be DELEGATE not "I will split"
        dspy.Example(
            query="Process items A, B, C, D, E in parallel and summarize each",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="DELEGATE"  # NOT "I will split this into subtasks..."
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # FAILURE CASES: Numbered List Prevention
        # =====================================================================
        # Should not return "1. First step 2. Second step"
        dspy.Example(
            query="Create a bar chart from the sales data",
            data_desc="AVAILABLE FILES:\n[FILE] sales.csv\nExecution History: 0 steps. No code executed yet.",
            action="CODE"  # NOT "1. Load the data 2. Create chart..."
        ).with_inputs("query", "data_desc"),

        # Conceptual question - single word answer
        dspy.Example(
            query="How do neural networks learn?",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="ANSWER"  # NOT "1. Forward pass 2. Compute loss..."
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Context-Aware Decisions
        # =====================================================================
        # Has artifacts directory, should save output there
        dspy.Example(
            query="Generate a visualization of the data",
            data_desc="OUTPUT DIRECTORY: /runs/20260109_123456\nAVAILABLE FILES:\n[FILE] data.csv\nExecution History: 0 steps. No code executed yet.",
            action="CODE"  # Needs to create and save chart
        ).with_inputs("query", "data_desc"),

        # Context directory provided, need to read files
        dspy.Example(
            query="Summarize all the text files in the context",
            data_desc="INPUT FILES (in /data/docs):\n[FILE] report1.txt\n[FILE] report2.txt\n[FILE] summary.md\nExecution History: 0 steps. No code executed yet.",
            action="CODE"  # Need to read files first
        ).with_inputs("query", "data_desc"),
    ]
    return dataset


def get_coder_data() -> list[dspy.Example]:
    """
    Returns training examples for the Coder module.

    The Coder generates executable Python code for a given task.
    Examples cover various file types, tools, and common patterns.

    PAPER-STYLE PATTERNS (MIT RLM arXiv:2512.24601v1):
    - context_summary contains METADATA only, not full execution content
    - Code should access full content via __execution_history__
    - Large outputs should be processed with llm_query() in chunks
    - Available globals: __execution_history__, __task__, __artifacts_dir__, llm_query, search_web

    Returns:
        List of dspy.Example objects with task, context_summary, and python_code fields.
    """
    dataset = [
        # =====================================================================
        # FILE HANDLING: Excel/Spreadsheets
        # =====================================================================
        dspy.Example(
            task="Check the formula in cell E5 of 'dataset.xlsx'.",
            context_summary="AVAILABLE FILES: [FILE] dataset.xlsx",
            python_code="import openpyxl\nwb = openpyxl.load_workbook('dataset.xlsx', data_only=False)\nws = wb.active\nprint(f'Formula in E5: {ws[\"E5\"].value}')",
            expected_output="=SUM"
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Read the first sheet of 'report.xlsx' into a DataFrame.",
            context_summary="AVAILABLE FILES: [FILE] report.xlsx",
            python_code="import pandas as pd\ndf = pd.read_excel('report.xlsx', sheet_name=0, engine='openpyxl')\nprint(df.head())",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # FILE HANDLING: CSV
        # =====================================================================
        dspy.Example(
            task="Read 'data.csv' and print the column names.",
            context_summary="AVAILABLE FILES: [FILE] data.csv",
            python_code="import pandas as pd\ndf = pd.read_csv('data.csv')\nprint('Columns:', list(df.columns))",
            expected_output="Columns:"
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Calculate the sum of the 'revenue' column in sales.csv.",
            context_summary="AVAILABLE FILES: [FILE] sales.csv",
            python_code="import pandas as pd\ndf = pd.read_csv('sales.csv')\ntotal = df['revenue'].sum()\nprint(f'Total revenue: {total}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # FILE HANDLING: PDF
        # =====================================================================
        dspy.Example(
            task="Extract text from the first page of 'document.pdf'.",
            context_summary="AVAILABLE FILES: [FILE] document.pdf",
            python_code="from pypdf import PdfReader\nreader = PdfReader('document.pdf')\ntext = reader.pages[0].extract_text()\nprint(text[:500])",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Extract the first table from 'report.pdf'.",
            context_summary="AVAILABLE FILES: [FILE] report.pdf",
            python_code="import pdfplumber\nwith pdfplumber.open('report.pdf') as pdf:\n    page = pdf.pages[0]\n    table = page.extract_table()\n    for row in table[:5]:\n        print(row)",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # FILE HANDLING: Word Documents
        # =====================================================================
        dspy.Example(
            task="Read the text from 'memo.docx'.",
            context_summary="AVAILABLE FILES: [FILE] memo.docx",
            python_code="from docx import Document\ndoc = Document('memo.docx')\nfor para in doc.paragraphs:\n    print(para.text)",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # WEB SEARCH (Using project's search tool)
        # search_web is PRE-LOADED in globals - no import needed!
        # =====================================================================
        dspy.Example(
            task="Find out who won the 2024 Super Bowl.",
            context_summary="",
            python_code="results = search_web('2024 Super Bowl winner')\nfor r in results[:3]:\n    print(f\"- {r['title']}\")",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="What is the current weather in Tokyo?",
            context_summary="",
            python_code="results = search_web('Tokyo weather today')\nfor r in results[:3]:\n    print(f\"{r['title']}: {r['body'][:100]}\")",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Search for the latest news about AI regulation.",
            context_summary="",
            python_code="results = search_web('AI regulation news 2026')\nfor r in results:\n    print(f\"Title: {r['title']}\\nSnippet: {r['body'][:150]}...\\n\")",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # ARTIFACT SAVING PATTERNS
        # __artifacts_dir__ is PRE-LOADED in globals
        # =====================================================================
        dspy.Example(
            task="Create a pie chart of market share and save it.",
            context_summary="",
            python_code="import matplotlib.pyplot as plt\n\ndata = {'Company A': 35, 'Company B': 25, 'Company C': 20, 'Others': 20}\nplt.figure(figsize=(8, 8))\nplt.pie(data.values(), labels=data.keys(), autopct='%1.1f%%')\nplt.title('Market Share Distribution')\nplt.savefig(f'{__artifacts_dir__}/market_share.png')\nplt.close()\nprint('Chart saved to artifacts directory')",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Generate a timeline chart of AI model releases.",
            context_summary="",
            python_code="import matplotlib.pyplot as plt\nimport pandas as pd\n\ndata = {\n    'Model': ['GPT-3', 'DALL-E', 'GPT-4', 'Claude 3', 'GPT-5'],\n    'Year': [2020, 2021, 2023, 2024, 2025]\n}\ndf = pd.DataFrame(data)\n\nplt.figure(figsize=(12, 4))\nplt.barh(df['Model'], df['Year'], color='steelblue')\nplt.xlabel('Release Year')\nplt.title('Major AI Model Releases')\nplt.tight_layout()\nplt.savefig(f'{__artifacts_dir__}/ai_timeline.png')\nplt.close()\nprint('Timeline saved')",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Save the search results to a markdown report.",
            context_summary="Previous execution: results = search_web('AI breakthroughs 2025')",
            python_code="# results already available from previous step\nreport = '# AI Breakthroughs 2025\\n\\n'\nfor r in results:\n    report += f\"## {r['title']}\\n{r['body']}\\n\\n\"\n\nwith open(f'{__artifacts_dir__}/ai_report.md', 'w') as f:\n    f.write(report)\nprint('Report saved to ai_report.md')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # COMPUTATION
        # =====================================================================
        dspy.Example(
            task="Calculate the 50th Fibonacci number.",
            context_summary="",
            python_code="def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n\nprint(f'Fibonacci(50) = {fib(50)}')",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Find all prime numbers less than 100.",
            context_summary="",
            python_code="def is_prime(n):\n    if n < 2:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True\n\nprimes = [n for n in range(100) if is_prime(n)]\nprint(f'Primes under 100: {primes}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # USING PREVIOUS CONTEXT
        # =====================================================================
        dspy.Example(
            task="Calculate the standard deviation of the data.",
            context_summary="Previous execution:\ndf = pd.read_csv('data.csv')\nColumns: ['id', 'value', 'category']",
            python_code="# df already loaded from previous step\nimport statistics\nstd_dev = df['value'].std()\nprint(f'Standard deviation: {std_dev}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # ERROR RECOVERY PATTERNS
        # =====================================================================
        dspy.Example(
            task="Install and use the requests library to fetch data from an API.",
            context_summary="Previous execution:\nOutput: ModuleNotFoundError: No module named 'requests'",
            python_code="# requests not available, use built-in urllib instead\nimport urllib.request\nimport json\nwith urllib.request.urlopen('https://api.example.com/data') as response:\n    data = json.loads(response.read())\nprint(data)",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # JSON HANDLING
        # =====================================================================
        dspy.Example(
            task="Parse the config.json file and print all keys.",
            context_summary="AVAILABLE FILES: [FILE] config.json",
            python_code="import json\nwith open('config.json', 'r') as f:\n    config = json.load(f)\nprint('Keys:', list(config.keys()))",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # DATA TRANSFORMATION
        # =====================================================================
        dspy.Example(
            task="Merge sales.csv and products.csv on product_id.",
            context_summary="AVAILABLE FILES: [FILE] sales.csv [FILE] products.csv",
            python_code="import pandas as pd\nsales = pd.read_csv('sales.csv')\nproducts = pd.read_csv('products.csv')\nmerged = pd.merge(sales, products, on='product_id')\nprint(merged.head())",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # PLOTTING/VISUALIZATION
        # =====================================================================
        dspy.Example(
            task="Create a bar chart of category counts and save as chart.png.",
            context_summary="Previous execution:\ndf loaded with columns: ['id', 'category', 'value']",
            python_code="import matplotlib.pyplot as plt\ncounts = df['category'].value_counts()\ncounts.plot(kind='bar')\nplt.title('Category Distribution')\nplt.savefig('chart.png')\nprint('Saved chart.png')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # DATE/TIME OPERATIONS
        # =====================================================================
        dspy.Example(
            task="Calculate the number of days between the first and last date in dates.csv.",
            context_summary="AVAILABLE FILES: [FILE] dates.csv",
            python_code="import pandas as pd\ndf = pd.read_csv('dates.csv', parse_dates=['date'])\ndays_diff = (df['date'].max() - df['date'].min()).days\nprint(f'Days between first and last: {days_diff}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # PAPER-STYLE: Accessing __execution_history__
        # These examples teach the model to access previous results programmatically
        # =====================================================================
        dspy.Example(
            task="Analyze the search results from previous steps",
            context_summary="Execution History: 3 steps, 15000 chars total.\nLast output (500 chars, truncated): [Search results about AI...]",
            python_code="# Access full content from __execution_history__ (paper pattern)\nfor entry in __execution_history__:\n    if 'search' in entry['code'].lower():\n        print(f\"Step {entry['step']}: {entry['output_length']} chars\")\n        # Preview first 200 chars\n        print(f\"Preview: {entry['output'][:200]}...\")",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Summarize all findings from the research",
            context_summary="Execution History: 8 steps, 85000 chars total.\nLast output (300 chars, truncated): Research findings...",
            python_code="# Gather outputs and summarize with llm_query (paper pattern)\nall_content = '\\n\\n'.join(e['output'] for e in __execution_history__ if e['output_length'] > 100)\n\n# Process in chunks to avoid overflow\nchunk_size = 20000\nsummaries = []\nfor i in range(0, len(all_content), chunk_size):\n    chunk = all_content[i:i+chunk_size]\n    summary = llm_query('Extract key findings from this section', chunk)\n    summaries.append(summary)\n\n# Final aggregation\nfinal = llm_query(f'Combine into comprehensive answer for: {__task__}', '\\n\\n'.join(summaries))\nprint(final)",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Extract all dates mentioned in the documents",
            context_summary="Execution History: 5 steps, 100000 chars total.\nLast output (200 chars, truncated): PDF text content...",
            python_code="# Get large output from history and process in chunks\nbig_text = __execution_history__[-1]['output']\n\n# Process in chunks (paper pattern for 10M+ token handling)\nchunk_size = 15000\nall_dates = []\nfor i in range(0, len(big_text), chunk_size):\n    chunk = big_text[i:i+chunk_size]\n    dates = llm_query('List all dates in YYYY-MM-DD format', chunk)\n    if dates.strip():\n        all_dates.append(dates)\n\nprint('Found dates:')\nprint('\\n'.join(all_dates))",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Answer the original question using collected data",
            context_summary="Execution History: 6 steps, 45000 chars total.\nUse __execution_history__ for full content.",
            python_code="# Build answer from execution history (paper pattern)\nrelevant_data = []\nfor entry in __execution_history__:\n    if entry['output_length'] > 100:  # Skip empty/error outputs\n        relevant_data.append(f\"Step {entry['step']}:\\n{entry['output'][:5000]}\")\n\n# Synthesize answer with llm_query\ncontext = '\\n\\n---\\n\\n'.join(relevant_data)\nanswer = llm_query(f'Based on this research, answer: {__task__}', context[:50000])\nprint(answer)",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Find errors in previous execution steps",
            context_summary="Execution History: 4 steps, 8000 chars total.\nLast output (150 chars): Traceback...",
            python_code="# Analyze execution history for errors\nfor entry in __execution_history__:\n    if 'Traceback' in entry['output'] or 'Error' in entry['output']:\n        print(f\"Error in Step {entry['step']}:\")\n        print(f\"Code: {entry['code'][:100]}...\")\n        print(f\"Error: {entry['output'][:300]}\")\n        print()",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # PAPER-STYLE: Using llm_query for chunked processing
        # =====================================================================
        dspy.Example(
            task="Classify each item in the search results",
            context_summary="Execution History: 2 steps, 12000 chars total.\nLast output (500 chars, truncated): [List of articles...]",
            python_code="# Get articles from last step\narticles = __execution_history__[-1]['output'].split('\\n\\n')\n\n# Classify each using llm_query\nclassifications = []\nfor i, article in enumerate(articles[:20]):\n    if len(article) > 50:\n        label = llm_query('Classify as: positive, negative, or neutral', article)\n        classifications.append({'index': i, 'label': label.strip()})\n        print(f\"Article {i}: {label.strip()}\")",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Extract structured data from unstructured text",
            context_summary="Execution History: 3 steps, 50000 chars total.\nLast output (500 chars, truncated): Company reports...",
            python_code="# Process large text in chunks with llm_query\ntext = __execution_history__[-1]['output']\n\n# Extract data in chunks\nall_data = []\nchunk_size = 10000\nfor i in range(0, len(text), chunk_size):\n    chunk = text[i:i+chunk_size]\n    extracted = llm_query('Extract company names, revenues, and dates as JSON', chunk)\n    all_data.append(extracted)\n\n# Combine results\nprint('Extracted data:')\nfor data in all_data:\n    print(data)",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # ANTI-PATTERNS: Things the model should NOT do
        # These examples show CORRECT alternatives to forbidden patterns
        # =====================================================================

        # NEVER use Jupyter magic commands
        dspy.Example(
            task="Install pandas and use it to read a CSV file.",
            context_summary="",
            python_code="# pandas is already installed, just import and use it\nimport pandas as pd\ndf = pd.read_csv('data.csv')\nprint(df.head())",
        ).with_inputs("task", "context_summary"),

        # NEVER use subprocess or os.system
        dspy.Example(
            task="Get system CPU information.",
            context_summary="",
            python_code="import platform\nimport os\n\nprint(f'Platform: {platform.system()}')\nprint(f'Processor: {platform.processor()}')\nprint(f'Architecture: {platform.machine()}')\nprint(f'CPU count: {os.cpu_count()}')",
        ).with_inputs("task", "context_summary"),

        # NEVER use requests directly - use search_web
        dspy.Example(
            task="Fetch data from an external API.",
            context_summary="",
            python_code="# Use search_web for external data instead of requests\nresults = search_web('my query')\nfor r in results[:3]:\n    print(r['title'])",
        ).with_inputs("task", "context_summary"),

        # Output ONLY code, no explanatory text
        dspy.Example(
            task="Create a simple calculation function.",
            context_summary="",
            python_code="def calculate(a, b):\n    return a + b\n\nresult = calculate(10, 20)\nprint(f'Result: {result}')",
        ).with_inputs("task", "context_summary"),

        # Use pre-loaded variables correctly
        dspy.Example(
            task="Save analysis results to the output folder.",
            context_summary="data = {'accuracy': 0.95, 'precision': 0.92}",
            python_code="import json\n\n# __artifacts_dir__ is pre-loaded, use it directly\nwith open(f'{__artifacts_dir__}/results.json', 'w') as f:\n    json.dump(data, f, indent=2)\nprint(f'Results saved to {__artifacts_dir__}/results.json')",
        ).with_inputs("task", "context_summary"),
    ]
    return dataset


def split_train_val(dataset: list[dspy.Example], val_ratio: float = 0.3) -> tuple[list, list]:
    """
    Split dataset into training and validation sets.

    For MIPROv2, validation set is used to prevent overfitting during
    Bayesian optimization of instructions.

    Args:
        dataset: Full list of examples
        val_ratio: Fraction to use for validation (default 0.3)

    Returns:
        Tuple of (trainset, valset)
    """
    import random
    random.seed(42)  # Reproducibility
    shuffled = dataset.copy()
    random.shuffle(shuffled)

    split_idx = int(len(shuffled) * (1 - val_ratio))
    return shuffled[:split_idx], shuffled[split_idx:]
