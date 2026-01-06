import dspy

def get_architect_data():
    """
    Returns a list of dspy.Example objects for training the Architect.
    Each example mimics the Agent's runtime state.
    """
    dataset = [
        # Case 1: Start fresh -> Need Code
        dspy.Example(
            query="What is 2 + 2?",
            data_desc="Execution History:\n",
            action="CODE"
        ).with_inputs("query", "data_desc"),

        # Case 2: Code executed, result available -> Answer
        dspy.Example(
            query="What is 2 + 2?",
            data_desc="Execution History:\n--- Step 1 ---\nInput: print(2+2)\nOutput: 4\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # Case 3: Need to read file
        dspy.Example(
            query="What is the first line of test.txt?",
            data_desc="AVAILABLE FILES:\n[FILE] test.txt\nExecution History:\n",
            action="CODE"
        ).with_inputs("query", "data_desc"),

         # Case 4: File read, content available -> Answer (The critical fix for the loop)
        dspy.Example(
            query="What is the first line of test.txt?",
            data_desc="AVAILABLE FILES:\n[FILE] test.txt\nExecution History:\n--- Step 1 ---\nInput: print(open('test.txt').readline())\nOutput: # Hello World\n",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),

        # Case 5: Explicit Delegation
        dspy.Example(
            query="Process these 5 items in parallel.",
            data_desc="Execution History:\n",
            action="DELEGATE"
        ).with_inputs("query", "data_desc"),

        # Case 6: Delegation Done -> Answer
        dspy.Example(
            query="Process these 5 items in parallel.",
            data_desc="Execution History:\nDelegated Subtasks: [...]\nResults from sub-agents:\nItem 1: Done\nItem 2: Done",
            action="ANSWER"
        ).with_inputs("query", "data_desc"),
    ]
    return dataset
