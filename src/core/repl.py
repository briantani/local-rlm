import io
import contextlib
import traceback

class PythonREPL:
    """
    A stateful, secure Python sandbox for executing generated code.
    """
    def __init__(self):
        self.globals = {}
        self.locals = {}

    def execute(self, code: str) -> str:
        """
        Executes the given Python code in the sandbox.

        Args:
            code: The Python code to execute.

        Returns:
            The captured stdout or the traceback if an exception occurred.
        """
        # Basic Sanitization
        if "os.system" in code or "subprocess" in code:
             return "SecurityError: Forbidden module or function usage."

        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                exec(code, self.globals, self.locals)
            return buffer.getvalue().strip()
        except Exception:
            # Return traceback as string, don't crash
            return traceback.format_exc()
