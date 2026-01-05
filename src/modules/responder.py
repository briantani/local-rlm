import dspy

class ResponderSignature(dspy.Signature):
    """
    Generates a natural language response to a user's query based on context.
    """
    query = dspy.InputField(desc="The user's query.")
    context = dspy.InputField(desc="Context, including previous code execution outputs.", default="")
    response = dspy.OutputField(desc="The final answer to the query.")

class Responder(dspy.Module):
    def __init__(self):
        super().__init__()
        self.respond = dspy.ChainOfThought(ResponderSignature)

    def forward(self, query: str, context: str = "") -> dspy.Prediction:
        return self.respond(query=query, context=context)
