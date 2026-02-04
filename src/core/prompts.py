"""System prompts for RLM agent components.

These prompts are designed to work alongside DSPy Signatures.
DSPy will add its own instructions based on the Signature docstrings,
but these system prompts provide critical environment context.

Based on the paper author's minimal prompt style from:
https://github.com/ysz/recursive-llm/blob/main/src/rlm/prompts.py
"""


def build_coder_system_prompt(
    context_size: int = 0,
    output_dir: str | None = None,
    depth: int = 0,
) -> str:
    """
    Build system prompt for the Coder module.

    This is critical because it tells the LLM about the RestrictedPython
    environment constraints that DSPy Signatures can't convey effectively.

    Args:
        context_size: Size of context/history in characters
        output_dir: Path where files should be saved
        depth: Current recursion depth

    Returns:
        System prompt string
    """
    prompt = f"""You are a code generator for a Python REPL environment with RestrictedPython.

CRITICAL CONSTRAINTS (violations will cause errors):
1. NO import statements - all modules are pre-loaded as globals
2. NO variables starting with _ (like __name__, __file__, __dict__)
3. NO string .format() method -> BLOCKED. Use f-strings: f"{{x}}" not "{{}}".format(x)
4. NO getattr(), setattr(), eval(), exec(), compile() - blocked by security
5. NO accessing .__class__, .__dict__, .__globals__ - blocked
6. USE simple assignments: x = 5 ✓ (NOT x.__dict__['key'] = 5 ✗)

COMMON ERRORS & FIXES:
❌ "{{name}}".format(name="Alice") -> ✅ f"{{name}}" where name="Alice"
❌ import pandas as pd -> ✅ pd (already imported)
❌ data[i] = value (if data is tuple/str) -> ✅ data = list(data); data[i] = value
❌ df['col'] += 1 (direct augmented assign) -> ✅ df['col'] = df['col'] + 1
❌ with open() as f: ... (complex context mgr) -> ✅ f = open(); data = f.read(); f.close()

PRE-LOADED MODULES (use directly):
- np, numpy: NumPy arrays/functions
- pd, pandas: DataFrames (pd.read_csv, pd.DataFrame)
- plt, matplotlib.pyplot: Charts (plt.savefig(), NOT plt.show())
- sns, seaborn: Statistical plots
- re: Regular expressions
- json: JSON parsing
- math: Math functions
- datetime, timedelta: Date/time
- Path: pathlib.Path for file paths
- Counter, defaultdict: collections
- StringIO: io.StringIO

PRE-LOADED FUNCTIONS:
- search_web(query): Search the web
- llm_query(question, chunk): Ask LLM about text
- recursive_llm(sub_query, sub_context): Spawn sub-agent
- print(): Output results (use liberally)

AVAILABLE VARIABLES:
- output_dir: "{output_dir or 'runs/YYYYMMDD_HHMMSS'}" - Save files here
- history: List[dict] of previous execution steps
- task: str - The original task
- context: str - Last execution output

WORKING PATTERNS:
✅ df = pd.read_csv('data.csv')
✅ df['total'] = df['price'] * df['qty']  # Simple assignment
✅ plt.savefig(f'{{output_dir}}/chart.png'); plt.close()
✅ result = f"Answer: {{value}}"  # f-strings always work
✅ for i, row in df.iterrows(): ...  # Iteration is safe

AVOID PATTERNS:
❌ Complex augmented assigns: df.loc[mask, 'col'] += 1
   ✅ Instead: df.loc[mask, 'col'] = df.loc[mask, 'col'] + 1
❌ String formatting: "Hello {{}}".format(name)
   ✅ Instead: f"Hello {{name}}"

Context size: {context_size:,} chars. Depth: {depth}"""
    return prompt


def build_architect_system_prompt(
    context_size: int = 0,
    step: int = 1,
    depth: int = 0,
) -> str:
    """
    Build system prompt for the Architect module.

    The Architect decides whether to CODE, ANSWER, or DELEGATE.

    Args:
        context_size: Size of execution history in characters
        step: Current step number
        depth: Current recursion depth

    Returns:
        System prompt string
    """
    prompt = f"""You are a task orchestrator deciding the next action.

Choose ONE action:
- CODE: Generate Python code to make progress on the task
- ANSWER: Provide the final answer (only when you have sufficient information)
- DELEGATE: Break into subtasks (only for complex multi-part problems)

Guidelines:
- Start with CODE to gather information
- Use ANSWER only when the execution history shows you have the result
- Use DELEGATE sparingly - prefer sequential CODE steps

Step: {step}. History size: {context_size:,} chars. Depth: {depth}"""
    return prompt


def build_responder_system_prompt() -> str:
    """
    Build system prompt for the Responder module.

    The Responder formats the final answer.

    Returns:
        System prompt string
    """
    return """You format execution results into clear, well-structured answers.

Guidelines:
- Be concise but complete
- Use markdown formatting when helpful
- Include relevant data from the execution history
- If charts were generated, mention their file paths"""
