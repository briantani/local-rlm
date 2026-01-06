import concurrent.futures
from pathlib import Path
from src.core.repl import PythonREPL
from src.modules.architect import Architect
from src.modules.coder import Coder
from src.modules.responder import Responder
from src.modules.delegator import Delegator
from src.core.explorer import scan_directory

class RLMAgent:
    """
    The main Recursive Language Model Agent.
    Orchestrates the Architect, Coder, and REPL to solve tasks.
    Supports recursive delegation handling.
    """
    def __init__(self, max_steps: int = 10, max_depth: int = 3, depth: int = 0, root_dir: str | Path | None = None, coder=None):
        self.max_steps = max_steps
        self.max_depth = max_depth
        self.depth = depth
        self.root_dir = Path(root_dir) if root_dir else None

        self.repl = PythonREPL()
        self.architect = Architect()
        self.coder = coder if coder else Coder()
        self.responder = Responder()
        self.delegator = Delegator()

        self.history: list[tuple[str, str]] = [] # List of (Action/Code, Output)

        # Initialize context with file listing if root_dir is provided
        if self.root_dir and self.root_dir.exists():
            file_structure = scan_directory(self.root_dir)
            initial_context = (
                f"AVAILABLE FILES (Use Python code to read them):\n{file_structure}\n"
                f"NOTE: To access file content, you MUST generate Python code using open(), pd.read_csv(), etc."
            )
            self.history.append(("System Initialization", initial_context))

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
        indent = "  " * self.depth
        print(f"{indent}Agent (Depth {self.depth}) received task: {task}")

        for step in range(self.max_steps):
            print(f"\n{indent}--- Step {step + 1} ---")
            context = self.format_context()

            # 1. Architect decides what to do
            print(f"{indent}Thinking...")
            try:
                # We interpret 'data_desc' as the current context/state
                decision = self.architect(query=task, data_desc=context)
                action = decision.action.upper()
                print(f"{indent}Architect Decision: {action}")
            except Exception as e:
                print(f"{indent}Architect error: {e}")
                action = "ANSWER"

            # 2. Execute Action
            if action == "ANSWER":
                response = self.responder(query=task, context=context)
                final_answer = response.response
                print(f"{indent}Final Answer: {final_answer}")
                return final_answer

            elif action == "CODE":
                print(f"{indent}Generating code...")
                try:
                    code_pred = self.coder(task=task, context_summary=context)
                    code = code_pred.python_code
                    # print(f"{indent}Code Generated:\n{code}")

                    print(f"{indent}Executing code...")
                    output = self.repl.execute(code)
                    print(f"{indent}Execution Output (truncated): {output[:100]}..." if len(output) > 100 else f"{indent}Execution Output: {output}")

                    self.history.append((f"Executed Code:\n{code}", output))

                except Exception as e:
                    error_msg = f"Error during coding/execution: {e}"
                    print(f"{indent}{error_msg}")
                    self.history.append(("Attempted Code Generation", error_msg))

            elif action == "DELEGATE":
                if self.depth >= self.max_depth:
                    print(f"{indent}Max depth reached. Cannot delegate further. Returning to Answer mode.")
                    # Force answer in next step or use responder now?
                    # Let's add instruction to history to guide Architect
                    self.history.append(("Action: DELEGATE", "FAILED: Max recursion saturation reached. You must solve this yourself using CODE or ANSWER."))
                    continue

                print(f"{indent}Delegating task...")
                try:
                    # 1. Break down task
                    subtasks = self.delegator(task=task, context=context)
                    print(f"{indent}Subtasks identified: {subtasks}")

                    if not subtasks:
                        print(f"{indent}No subtasks found. Aborting delegation.")
                        self.history.append(("Action: DELEGATE", "FAILED: Could not split task."))
                        continue

                    # 2. Execute in parallel
                    results = []
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # Create sub-agents
                        futures = {}
                        for i, subtask in enumerate(subtasks):
                            # Instantiate new agent for each subtask
                            sub_agent = RLMAgent(max_steps=self.max_steps, max_depth=self.max_depth, depth=self.depth + 1)
                            futures[executor.submit(sub_agent.run, subtask)] = subtask

                        for future in concurrent.futures.as_completed(futures):
                            original_subtask = futures[future]
                            try:
                                res = future.result()
                                results.append(f"Subtask '{original_subtask}': {res}")
                            except Exception as exc:
                                results.append(f"Subtask '{original_subtask}' generated an exception: {exc}")

                    # 3. Aggregate results into history
                    combined_results = "\n".join(results)
                    print(f"{indent}Delegation Complete. Results:\n{combined_results}")
                    self.history.append((f"Delegated Subtasks: {subtasks}", f"Results from sub-agents:\n{combined_results}"))

                except Exception as e:
                    print(f"{indent}Delegation error: {e}")
                    self.history.append(("Action: DELEGATE", f"Error: {e}"))

            else:
                print(f"{indent}Unknown action: {action}")
                return f"Agent confused: Unknown action {action}"

        return "Max steps reached without definitive answer."
