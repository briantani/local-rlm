from src.core.repl import PythonREPL

def test_repl_persistence():
    """Test 1.1: The REPL remembers variables between separate execute() calls."""
    repl = PythonREPL()
    repl.execute("x = 10")
    output = repl.execute("print(x)")
    assert output == "10"

def test_repl_syntax_error():
    """Test 1.2: Syntax errors return text descriptions, not exceptions."""
    repl = PythonREPL()
    output = repl.execute("def func(")
    assert "SyntaxError" in output

def test_repl_stdout():
    """Test 1.3: Run print('test'). Assert return value contains 'test'."""
    repl = PythonREPL()
    output = repl.execute("print('test')")
    assert "test" in output

def test_repl_security():
    """Test basic security sanitization."""
    repl = PythonREPL()
    output = repl.execute("import os; os.system('ls')")
    assert "SecurityError" in output


# ============================================================================
# PAPER-STYLE METADATA TESTS (MIT RLM Paper Implementation)
# ============================================================================

class TestPaperStyleMetadata:
    """Tests for the paper-style metadata approach that prevents context overflow."""

    def test_get_history_metadata_empty(self):
        """Test that metadata returns correct info when history is empty."""
        repl = PythonREPL()
        metadata = repl.get_history_metadata()
        assert "0 steps" in metadata
        assert "No code executed" in metadata or "0 chars" in metadata

    def test_get_history_metadata_with_entries(self):
        """Test metadata accurately reflects execution history."""
        repl = PythonREPL()
        repl.add_history_entry("x = 1", "1", step=1)
        repl.add_history_entry("y = 2", "22", step=2)

        metadata = repl.get_history_metadata()
        assert "2 steps" in metadata
        # Total chars: "x = 1" (5) + "1" (1) + "y = 2" (5) + "22" (2) = 13
        assert "13 chars" in metadata

    def test_get_history_metadata_large_content_not_included(self):
        """Critical: Metadata must NOT contain the actual content."""
        repl = PythonREPL()
        large_content = "A" * 10000  # 10KB of content
        repl.add_history_entry("big_code", large_content, step=1)

        metadata = repl.get_history_metadata()
        # Metadata should be short, not contain the 10KB
        assert len(metadata) < 200
        assert "AAAA" not in metadata  # Content should NOT be in metadata
        assert "10000" in metadata or "chars" in metadata

    def test_get_last_output_preview_empty(self):
        """Test preview returns empty string when no history."""
        repl = PythonREPL()
        preview = repl.get_last_output_preview()
        assert preview == ""

    def test_get_last_output_preview_short_output(self):
        """Test preview includes full output when it's short."""
        repl = PythonREPL()
        repl.add_history_entry("print(42)", "42", step=1)

        preview = repl.get_last_output_preview()
        assert "42" in preview
        assert "Last output" in preview

    def test_get_last_output_preview_truncates_long_output(self):
        """Test preview truncates output that exceeds max_chars."""
        repl = PythonREPL()
        long_output = "X" * 1000  # 1000 chars
        repl.add_history_entry("code", long_output, step=1)

        preview = repl.get_last_output_preview(max_chars=100)
        assert len(preview) < 300  # Should be truncated + header + hint
        assert "..." in preview  # Should indicate truncation
        assert "XXXX" in preview  # Should have some content
        assert "1000 chars" in preview  # Should show original length

    def test_execution_history_available_in_globals(self):
        """Test that history alias is accessible in code execution."""
        repl = PythonREPL()
        repl.add_history_entry("step1", "output1", step=1)
        repl.add_history_entry("step2", "output2", step=2)

        # Code should be able to access history (simple alias for __execution_history__)
        output = repl.execute("print(len(history))")
        assert "2" in output

    def test_execution_history_structure(self):
        """Test that history alias has correct structure."""
        repl = PythonREPL()
        repl.add_history_entry("x = 42", "42", step=1)

        # Access the history entry structure using simple alias
        output = repl.execute("entry = history[0]; print(entry['step'], entry['code'], entry['output'], entry['output_length'])")
        assert "1" in output  # step
        assert "x = 42" in output  # code
        assert "42" in output  # output

    def test_task_available_in_globals(self):
        """Test that task alias is accessible in code execution."""
        repl = PythonREPL()
        repl.set_task("Calculate fibonacci")

        # Use simple alias (task) instead of __task__
        output = repl.execute("print(task)")
        assert "Calculate fibonacci" in output

    def test_llm_query_available_in_globals(self):
        """Test that llm_query function is available (even if it's a stub)."""
        repl = PythonREPL()
        # Just check it exists, don't call it in tests (would need LLM)
        output = repl.execute("print(callable(llm_query))")
        assert "True" in output

    def test_recursive_llm_available_in_globals(self):
        """Test that recursive_llm function is available for paper-style recursion."""
        repl = PythonREPL()
        # Just check it exists, don't call it in tests (would spawn agents)
        output = repl.execute("print(callable(recursive_llm))")
        assert "True" in output

    def test_recursive_llm_depth_limit(self):
        """Test that recursive_llm respects max depth."""
        repl = PythonREPL(max_depth=2, current_depth=2)  # Already at max
        # Call the function directly (it should return an error message)
        result = repl.globals["recursive_llm"]("sub query", "sub context")
        assert "Max recursion depth" in result

    def test_history_entry_preserves_large_output(self):
        """Test that full output is preserved in history (not truncated)."""
        repl = PythonREPL()
        large_output = "B" * 50000  # 50KB
        repl.add_history_entry("big", large_output, step=1)

        # The full output should be in history (using simple alias)
        output = repl.execute("print(len(history[0]['output']))")
        assert "50000" in output


# ============================================================================
# RESTRICTEDPYTHON TESTS (Secure Sandbox)
# ============================================================================

class TestRestrictedPythonSecurity:
    """Tests for RestrictedPython-based security."""

    def test_forbidden_import_os(self):
        """Test that import os is blocked."""
        repl = PythonREPL()
        output = repl.execute("import os")
        # RestrictedPython blocks __import__
        assert "Error" in output or "None" in output or "not allowed" in output.lower()

    def test_forbidden_subprocess(self):
        """Test that subprocess is blocked."""
        repl = PythonREPL()
        output = repl.execute("import subprocess")
        assert "Error" in output or "None" in output

    def test_forbidden_builtins_access(self):
        """Test that __builtins__ access is blocked."""
        repl = PythonREPL()
        output = repl.execute("print(__builtins__)")
        assert "SecurityError" in output or "Error" in output

    def test_safe_builtins_available(self):
        """Test that safe builtins like len, str, int are available."""
        repl = PythonREPL()
        output = repl.execute("print(len([1,2,3]), str(42), int('10'))")
        assert "3" in output
        assert "42" in output
        assert "10" in output

    def test_safe_modules_re(self):
        """Test that re module is pre-loaded and available."""
        repl = PythonREPL()
        # Modules are pre-loaded, no import needed
        output = repl.execute("print(re.findall(r'\\d+', 'a1b2c3'))")
        assert "1" in output and "2" in output and "3" in output

    def test_safe_modules_json(self):
        """Test that json module is pre-loaded and available."""
        repl = PythonREPL()
        # Modules are pre-loaded, no import needed
        output = repl.execute("print(json.dumps({'a': 1}))")
        assert '"a": 1' in output or '"a":1' in output

    def test_safe_modules_math(self):
        """Test that math module is pre-loaded and available."""
        repl = PythonREPL()
        # Modules are pre-loaded, no import needed
        output = repl.execute("print(math.sqrt(16))")
        assert "4" in output

    def test_code_block_extraction(self):
        """Test that code is extracted from markdown blocks."""
        repl = PythonREPL()
        code_with_block = """```python
x = 42
print(x)
```"""
        output = repl.execute(code_with_block)
        assert "42" in output

    def test_empty_code(self):
        """Test that empty code returns appropriate message."""
        repl = PythonREPL()
        output = repl.execute("")
        assert "No code" in output

    def test_variable_persistence_across_executions(self):
        """Test that variables persist across execute() calls."""
        repl = PythonREPL()
        repl.execute("counter = 0")
        repl.execute("counter += 1")
        output = repl.execute("print(counter)")
        assert "1" in output


# ============================================================================
# PAPER-STYLE SIMPLE VARIABLE NAMES
# ============================================================================

class TestSimpleVariableNames:
    """Tests for simplified variable names (context, history, task)."""

    def test_context_initially_empty(self):
        """Test that 'context' is empty initially."""
        repl = PythonREPL()
        output = repl.execute("print(repr(context))")
        assert "''" in output  # Empty string

    def test_context_updated_after_history_entry(self):
        """Test that 'context' is updated to last output."""
        repl = PythonREPL()
        repl.add_history_entry("x = 1", "result: 42", step=1)

        output = repl.execute("print(context)")
        assert "result: 42" in output

    def test_context_slice_operation(self):
        """Test paper-style context[:100] slicing."""
        repl = PythonREPL()
        repl.add_history_entry("code", "A" * 200, step=1)

        output = repl.execute("print(len(context[:100]))")
        assert "100" in output

    def test_history_alias_for_execution_history(self):
        """Test that 'history' is an alias for __execution_history__."""
        repl = PythonREPL()
        repl.add_history_entry("step1", "out1", step=1)
        repl.add_history_entry("step2", "out2", step=2)

        output = repl.execute("print(len(history))")
        assert "2" in output

        output = repl.execute("print(history[-1]['output'])")
        assert "out2" in output

    def test_task_simple_alias(self):
        """Test that 'task' is a simple alias for __task__."""
        repl = PythonREPL()
        repl.set_task("Calculate fibonacci sequence")

        output = repl.execute("print(task)")
        assert "fibonacci" in output

    def test_all_simple_names_work_together(self):
        """Test using all simple variable names in one code block."""
        repl = PythonREPL()
        repl.set_task("Analyze data")
        repl.add_history_entry("load_data()", "data loaded: 100 rows", step=1)

        code = """
print(f"Task: {task}")
print(f"History entries: {len(history)}")
print(f"Last context: {context[:20]}")
"""
        output = repl.execute(code)
        assert "Analyze data" in output
        assert "1" in output  # 1 history entry
        assert "data loaded" in output


# ============================================================================
# FINAL() TERMINATION SUPPORT
# ============================================================================

class TestFinalTermination:
    """Tests for paper-style FINAL() termination detection."""

    def test_check_for_final_with_final(self):
        """Test that FINAL() in output is detected."""
        repl = PythonREPL()
        output = 'Some processing...\nFINAL("The answer is 42")'

        result = repl.check_for_final(output)
        assert result == "The answer is 42"

    def test_check_for_final_with_final_var(self):
        """Test that FINAL_VAR() in output is detected."""
        repl = PythonREPL()
        # Set up a variable in the REPL
        repl.execute("answer = 'computed result'")

        output = 'Computation done.\nFINAL_VAR(answer)'
        result = repl.check_for_final(output)
        assert result == "computed result"

    def test_check_for_final_no_final(self):
        """Test that regular output returns None."""
        repl = PythonREPL()
        output = "Just regular output, no final statement"

        result = repl.check_for_final(output)
        assert result is None

    def test_check_for_final_multiline(self):
        """Test FINAL() with multiline answer."""
        repl = PythonREPL()
        output = '''Processing...
FINAL("""Line 1
Line 2
Line 3""")'''

        result = repl.check_for_final(output)
        assert "Line 1" in result
        assert "Line 2" in result

    def test_final_in_executed_code(self):
        """Test FINAL() appearing as print output from executed code."""
        repl = PythonREPL()
        code = '''
result = 2 + 2
print(f'FINAL("The sum is {result}")')
'''
        output = repl.execute(code)
        # The output should contain FINAL(...)
        assert "FINAL" in output
        assert "4" in output
