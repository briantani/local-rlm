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
        """Test that __execution_history__ is accessible in code execution."""
        repl = PythonREPL()
        repl.add_history_entry("step1", "output1", step=1)
        repl.add_history_entry("step2", "output2", step=2)

        # Code should be able to access __execution_history__
        output = repl.execute("print(len(__execution_history__))")
        assert "2" in output

    def test_execution_history_structure(self):
        """Test that __execution_history__ has correct structure."""
        repl = PythonREPL()
        repl.add_history_entry("x = 42", "42", step=1)

        # Access the history entry structure
        output = repl.execute("entry = __execution_history__[0]; print(entry['step'], entry['code'], entry['output'], entry['output_length'])")
        assert "1" in output  # step
        assert "x = 42" in output  # code
        assert "42" in output  # output

    def test_task_available_in_globals(self):
        """Test that __task__ is accessible in code execution."""
        repl = PythonREPL()
        repl.set_task("Calculate fibonacci")

        output = repl.execute("print(__task__)")
        assert "Calculate fibonacci" in output

    def test_llm_query_available_in_globals(self):
        """Test that llm_query function is available (even if it's a stub)."""
        repl = PythonREPL()
        # Just check it exists, don't call it in tests (would need LLM)
        output = repl.execute("print(callable(llm_query))")
        assert "True" in output

    def test_history_entry_preserves_large_output(self):
        """Test that full output is preserved in history (not truncated)."""
        repl = PythonREPL()
        large_output = "B" * 50000  # 50KB
        repl.add_history_entry("big", large_output, step=1)

        # The full output should be in history
        output = repl.execute("print(len(__execution_history__[0]['output']))")
        assert "50000" in output
