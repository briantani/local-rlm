"""
Training data for DSPy module optimization.

Best Practices for DSPy Training Examples:
==========================================
1. DIVERSITY: Cover edge cases, not just happy paths. Include examples that
   represent different decision boundaries (e.g., when to CODE vs ANSWER).

2. CONTRASTIVE PAIRS: Include pairs that show the same query with different
   contexts leading to different outputs. This teaches the model decision logic.

3. REALISTIC CONTEXT: Use `data_desc` that mirrors actual runtime state
   (execution history, file manifests, error traces).

4. MINIMUM SIZE:
   - LabeledFewShot: 5-10 examples (just uses them as demos)
   - BootstrapFewShot: 10-20 examples (validates with metric)
   - MIPROv2: 50+ examples for instruction optimization, 200+ for full runs

5. INPUT MARKERS: Always call `.with_inputs()` to specify which fields are inputs.
   This is REQUIRED for optimization to work correctly.

6. VALIDATION SET: For MIPROv2, split data into trainset (70%) and valset (30%).
   The optimizer uses valset to prevent overfitting.
"""

import dspy


def get_architect_data() -> list[dspy.Example]:
    """
    Returns training examples for the Architect module.

    The Architect decides: ANSWER, CODE, or DELEGATE.
    Examples are organized as contrastive pairs to teach decision boundaries.

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
            data_desc="Execution History:\n",
            action="CODE"
        ).with_inputs("query", "data_desc"),

        # After execution: Result available, now ANSWER
        dspy.Example(
            query="What is 2 + 2?",
            data_desc="Execution History:\n--- Step 1 ---\nInput: print(2+2)\nOutput: 4\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # PAIR 2: File Reading - CODE vs ANSWER
        # =====================================================================
        # File exists but not read yet
        dspy.Example(
            query="What is the first line of test.txt?",
            data_desc="AVAILABLE FILES:\n[FILE] test.txt\nExecution History:\n",
            action="CODE"
        ).with_inputs("query", "data_desc"),

        # File has been read, content in history
        dspy.Example(
            query="What is the first line of test.txt?",
            data_desc="AVAILABLE FILES:\n[FILE] test.txt\nExecution History:\n--- Step 1 ---\nInput: print(open('test.txt').readline())\nOutput: # Hello World\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # PAIR 3: Data Analysis - CODE vs ANSWER
        # =====================================================================
        # CSV exists, need to analyze
        dspy.Example(
            query="What is the average sales in sales.csv?",
            data_desc="AVAILABLE FILES:\n[FILE] sales.csv\nExecution History:\n",
            action="CODE"
        ).with_inputs("query", "data_desc"),

        # Analysis complete
        dspy.Example(
            query="What is the average sales in sales.csv?",
            data_desc="AVAILABLE FILES:\n[FILE] sales.csv\nExecution History:\n--- Step 1 ---\nInput: import pandas as pd; df = pd.read_csv('sales.csv'); print(df['sales'].mean())\nOutput: 1523.45\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # PAIR 4: Delegation - DELEGATE vs ANSWER
        # =====================================================================
        # Explicit parallel request
        dspy.Example(
            query="Process these 5 items in parallel.",
            data_desc="Execution History:\n",
            action="DELEGATE"
        ).with_inputs("query", "data_desc"),

        # Delegation complete
        dspy.Example(
            query="Process these 5 items in parallel.",
            data_desc="Execution History:\nDelegated Subtasks: [...]\nResults from sub-agents:\nItem 1: Done\nItem 2: Done\nItem 3: Done\nItem 4: Done\nItem 5: Done",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # PURE ANSWER CASES (No computation needed)
        # =====================================================================
        # General knowledge - no code needed
        dspy.Example(
            query="What is the capital of France?",
            data_desc="Execution History:\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # Greeting/chitchat
        dspy.Example(
            query="Hello, how are you?",
            data_desc="Execution History:\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # Explain a concept
        dspy.Example(
            query="What is recursion in programming?",
            data_desc="Execution History:\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Error Recovery
        # =====================================================================
        # Code failed, need to retry with different approach
        dspy.Example(
            query="Read the Excel file report.xlsx",
            data_desc="AVAILABLE FILES:\n[FILE] report.xlsx\nExecution History:\n--- Step 1 ---\nInput: import pandas as pd; df = pd.read_excel('report.xlsx')\nOutput: Traceback: ModuleNotFoundError: No module named 'openpyxl'\n",
            action="CODE"  # Should try again with openpyxl import
        ).with_inputs("query", "data_desc"),

        # Successful retry
        dspy.Example(
            query="Read the Excel file report.xlsx",
            data_desc="AVAILABLE FILES:\n[FILE] report.xlsx\nExecution History:\n--- Step 2 ---\nInput: import openpyxl; wb = openpyxl.load_workbook('report.xlsx'); print(wb.sheetnames)\nOutput: ['Sheet1', 'Summary']\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Web Search
        # =====================================================================
        # Need current information
        dspy.Example(
            query="What is the current price of Bitcoin?",
            data_desc="Execution History:\n",
            action="CODE"  # Needs web search tool
        ).with_inputs("query", "data_desc"),

        # Search complete
        dspy.Example(
            query="What is the current price of Bitcoin?",
            data_desc="Execution History:\n--- Step 1 ---\nInput: from src.tools.search import search_web; print(search_web('Bitcoin price today'))\nOutput: Bitcoin is trading at $98,432 as of January 6, 2026.\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Complex Multi-Step
        # =====================================================================
        # Multi-step task, first step done
        dspy.Example(
            query="Load data.csv, calculate the mean, and plot a histogram",
            data_desc="AVAILABLE FILES:\n[FILE] data.csv\nExecution History:\n--- Step 1 ---\nInput: import pandas as pd; df = pd.read_csv('data.csv'); print(df.head())\nOutput:    value\n0    10\n1    20\n",
            action="CODE"  # Still need to calculate mean and plot
        ).with_inputs("query", "data_desc"),

        # All steps complete
        dspy.Example(
            query="Load data.csv, calculate the mean, and plot a histogram",
            data_desc="AVAILABLE FILES:\n[FILE] data.csv\nExecution History:\n--- Step 1 ---\nInput: import pandas as pd; df = pd.read_csv('data.csv'); print(df['value'].mean())\nOutput: 15.0\n--- Step 2 ---\nInput: import matplotlib.pyplot as plt; df['value'].hist(); plt.savefig('histogram.png'); print('Saved histogram.png')\nOutput: Saved histogram.png\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Empty/No Output
        # =====================================================================
        # Code ran but no output (might need to check result)
        dspy.Example(
            query="Save the data to output.csv",
            data_desc="Execution History:\n--- Step 1 ---\nInput: df.to_csv('output.csv', index=False)\nOutput: \n",
            action="ANSWER"  # Empty output is fine for file save operations
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: SecurityError
        # =====================================================================
        # Code was blocked by REPL security
        dspy.Example(
            query="Run a shell command to list files",
            data_desc="Execution History:\n--- Step 1 ---\nInput: import os; os.system('ls -la')\nOutput: SecurityError: Forbidden module or function usage.\n",
            action="ANSWER"  # Should explain the security restriction
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Ambiguous Queries
        # =====================================================================
        # User asks about code but doesn't need it run
        dspy.Example(
            query="How do I read a CSV file in Python?",
            data_desc="Execution History:\n",
            action="ANSWER"  # This is a knowledge question, not execution
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: Image Generation
        # =====================================================================
        # Need to generate a visualization
        dspy.Example(
            query="Create a pie chart showing the distribution of categories",
            data_desc="Previous execution:\ndf loaded with columns: ['category', 'value']\n",
            action="CODE"  # Needs matplotlib to create chart
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # EDGE CASES: API/Web Requests
        # =====================================================================
        # Need live data from web
        dspy.Example(
            query="What are today's top news headlines?",
            data_desc="Execution History:\n",
            action="CODE"  # Needs web search tool
        ).with_inputs("query", "data_desc"),

        # =====================================================================
        # COMPLEX: Multi-file Operations
        # =====================================================================
        dspy.Example(
            query="Compare the schemas of data1.csv and data2.csv",
            data_desc="AVAILABLE FILES:\n[FILE] data1.csv\n[FILE] data2.csv\nExecution History:\n",
            action="CODE"  # Need to read both files
        ).with_inputs("query", "data_desc"),
    ]
    return dataset


def get_coder_data() -> list[dspy.Example]:
    """
    Returns training examples for the Coder module.

    The Coder generates executable Python code for a given task.
    Examples cover various file types, tools, and common patterns.

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
        # =====================================================================
        dspy.Example(
            task="Find out who won the 2024 Super Bowl.",
            context_summary="",
            python_code="from src.tools.search import search_web\nresults = search_web('2024 Super Bowl winner')\nprint(results)",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="What is the current weather in Tokyo?",
            context_summary="",
            python_code="from src.tools.search import search_web\nresults = search_web('Tokyo weather today')\nprint(results)",
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
