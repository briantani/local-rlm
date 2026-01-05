import dspy

class DelegatorSignature(dspy.Signature):
    """
    Breaks down a complex task into smaller, independent subtasks that can be executed in parallel.
    Returns a Python list of strings.
    """
    task = dspy.InputField(desc="The complex task to split.")
    context = dspy.InputField(desc="Relevant context.", default="")
    subtasks = dspy.OutputField(desc="A list of subtasks, one per line, starting with '- '.")

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
