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

    The Architect decides: ANSWER or CODE.
    (DELEGATE was removed - sub-agents are now spawned via recursive_llm() in code)
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
        # PAIR 4: Sub-task Recursion - CODE with recursive_llm()
        # Paper-style: Complex tasks use recursive_llm() to spawn sub-agents
        # =====================================================================
        # Need to break down into sub-tasks
        dspy.Example(
            query="Process these 5 items in parallel.",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="CODE"  # Use recursive_llm() to spawn sub-agents
        ).with_inputs("query", "data_desc"),

        # Sub-agents complete
        dspy.Example(
            query="Process these 5 items in parallel.",
            data_desc="Execution History: 1 step, 5000 chars total.\nLast output (500 chars, truncated): Results from recursive_llm calls:\nItem 1: Done\nItem 2: Done...",
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

        # Multi-part question - use CODE with recursive_llm() for sub-queries
        dspy.Example(
            query="Explain 1) Language model trends, 2) Computer vision advances",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="CODE"  # Use recursive_llm() for each sub-topic
        ).with_inputs("query", "data_desc"),

        # After recursive_llm() calls complete
        dspy.Example(
            query="Explain 1) Language model trends, 2) Computer vision advances",
            data_desc="Execution History: 1 step, 8000 chars total.\nLast output (500 chars, truncated): recursive_llm results:\n- LLM: Scaling laws continue...",
            action="ANSWER"  # Combine results
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

        # Should be CODE with recursive_llm() for parallelism
        dspy.Example(
            query="Process items A, B, C, D, E in parallel and summarize each",
            data_desc="Execution History: 0 steps. No code executed yet.",
            action="CODE"  # Use recursive_llm() in a loop or ThreadPoolExecutor
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
    Examples use RestrictedPython-compatible patterns:

    CRITICAL RULES (RestrictedPython sandbox):
    - NO import statements - all modules are PRE-LOADED as globals
    - Use simple variable names: output_dir, history, task, context
    - Pre-loaded modules: np, pd, plt, re, json, math, datetime, Counter, defaultdict
    - Pre-loaded functions: search_web(), llm_query()

    Returns:
        List of dspy.Example objects with task, context_summary, and python_code fields.
    """
    dataset = [
        # =====================================================================
        # DATA SCIENCE - Using pre-loaded numpy, pandas, matplotlib
        # NO IMPORTS NEEDED - modules are pre-loaded as globals
        # =====================================================================
        dspy.Example(
            task="Create synthetic sales data and calculate statistics",
            context_summary="output_dir = '/tmp/output'",
            python_code="# np, pd are pre-loaded - NO imports\ndata = {'Q1': np.random.randint(100, 300), 'Q2': np.random.randint(150, 350)}\ndf = pd.DataFrame([data], index=['Sales'])\nprint(df.to_markdown())\nprint(f'Total: ${df.sum().sum()}')",
            expected_output="Sales"
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Create a bar chart of quarterly sales and save it",
            context_summary="output_dir = '/tmp/output'",
            python_code="# plt is pre-loaded - NO imports\ndata = {'Q1': 100, 'Q2': 150, 'Q3': 120, 'Q4': 180}\nplt.figure(figsize=(10, 6))\nplt.bar(data.keys(), data.values(), color='steelblue')\nplt.title('Quarterly Sales')\nplt.ylabel('Sales ($K)')\nplt.savefig(f'{output_dir}/sales_chart.png', dpi=100)\nplt.close()\nprint(f'Chart saved to {output_dir}/sales_chart.png')",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Create a pie chart of category distribution",
            context_summary="output_dir = '/tmp/output'",
            python_code="# plt is pre-loaded - NO imports\ndata = {'Electronics': 35, 'Clothing': 25, 'Home': 20, 'Food': 20}\nplt.figure(figsize=(8, 8))\nplt.pie(data.values(), labels=data.keys(), autopct='%1.1f%%')\nplt.title('Sales by Category')\nplt.savefig(f'{output_dir}/category_pie.png')\nplt.close()\nprint('Pie chart saved')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # DATA ANALYSIS with pre-loaded modules
        # =====================================================================
        dspy.Example(
            task="Generate random data and calculate mean and standard deviation",
            context_summary="",
            python_code="# np is pre-loaded - NO imports\ndata = np.random.normal(100, 15, size=1000)\nprint(f'Mean: {np.mean(data):.2f}')\nprint(f'Std Dev: {np.std(data):.2f}')\nprint(f'Min: {np.min(data):.2f}')\nprint(f'Max: {np.max(data):.2f}')",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Create a DataFrame with random data and save as markdown table",
            context_summary="",
            python_code="# pd, np are pre-loaded - NO imports\ncategories = ['Electronics', 'Clothing', 'Home', 'Food']\nquarters = ['Q1', 'Q2', 'Q3', 'Q4']\ndata = np.random.randint(50, 500, size=(4, 4)) * 1000\ndf = pd.DataFrame(data, index=categories, columns=quarters)\nprint('## Sales Data')\nprint(df.to_markdown())\nprint(f'\\nTotal: ${df.sum().sum():,}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # WEB SEARCH - search_web is pre-loaded
        # =====================================================================
        dspy.Example(
            task="Search for the latest AI news",
            context_summary="",
            python_code="# search_web is pre-loaded - NO imports\nresults = search_web('latest AI news 2026')\nfor r in results[:3]:\n    print(f\"- {r['title']}: {r['body'][:100]}...\")",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Find information about quantum computing",
            context_summary="",
            python_code="# search_web is pre-loaded - NO imports\nresults = search_web('quantum computing breakthroughs')\nfor r in results:\n    print(f\"Title: {r['title']}\")\n    print(f\"Snippet: {r['body'][:150]}...\")\n    print()",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # REGEX OPERATIONS - re is pre-loaded
        # =====================================================================
        dspy.Example(
            task="Extract all numbers from the text",
            context_summary="",
            python_code="# re is pre-loaded - NO imports\ntext = 'Revenue was $1.5M in Q1, $2.3M in Q2, and $3.1M in Q3'\nnumbers = re.findall(r'\\d+\\.?\\d*', text)\nprint(f'Found numbers: {numbers}')",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Find all email addresses in the document",
            context_summary="Execution History: 1 step. Last output: document text...",
            python_code="# re is pre-loaded, history is the simple alias for execution history\ntext = history[-1]['output'] if history else 'test@example.com'\nemails = re.findall(r'[\\w.+-]+@[\\w-]+\\.[\\w.-]+', text)\nprint(f'Found {len(emails)} emails:')\nfor email in emails:\n    print(f'  - {email}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # JSON OPERATIONS - json is pre-loaded
        # =====================================================================
        dspy.Example(
            task="Convert data to JSON and save it",
            context_summary="output_dir = '/tmp/output'",
            python_code="# json is pre-loaded - NO imports\ndata = {'name': 'Report', 'values': [1, 2, 3], 'meta': {'version': '1.0'}}\nwith open(f'{output_dir}/data.json', 'w') as f:\n    json.dump(data, f, indent=2)\nprint('JSON saved')\nprint(json.dumps(data, indent=2))",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # ACCESSING EXECUTION HISTORY - use 'history' simple alias
        # =====================================================================
        dspy.Example(
            task="Analyze the search results from previous steps",
            context_summary="Execution History: 3 steps, 15000 chars total. Last output: search results...",
            python_code="# Use 'history' (simple alias) instead of __execution_history__\nfor entry in history:\n    if 'search' in entry['code'].lower():\n        print(f\"Step {entry['step']}: {entry['output_length']} chars\")\n        print(f\"Preview: {entry['output'][:200]}...\")",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Summarize all findings from the research",
            context_summary="Execution History: 8 steps, 85000 chars total.",
            python_code="# Use 'history' and 'task' simple aliases\nall_content = '\\n\\n'.join(e['output'] for e in history if e['output_length'] > 100)\n\n# Process in chunks with llm_query\nchunk_size = 20000\nsummaries = []\nfor i in range(0, len(all_content), chunk_size):\n    chunk = all_content[i:i+chunk_size]\n    summary = llm_query('Extract key findings', chunk)\n    summaries.append(summary)\n\nfinal = llm_query(f'Combine into answer for: {task}', '\\n\\n'.join(summaries))\nprint(final)",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Answer the original question using collected data",
            context_summary="Execution History: 6 steps, 45000 chars total.",
            python_code="# Use 'history' and 'task' simple aliases\nrelevant = []\nfor entry in history:\n    if entry['output_length'] > 100:\n        relevant.append(f\"Step {entry['step']}:\\n{entry['output'][:5000]}\")\n\ncontext_str = '\\n\\n---\\n\\n'.join(relevant)\nanswer = llm_query(f'Based on this research, answer: {task}', context_str[:50000])\nprint(answer)",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # MATH OPERATIONS - math is pre-loaded
        # =====================================================================
        dspy.Example(
            task="Calculate compound interest",
            context_summary="",
            python_code="# math is pre-loaded - NO imports\nprincipal = 10000\nrate = 0.05\nyears = 10\nfinal = principal * math.pow(1 + rate, years)\nprint(f'Principal: ${principal:,}')\nprint(f'Rate: {rate*100}%')\nprint(f'Years: {years}')\nprint(f'Final amount: ${final:,.2f}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # DATETIME OPERATIONS - datetime, timedelta are pre-loaded
        # =====================================================================
        dspy.Example(
            task="Calculate days until end of year",
            context_summary="",
            python_code="# datetime is pre-loaded - NO imports\ntoday = datetime.now()\nyear_end = datetime(today.year, 12, 31)\ndays_left = (year_end - today).days\nprint(f'Today: {today.strftime(\"%Y-%m-%d\")}')\nprint(f'Days until year end: {days_left}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # COLLECTIONS - Counter, defaultdict are pre-loaded
        # =====================================================================
        dspy.Example(
            task="Count word frequencies in text",
            context_summary="",
            python_code="# Counter is pre-loaded - NO imports\ntext = 'the quick brown fox jumps over the lazy dog the fox is quick'\nwords = text.lower().split()\nword_counts = Counter(words)\nprint('Word frequencies:')\nfor word, count in word_counts.most_common(5):\n    print(f'  {word}: {count}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # SEABORN - Statistical visualization (sns is pre-loaded)
        # =====================================================================
        dspy.Example(
            task="Create a correlation heatmap for the data",
            context_summary="output_dir = '/tmp/output'",
            python_code="# sns (seaborn) is pre-loaded - NO imports\ndata = pd.DataFrame(np.random.randn(50, 4), columns=['A', 'B', 'C', 'D'])\nplt.figure(figsize=(8, 6))\nsns.heatmap(data.corr(), annot=True, cmap='coolwarm', center=0)\nplt.title('Correlation Heatmap')\nplt.tight_layout()\nplt.savefig(f'{output_dir}/heatmap.png')\nplt.close()\nprint('Heatmap saved')",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Create a distribution plot for the sales data",
            context_summary="output_dir = '/tmp/output'",
            python_code="# sns (seaborn) is pre-loaded\ndata = np.random.normal(100, 15, 200)\nplt.figure(figsize=(10, 6))\nsns.histplot(data, kde=True)\nplt.title('Sales Distribution')\nplt.xlabel('Sales ($K)')\nplt.savefig(f'{output_dir}/distribution.png')\nplt.close()\nprint('Distribution plot saved')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # SCIPY - Scientific computing (scipy, scipy_stats are pre-loaded)
        # =====================================================================
        dspy.Example(
            task="Perform a t-test to compare two groups",
            context_summary="",
            python_code="# scipy_stats is pre-loaded - NO imports\ngroup_a = [23, 25, 28, 24, 26, 27, 25]\ngroup_b = [31, 29, 32, 30, 28, 33, 31]\nt_stat, p_value = scipy_stats.ttest_ind(group_a, group_b)\nprint(f'T-statistic: {t_stat:.4f}')\nprint(f'P-value: {p_value:.4f}')\nprint(f'Significant at 0.05: {p_value < 0.05}')",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Calculate correlation between two variables",
            context_summary="",
            python_code="# scipy_stats is pre-loaded\nx = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\ny = [2, 4, 5, 4, 5, 7, 8, 9, 10, 11]\ncorr, p_value = scipy_stats.pearsonr(x, y)\nprint(f'Pearson correlation: {corr:.4f}')\nprint(f'P-value: {p_value:.4f}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # SCIKIT-LEARN - Machine learning (sklearn classes are pre-loaded)
        # =====================================================================
        dspy.Example(
            task="Fit a linear regression model to the data",
            context_summary="",
            python_code="# LinearRegression is pre-loaded - NO imports\nX = np.array([[1], [2], [3], [4], [5]])\ny = np.array([2.1, 3.9, 6.2, 7.8, 10.1])\nmodel = LinearRegression()\nmodel.fit(X, y)\nprint(f'Coefficient: {model.coef_[0]:.4f}')\nprint(f'Intercept: {model.intercept_:.4f}')\nprint(f'R² Score: {model.score(X, y):.4f}')",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Cluster the data into 3 groups using K-means",
            context_summary="output_dir = '/tmp/output'",
            python_code="# KMeans is pre-loaded - NO imports\ndata = np.random.randn(100, 2)\nkmeans = KMeans(n_clusters=3, random_state=42, n_init=10)\nlabels = kmeans.fit_predict(data)\n\nplt.figure(figsize=(8, 6))\nplt.scatter(data[:, 0], data[:, 1], c=labels, cmap='viridis')\nplt.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:, 1], marker='X', s=200, c='red')\nplt.title('K-Means Clustering')\nplt.savefig(f'{output_dir}/clusters.png')\nplt.close()\nprint(f'Cluster sizes: {np.bincount(labels)}')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # STATSMODELS - Statistical analysis (sm is pre-loaded)
        # =====================================================================
        dspy.Example(
            task="Perform OLS regression with summary statistics",
            context_summary="",
            python_code="# sm (statsmodels.api) is pre-loaded - NO imports\nX = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])\ny = np.array([2.3, 4.1, 5.8, 8.2, 9.5, 11.8, 13.2, 16.1, 17.5, 20.1])\nX_with_const = sm.add_constant(X)\nmodel = sm.OLS(y, X_with_const).fit()\nprint(model.summary())",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # DOCUMENT PROCESSING - pdfplumber, docx, openpyxl are pre-loaded
        # =====================================================================
        dspy.Example(
            task="Extract text from a PDF file",
            context_summary="AVAILABLE FILES: [FILE] document.pdf",
            python_code="# pdfplumber is pre-loaded - NO imports\nwith pdfplumber.open(f'{input_dir}/document.pdf') as pdf:\n    text = ''\n    for page in pdf.pages:\n        text += page.extract_text() or ''\nprint(f'Extracted {len(text)} characters from PDF')\nprint(text[:500])",
        ).with_inputs("task", "context_summary"),

        dspy.Example(
            task="Read a Word document and extract paragraphs",
            context_summary="AVAILABLE FILES: [FILE] report.docx",
            python_code="# docx is pre-loaded - NO imports\ndoc = docx.Document(f'{input_dir}/report.docx')\nparagraphs = [p.text for p in doc.paragraphs if p.text.strip()]\nprint(f'Found {len(paragraphs)} paragraphs')\nfor i, p in enumerate(paragraphs[:5]):\n    print(f'{i+1}. {p[:100]}...')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # COMPLETE EXAMPLE: Generate report with chart
        # =====================================================================
        dspy.Example(
            task="Generate a sales report with table and chart",
            context_summary="output_dir = '/tmp/output'",
            python_code="# All modules pre-loaded: np, pd, plt, json\n# Generate data\ncategories = ['Electronics', 'Clothing', 'Home', 'Food']\nquarters = ['Q1', 'Q2', 'Q3', 'Q4']\ndata = np.random.randint(100, 500, size=(4, 4))\ndf = pd.DataFrame(data, index=categories, columns=quarters)\n\n# Print table\nprint('# Sales Report')\nprint(df.to_markdown())\nprint(f'\\nTotal: ${df.sum().sum():,}K')\n\n# Best performers\nprint(f'\\nBest category: {df.sum(axis=1).idxmax()}')\nprint(f'Best quarter: {df.sum(axis=0).idxmax()}')\n\n# Create chart\nplt.figure(figsize=(10, 6))\ndf.plot(kind='bar', ax=plt.gca())\nplt.title('Quarterly Sales by Category')\nplt.ylabel('Sales ($K)')\nplt.legend(title='Quarter')\nplt.tight_layout()\nplt.savefig(f'{output_dir}/sales_report.png')\nplt.close()\nprint(f'\\nChart saved to {output_dir}/sales_report.png')",
        ).with_inputs("task", "context_summary"),

        # =====================================================================
        # ANTI-PATTERNS: Teach what NOT to do
        # =====================================================================
        # NEVER use import statements
        dspy.Example(
            task="Calculate statistics for a list of numbers",
            context_summary="",
            python_code="# CORRECT: Use pre-loaded np, not 'import numpy'\ndata = [10, 20, 30, 40, 50]\narr = np.array(data)\nprint(f'Mean: {np.mean(arr)}')\nprint(f'Std: {np.std(arr)}')\nprint(f'Sum: {np.sum(arr)}')",
        ).with_inputs("task", "context_summary"),

        # Use output_dir not __artifacts_dir__
        dspy.Example(
            task="Save results to the output directory",
            context_summary="output_dir = '/tmp/output'",
            python_code="# CORRECT: Use 'output_dir' not '__artifacts_dir__'\nresults = {'score': 0.95, 'accuracy': 0.92}\nwith open(f'{output_dir}/results.json', 'w') as f:\n    json.dump(results, f, indent=2)\nprint(f'Saved to {output_dir}/results.json')",
        ).with_inputs("task", "context_summary"),

        # Use history not __execution_history__
        dspy.Example(
            task="Get the last execution output",
            context_summary="Execution History: 3 steps.",
            python_code="# CORRECT: Use 'history' not '__execution_history__'\nlast_output = history[-1]['output'] if history else 'No history'\nprint(f'Last output ({len(last_output)} chars):')\nprint(last_output[:500])",
        ).with_inputs("task", "context_summary"),

        # Use task not __task__
        dspy.Example(
            task="Echo the current task",
            context_summary="",
            python_code="# CORRECT: Use 'task' not '__task__'\nprint(f'Current task: {task}')",
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
