"""Tests for the parser module (paper-style FINAL() termination)."""

from src.core.parser import extract_final, extract_final_var, is_final, parse_response


class TestExtractFinal:
    """Tests for extract_final function."""

    def test_double_quotes(self):
        """Test extracting FINAL with double quotes."""
        response = 'Some text\nFINAL("The answer is 42")\nMore text'
        assert extract_final(response) == "The answer is 42"

    def test_single_quotes(self):
        """Test extracting FINAL with single quotes."""
        response = "FINAL('Hello world')"
        assert extract_final(response) == "Hello world"

    def test_triple_double_quotes(self):
        """Test extracting FINAL with triple double quotes."""
        response = '''FINAL("""This is a
multiline
answer""")'''
        result = extract_final(response)
        assert "multiline" in result
        assert "answer" in result

    def test_triple_single_quotes(self):
        """Test extracting FINAL with triple single quotes."""
        response = """FINAL('''Another
multiline
response''')"""
        result = extract_final(response)
        assert "multiline" in result
        assert "response" in result

    def test_f_string_double(self):
        """Test extracting FINAL with f-string double quotes."""
        response = 'FINAL(f"The result is {value}")'
        assert extract_final(response) == "The result is {value}"

    def test_f_string_single(self):
        """Test extracting FINAL with f-string single quotes."""
        response = "FINAL(f'Count: {count}')"
        assert extract_final(response) == "Count: {count}"

    def test_not_found(self):
        """Test when FINAL not found."""
        response = "Just some text without final"
        assert extract_final(response) is None

    def test_with_spaces(self):
        """Test FINAL with spaces around parentheses."""
        response = 'FINAL( "with spaces" )'
        assert extract_final(response) == "with spaces"

    def test_in_code_output(self):
        """Test FINAL appearing in code execution output."""
        response = """
result = calculate_stuff()
print(f"Computed: {result}")
FINAL("The computation is complete with result 42")
"""
        assert extract_final(response) == "The computation is complete with result 42"


class TestExtractFinalVar:
    """Tests for extract_final_var function."""

    def test_simple_variable(self):
        """Test extracting FINAL_VAR with simple variable."""
        response = "result = 'test'\nFINAL_VAR(result)"
        env = {"result": "test value"}
        assert extract_final_var(response, env) == "test value"

    def test_numeric_variable(self):
        """Test extracting FINAL_VAR with numeric variable."""
        response = "FINAL_VAR(answer)"
        env = {"answer": 42}
        assert extract_final_var(response, env) == "42"

    def test_list_variable(self):
        """Test extracting FINAL_VAR with list variable."""
        response = "FINAL_VAR(items)"
        env = {"items": [1, 2, 3]}
        assert extract_final_var(response, env) == "[1, 2, 3]"

    def test_not_found(self):
        """Test when FINAL_VAR not found."""
        response = "Just some code"
        env = {}
        assert extract_final_var(response, env) is None

    def test_missing_variable(self):
        """Test when variable doesn't exist in env."""
        response = "FINAL_VAR(missing)"
        env = {}
        assert extract_final_var(response, env) is None

    def test_with_spaces(self):
        """Test FINAL_VAR with spaces."""
        response = "FINAL_VAR( result )"
        env = {"result": "found"}
        assert extract_final_var(response, env) == "found"


class TestIsFinal:
    """Tests for is_final function."""

    def test_final_detected(self):
        """Test that FINAL() is detected."""
        assert is_final('FINAL("answer")') is True

    def test_final_var_detected(self):
        """Test that FINAL_VAR() is detected."""
        assert is_final("FINAL_VAR(result)") is True

    def test_not_final(self):
        """Test that regular text is not detected."""
        assert is_final("Just text") is False

    def test_partial_match(self):
        """Test partial matches."""
        assert is_final("FINAL") is False  # No parenthesis
        assert is_final("FINAL_VAR") is False  # No parenthesis


class TestParseResponse:
    """Tests for parse_response function."""

    def test_final_preferred(self):
        """Test that FINAL() is tried before FINAL_VAR()."""
        response = 'FINAL("direct answer")\nFINAL_VAR(result)'
        env = {"result": "variable answer"}
        # Should return FINAL() value, not FINAL_VAR()
        assert parse_response(response, env) == "direct answer"

    def test_final_var_fallback(self):
        """Test FINAL_VAR when FINAL not present."""
        response = "FINAL_VAR(result)"
        env = {"result": "variable answer"}
        assert parse_response(response, env) == "variable answer"

    def test_none_when_no_final(self):
        """Test None returned when no final."""
        response = "Regular code output"
        assert parse_response(response, {}) is None


class TestIntegrationWithCodeOutput:
    """Integration tests simulating real code execution output."""

    def test_final_in_print_output(self):
        """Test FINAL appearing after print statements."""
        output = """Loading data...
Processing 100 items...
Done!
FINAL("Processed 100 items successfully")"""
        assert is_final(output)
        assert extract_final(output) == "Processed 100 items successfully"

    def test_final_with_computed_result(self):
        """Test FINAL with a result computed in code."""
        output = """
for i in range(10):
    total += i
print(f"Sum: {total}")
FINAL("The sum of 0-9 is 45")
"""
        assert extract_final(output) == "The sum of 0-9 is 45"

    def test_final_var_with_complex_value(self):
        """Test FINAL_VAR with complex computed value."""
        output = """
analysis_result = {
    'count': 42,
    'average': 3.14,
    'status': 'complete'
}
FINAL_VAR(analysis_result)
"""
        env = {"analysis_result": {"count": 42, "average": 3.14, "status": "complete"}}
        assert is_final(output)
        result = parse_response(output, env)
        assert "count" in result
        assert "42" in result
