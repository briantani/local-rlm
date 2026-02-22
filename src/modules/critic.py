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
    MANDATORY CHECKS:
    1. Title: Is there a clear, descriptive title?
    2. Axes: Are X and Y axes clearly labeled with units (if applicable)?
    3. Legend: Is a legend present (if multiple series)? Is it placed without obscuring data?
    4. Readability: Are fonts large enough? Is there a grid (if helpful)?
    5. Aesthetics: Are colors distinct and accessible? Is the layout uncrowded?

    If ANY of these are missing or poor, set is_valid to NO and provide specific Python code fixes in the feedback.

    CRITICAL: Code suggestions must be RestrictedPython-safe:
    - NO import statements (matplotlib, pandas, etc. are pre-loaded as plt, pd)
    - NO .format() string method - use f-strings: f"{x}" not "{}".format(x)
    - NO underscore variables (__name__, __file__, __import__)
    - NO pd.read_csv parameters that trigger imports (e.g., on_bad_lines, error_bad_lines)
    - Keep suggestions simple: plt.xlabel(), plt.title(), plt.legend(), etc.
    """
    task = dspy.InputField(desc="Original user task/query that required the visualization")
    code = dspy.InputField(desc="Python code that generated the visualization")
    image_path = dspy.InputField(desc="Path to the generated image file")
    execution_output = dspy.InputField(desc="Console output from code execution", default="")
    previous_feedback = dspy.InputField(desc="Feedback from previous refinement rounds", default="")

    is_valid = dspy.OutputField(desc="YES if visualization meets ALL quality standards, NO if refinement needed")
    feedback = dspy.OutputField(desc="Detailed critique with specific Python code suggestions (e.g., plt.xlabel, plt.legend(loc='best'))")
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
                task="Plot the sine wave and cosine wave",
                code="plt.plot(x, np.sin(x))\nplt.plot(x, np.cos(x))\nplt.savefig('waves.png')",
                image_path="/path/to/waves.png",
                execution_output="Chart saved",
                previous_feedback="",
                is_valid="NO",
                feedback="Missing title, axis labels, and legend. \nFix (RestrictedPython-safe):\n1. Add plt.title('Sine and Cosine Waves')\n2. Add plt.xlabel('Angle (radians)') and plt.ylabel('Amplitude')\n3. Add plt.legend(['Sine', 'Cosine'])\nDo NOT suggest import statements or .format() methods.",
                confidence="0.95"
            ).with_inputs("task", "code", "image_path", "execution_output", "previous_feedback"),

            dspy.Example(
                task="Show the distribution of age groups",
                code="plt.hist(ages, bins=10)\nplt.title('Age Distribution')\nplt.savefig('hist.png')",
                image_path="/path/to/hist.png",
                execution_output="Chart saved",
                previous_feedback="",
                is_valid="NO",
                feedback="Good start, but missing axis labels. \nFix:\n1. Add plt.xlabel('Age Group')\n2. Add plt.ylabel('Frequency')\n3. Consider adding plt.grid(axis='y', alpha=0.5) for better readability.\nNote: Only suggest matplotlib functions, no imports or advanced pandas parameters.",
                confidence="0.9"
            ).with_inputs("task", "code", "image_path", "execution_output", "previous_feedback"),

            dspy.Example(
                task="Compare sales across 3 regions over time",
                code="plt.figure(figsize=(10, 6))\nfor r in regions: plt.plot(data[r])\nplt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')\nplt.title('Regional Sales Over Time')\nplt.xlabel('Year')\nplt.ylabel('Revenue ($M)')\nplt.savefig('sales.png')",
                image_path="/path/to/sales.png",
                execution_output="Chart saved",
                previous_feedback="Round 1 Critique: Legend was obscuring data lines. Added bbox_to_anchor, axis labels, and figure size.",
                is_valid="YES",
                feedback="Excellent! All improvements from Round 1 are implemented. Legend is outside the plot, axes are labeled with units, and figure is properly sized.",
                confidence="0.98"
            ).with_inputs("task", "code", "image_path", "execution_output", "previous_feedback"),

            dspy.Example(
                task="Visualize correlation between GDP and Life Expectancy",
                code="plt.scatter(gdp, life_exp)\nplt.xlabel('GDP per Capita')\nplt.ylabel('Life Expectancy (Years)')\nplt.title('GDP vs Life Expectancy')\nplt.grid(True)\nplt.savefig('scatter.png')",
                image_path="/path/to/scatter.png",
                execution_output="Chart saved",
                previous_feedback="",
                is_valid="YES",
                feedback="Excellent. The chart has a clear title, appropriate axis labels with units, and a grid. The scatter plot is the correct choice for correlation.",
                confidence="1.0"
            ).with_inputs("task", "code", "image_path", "execution_output", "previous_feedback"),

            dspy.Example(
                task="Create a bar chart of quarterly sales data",
                code="plt.figure(figsize=(10, 6))\nquarters = ['Q1', 'Q2', 'Q3', 'Q4']\nsales = [120, 150, 180, 210]\nplt.bar(quarters, sales, color='steelblue', edgecolor='black')\nplt.title('Quarterly Sales Performance', fontsize=14, fontweight='bold')\nplt.xlabel('Quarter', fontsize=12)\nplt.ylabel('Sales ($M)', fontsize=12)\nplt.grid(axis='y', alpha=0.3)\nplt.savefig('sales_bar.png')",
                image_path="/path/to/sales_bar.png",
                execution_output="Chart saved",
                previous_feedback="",
                is_valid="YES",
                feedback="Well structured bar chart! Clear title with font weight, properly labeled axes with units, grid on Y-axis for readability, and appropriate color scheme with edge contrast.",
                confidence="0.96"
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
        # Check for negation words first (strict interpretation)
        if any(neg in is_valid_str for neg in ("NO", "NEEDS", "SHOULD", "MISSING", "LACKS", "LACK", "IMPROVEMENT")):
            is_valid = False
        else:
            # Accept explicit YES or close variants
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
