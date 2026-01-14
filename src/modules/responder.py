from typing import TYPE_CHECKING

import dspy

if TYPE_CHECKING:
    from src.core.run_context import RunContext


class ResponderSignature(dspy.Signature):
    """
    Generates a natural language response to a user's query based on context.
    Format your response in Markdown with clear sections, bullet points, and code blocks where appropriate.
    """
    query = dspy.InputField(desc="The user's query.")
    context = dspy.InputField(desc="Context, including previous code execution outputs.", default="")
    artifacts_info = dspy.InputField(desc="Structured artifact metadata (filenames, sections, descriptions).", default="")
    response = dspy.OutputField(desc="A well-formatted Markdown response answering the query.")


class Responder(dspy.Module):
    def __init__(self, run_context: "RunContext | None" = None):
        super().__init__()
        self.respond = dspy.ChainOfThought(ResponderSignature)
        self.run_context = run_context

    def forward(self, query: str, context: str = "") -> dspy.Prediction:
        prediction = self.respond(query=query, context=context)

        # If we have a run context with images, append them to the response
        if self.run_context:
            response = self._enhance_with_artifacts(prediction.response)
            return dspy.Prediction(response=response)

        return prediction

    def _enhance_with_artifacts(self, response: str) -> str:
        """Enhance the response with references to generated artifacts.

        Args:
            response: The original response text

        Returns:
            Enhanced response with artifact references
        """
        if not self.run_context:
            return response

        images = self.run_context.list_images()
        if not images:
            return response

        # Append a section with generated images
        enhanced = response.strip()
        enhanced += "\n\n---\n\n## Generated Visualizations\n\n"

        for img in images:
            filename = img["filename"]
            description = img.get("description", filename)
            section = img.get("section")
            rationale = img.get("rationale")
            prompt = img.get("prompt")

            # Optionally include intended section as a subheading
            if section:
                enhanced += f"### Section: {section}\n\n"

            # Use relative path for markdown with description as alt text
            enhanced += f"![{description}]({filename})\n\n"

            # Include rationale and prompt if available to give context to the reader
            if rationale:
                enhanced += f"*Rationale:* {rationale}\n\n"
            if prompt:
                enhanced += f"*Prompt:* `{prompt}`\n\n"

        return enhanced
