import dspy
from src.core.repl import PythonREPL
from src.modules.architect import Architect
from src.modules.coder import Coder
from src.modules.responder import Responder

class RLMAgent:
    """
    The main Recursive Language Model Agent.
    Orchestrates the Architect, Coder, and REPL to solve tasks.
    """
    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
        self.repl = PythonREPL()
        self.architect = Architect()
        self.coder = Coder()
        self.responder = Responder()
        self.history: list[tuple[str, str]] = [] # List of (Action/Code, Output)

    def format_context(self) -> str:
        """Formats the execution history into a string context."""
        if not self.history:
            return ""

        context_str = "Execution History:\n"
        for i, (action_or_code, output) in enumerate(self.history, 1):
            context_str += f"--- Step {i} ---\n"
            context_str += f"Input: {action_or_code}\n"
            context_str += f"Output: {output}\n"
        return context_str

    def run(self, task: str) -> str:
        """
        Executes the main loop to solve the task.
        """
        print(f"Agent received task: {task}")

        for step in range(self.max_steps):
            print(f"\n--- Step {step + 1} ---")
            context = self.format_context()

            # 1. Architect decides what to do
            print("Thinking...")
            try:
                # We interpret 'data_desc' as the current context/state
                decision = self.architect(query=task, data_desc=context)
                action = decision.action
                print(f"Architect Decision: {action}")
            except Exception as e:
                print(f"Architect error: {e}")
                # If architect fails, fallback or break?
                # For now, let's treat it as a hard failure or try to answer
                action = "ANSWER"

            # 2. Execute Action
            if action == "ANSWER":
                response = self.responder(query=task, context=context)
                return response.response

            elif action == "CODE":
                print("Generating code...")
                try:
                    code_pred = self.coder(task=task, context_summary=context)
                    code = code_pred.python_code
                    print(f"Code Generated:\n{code}")

                    print("Executing code...")
                    output = self.repl.execute(code)
                    print(f"Execution Output: {output}")

                    # Add to history
                    self.history.append((f"Executed Code:\n{code}", output))

                    # Heuristic: If we produced an answer in code (printed it),
                    # we might want to let the Architect decide if we are done in next loop.
                    # Or we could have an Explicit "DONE" check.
                    # For now, the Architect will see the output in context next turn and decide to ANSWER.

                except Exception as e:
                    error_msg = f"Error during coding/execution: {e}"
                    print(error_msg)
                    self.history.append(("Attempted Code Generation", error_msg))

            elif action == "DELEGATE":
                print("Delegating task (Not implemented yet).")
                self.history.append(("Action: DELEGATE", "Delegate functionality not yet implemented."))
                # Prevent infinite loop on stub
                if step > 2:
                    return "Delegation not implemented, stopping."

            else:
                print(f"Unknown action: {action}")
                return f"Agent confused: Unknown action {action}"

        return "Max steps reached without definitive answer."
