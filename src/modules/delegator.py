import dspy

class DelegatorSignature(dspy.Signature):
    """
    Breaks down a complex task into smaller, independent subtasks that can be executed sequentially.
    Each subtask should be self-contained and should NOT assume data from previous subtasks.

    CRITICAL: Subtasks run SEQUENTIALLY with SHARED STATE. Variables created by earlier subtasks
    are available to later subtasks. Structure subtasks so earlier ones create data, later ones use it.

    IMPORTANT: Each subtask should:
    1. First check if data already exists (from previous subtask) before generating/loading
    2. Reference variables by name (e.g., "Use the 'sales_df' DataFrame from the previous step")
    3. Be specific about what variables to create and what to output

    Returns a Python list of strings.
    """
    task = dspy.InputField(desc="The complex task to split.")
    context = dspy.InputField(desc="Relevant context.", default="")
    subtasks = dspy.OutputField(desc="A list of subtasks, one per line, starting with '- '. Each subtask should reference any data it needs from previous subtasks.")

class Delegator(dspy.Module):
    def __init__(self):
        super().__init__()
        self.delegate = dspy.ChainOfThought(DelegatorSignature)

    def forward(self, task: str, context: str = "") -> list[str]:
        prediction = self.delegate(task=task, context=context)
        raw_text = prediction.subtasks

        # Parse the output into a list of strings
        subtasks = []
        for line in raw_text.split('\n'):
            line = line.strip()
            if line.startswith("- "):
                subtasks.append(line[2:].strip())
            elif line.startswith("* "):
                subtasks.append(line[2:].strip())
            elif line and line[0].isdigit() and ". " in line: # Handle "1. ", "2. "
                parts = line.split(". ", 1)
                if len(parts) > 1:
                    subtasks.append(parts[1].strip())

        # Fallback if parsing failed but there is text
        if not subtasks and raw_text.strip():
            subtasks = [raw_text.strip()]

        return subtasks
