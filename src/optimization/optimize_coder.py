import dspy
from src.config import get_lm
from src.modules.coder import Coder
from src.core.repl import PythonREPL
from src.core.logger import logger
from dspy.teleprompt import LabeledFewShot
import os
from pathlib import Path

# 1. Configure LM
try:
    lm = get_lm("ollama")
    dspy.settings.configure(lm=lm)
    logger.info(f"LM Configured: {lm.model}")
except Exception as e:
    logger.error(f"Error configuring LM: {e}")

# 2. Define Metric
def validate_code_execution(example, prediction, trace=None):
    repl = PythonREPL()

    # Setup mock file for this validation run if needed
    if "dataset.xlsx" in example.task:
        # Create a mock file
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["E5"] = "=SUM(A1:A5)"
        wb.save("dataset.xlsx")

    # Also create data.csv if needed
    if "data.csv" in example.task:
        with open("data.csv", "w") as f:
            f.write("col1,col2\n1,2")

    try:
        output = repl.execute(prediction.python_code)

        # Check against expected output if provided
        if hasattr(example, "expected_output"):
            return example.expected_output in output

        return "Traceback" not in output and "Error" not in output
    except Exception:
        return False
    finally:
        if os.path.exists("dataset.xlsx"):
            os.remove("dataset.xlsx")
        if os.path.exists("data.csv"):
            os.remove("data.csv")

logger.info("Metric defined.")

# 3. Create Training Set
# We add examples that specifically teach the tricky parts (Excel formulas, Search).

trainset = [
    dspy.Example(
        task="Check the formula in cell E5 of 'dataset.xlsx'.",
        context_summary="AVAILABLE FILES: [FILE] dataset.xlsx",
        reasoning="To get the formula, I need to load the workbook with openpyxl WITHOUT data_only=True (default). Then I access the cell's .value property, which contains the formula string if it is a formula.",
        python_code="import openpyxl\nwb = openpyxl.load_workbook('dataset.xlsx')\nprint(wb.active['E5'].value)",
        expected_output="=SUM(A1:A5)"
    ).with_inputs("task", "context_summary"),

    dspy.Example(
        task="Read 'data.csv' and print the columns.",
        context_summary="AVAILABLE FILES: [FILE] data.csv",
        expected_output="Columns:"
    ).with_inputs("task", "context_summary")
]

logger.info(f"Created {len(trainset)} training examples.")

# 4. Compile Coder

# Use LabeledFewShot to simply use our manual examples as demos
teleprompter = LabeledFewShot(k=2)

logger.info("Compiling with LabeledFewShot...")
coder_uncompiled = Coder()
compiled_coder = teleprompter.compile(coder_uncompiled, trainset=trainset)
logger.info("Compilation finished.")

# 5. Save the Compiled Module
project_root = Path(__file__).parent.parent.parent
save_path = project_root / "src/modules/coder_compiled.json"
compiled_coder.save(save_path)
logger.info(f"Saved compiled module to {save_path}")
