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
