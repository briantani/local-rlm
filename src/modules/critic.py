"""
Vision-capable critic module for validating and refining visualizations.

Inspired by reflection patterns in recent Google research (Paperbanana),
this module analyzes generated charts/plots using vision-capable LLMs and
provides actionable feedback for iterative refinement.
"""

import dspy
from pathlib import Path


class CriticSignature(dspy.Signature):
    """Validate visualization quality and suggest specific improvements.

    Analyze the visualization against the task requirements and code intent.
    Evaluate: data accuracy, clarity, labeling, color choices, layout, and readability.

    Provide specific, actionable feedback for refinement.
    """
    task = dspy.InputField(desc="Original user task/query that required the visualization")
    code = dspy.InputField(desc="Python code that generated the visualization")
    image_path = dspy.InputField(desc="Path to the generated image file")
    execution_output = dspy.InputField(desc="Console output from code execution", default="")
    previous_feedback = dspy.InputField(desc="Feedback from previous refinement rounds", default="")

    is_valid = dspy.OutputField(desc="YES if visualization meets quality standards, NO if refinement needed")
    feedback = dspy.OutputField(desc="Detailed critique with specific improvement suggestions")
    confidence = dspy.OutputField(desc="Confidence score 0.0-1.0 in the validation", default="1.0")


class Critic(dspy.Module):
    """Vision-capable critic for visualization quality validation.

    Uses vision-capable LLMs (qwen3-vl, Gemini Flash, GPT-4o, llava) to analyze
    generated images and provide feedback for up to 3 rounds of refinement.
    """

    def __init__(self):
        super().__init__()
        self.critique = dspy.ChainOfThought(CriticSignature)

        # Few-shot examples for quality assessment
        self.critique.demos = [
            dspy.Example(
                task="Create a bar chart of quarterly sales data",
                code="plt.bar(quarters, sales)\nplt.title('Sales')\nplt.savefig(f'{output_dir}/chart.png')",
                image_path="/path/to/chart.png",
                execution_output="Chart saved to runs/20260209/chart.png",
                previous_feedback="",
                is_valid="NO",
                feedback="Chart lacks axis labels. Add: plt.xlabel('Quarter') and plt.ylabel('Sales ($)'). Consider adding a grid for better readability.",
                confidence="0.9"
            ).with_inputs("task", "code", "image_path", "execution_output", "previous_feedback"),

            dspy.Example(
                task="Visualize the correlation between temperature and sales",
                code="plt.scatter(temp, sales)\nplt.xlabel('Temperature (F)')\nplt.ylabel('Sales ($)')\nplt.title('Temperature vs Sales Correlation')\nplt.grid(True, alpha=0.3)\nplt.savefig(f'{output_dir}/correlation.png')",
                image_path="/path/to/correlation.png",
                execution_output="Chart saved",
                previous_feedback="",
                is_valid="YES",
                feedback="Excellent! Chart has clear labels, appropriate title, and grid for readability. Data points are visible and the correlation is clear.",
                confidence="0.95"
            ).with_inputs("task", "code", "image_path", "execution_output", "previous_feedback"),

            dspy.Example(
                task="Create a pie chart of market share by region",
                code="plt.pie(shares, labels=regions)\nplt.title('Market Share')\nplt.savefig(f'{output_dir}/pie.png')",
                image_path="/path/to/pie.png",
                execution_output="Chart saved",
                previous_feedback="Round 1: Missing percentage labels on pie slices",
                is_valid="NO",
                feedback="Previous feedback addressed partially. Add autopct='%1.1f%%' to plt.pie() to show percentages. Also consider using different colors for better distinction between regions.",
                confidence="0.85"
            ).with_inputs("task", "code", "image_path", "execution_output", "previous_feedback"),
        ]

    def forward(
        self,
        task: str,
        code: str,
        image_path: str | Path,
        execution_output: str = "",
        previous_feedback: str = ""
    ) -> dspy.Prediction:
        """Validate visualization and provide feedback.

        Args:
            task: Original user task
            code: Python code that generated the visualization
            image_path: Path to the image file
            execution_output: Console output from execution
            previous_feedback: Cumulative feedback from prior rounds

        Returns:
            Prediction with is_valid (bool), feedback (str), confidence (float)

        Raises:
            FileNotFoundError: If image_path doesn't exist
            ValueError: If vision model response is invalid
        """
        img_path = Path(image_path)
        if not img_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # NOTE: DSPy will handle image encoding internally when passing the path
        # to vision-capable LLMs. We don't need to manually encode unless using
        # a specific API that requires base64 strings.

        # Call the vision model with Chain-of-Thought reasoning
        prediction = self.critique(
            task=task,
            code=code,
            image_path=str(img_path),  # Pass path as string for vision models
            execution_output=execution_output,
            previous_feedback=previous_feedback
        )

        # Validate and normalize the is_valid field
        is_valid_str = str(prediction.is_valid).strip().upper()
        is_valid = is_valid_str in ("YES", "TRUE", "1", "VALID", "APPROVED")

        # Validate confidence score
        try:
            confidence = float(prediction.confidence)
            if not (0.0 <= confidence <= 1.0):
                confidence = 0.8  # Default if out of range
        except (ValueError, TypeError):
            confidence = 0.8  # Default if invalid

        return dspy.Prediction(
            is_valid=is_valid,
            feedback=prediction.feedback,
            confidence=confidence
        )
