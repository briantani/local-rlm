from src.core.repl import PythonREPL

def test_batch_llm_query_exposed():
    """Test that batch_llm_query is available in the REPL globals."""
    repl = PythonREPL()
    output = repl.execute("print(callable(batch_llm_query))")
    assert "True" in output

def test_batch_llm_query_interface():
    """Test that batch_llm_query can be called (mocking the actual LLM call)."""
    # We can't easily mock the internal LLM call here without dependency injection,
    # but we can verify the function signature and existence.
    repl = PythonREPL()
    
    # Check it accepts list input
    code = """
try:
    # Passing empty list should return empty list without calling LLM
    result = batch_llm_query("query", [])
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result)}")
except Exception as e:
    print(f"Error: {e}")
"""
    output = repl.execute(code)
    assert "Result type: <class 'list'>" in output
    assert "Result length: 0" in output
