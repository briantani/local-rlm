"""Parse FINAL() and FINAL_VAR() statements from LLM responses (paper-style).

This module provides paper-compatible termination parsing. When the LLM
outputs FINAL("answer") or FINAL_VAR(result), the agent can detect it
and return immediately without going through the Architect → ANSWER flow.

Reference: MIT RLM paper - the LLM writes FINAL() to signal task completion.
"""

import re
from typing import Any


def extract_final(response: str) -> str | None:
    """Extract answer from FINAL() statement.

    Supports multiple quote styles:
    - FINAL("answer")
    - FINAL('answer')
    - FINAL('''multiline answer''')
    - FINAL(f"formatted {var}")  # f-string evaluated in context

    Args:
        response: LLM response text or code output

    Returns:
        Extracted answer string or None if not found
    """
    # Patterns in order of specificity (triple quotes first)
    patterns = [
        r'FINAL\s*\(\s*"""(.*)"""',  # FINAL("""answer""") - triple double quotes
        r"FINAL\s*\(\s*'''(.*)'''",  # FINAL('''answer''') - triple single quotes
        r'FINAL\s*\(\s*"([^"]*)"',   # FINAL("answer") - double quotes
        r"FINAL\s*\(\s*'([^']*)'",   # FINAL('answer') - single quotes
        r'FINAL\s*\(\s*f"([^"]*)"',  # FINAL(f"answer") - f-string (content only)
        r"FINAL\s*\(\s*f'([^']*)'",  # FINAL(f'answer') - f-string single quotes
    ]

    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()

    return None


def extract_final_var(response: str, env: dict[str, Any]) -> str | None:
    """Extract answer from FINAL_VAR() statement.

    FINAL_VAR(variable_name) returns the value of a variable from the
    REPL environment. This is useful when the answer is computed and
    stored in a variable rather than as a literal string.

    Args:
        response: LLM response text or code output
        env: REPL environment with variables (globals/locals)

    Returns:
        Variable value as string or None if not found
    """
    # Look for FINAL_VAR(var_name)
    match = re.search(r'FINAL_VAR\s*\(\s*(\w+)\s*\)', response)
    if not match:
        return None

    var_name = match.group(1)

    # Get variable from environment
    if var_name in env:
        value = env[var_name]
        return str(value)

    return None


def is_final(response: str) -> bool:
    """Check if response contains FINAL() or FINAL_VAR().

    This is a quick check to avoid regex overhead on every response.

    Args:
        response: LLM response text or code output

    Returns:
        True if response contains a final statement
    """
    return 'FINAL(' in response or 'FINAL_VAR(' in response


def parse_response(response: str, env: dict[str, Any]) -> str | None:
    """Parse response for any final statement.

    Tries FINAL() first, then FINAL_VAR().

    Args:
        response: LLM response text or code output
        env: REPL environment for FINAL_VAR lookup

    Returns:
        Final answer or None if no final statement found
    """
    # Try FINAL() first (more common)
    answer = extract_final(response)
    if answer is not None:
        return answer

    # Try FINAL_VAR()
    answer = extract_final_var(response, env)
    if answer is not None:
        return answer

    return None
