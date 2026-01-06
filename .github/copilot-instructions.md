# Project Instructions for RLM Agent

## 🧠 Project Context & Architecture
This project implements a **Recursive Language Model (RLM)** using **Python 3.14.2 (Free-Threaded)** and **DSPy**.
The goal is to build an agent that can recursively solve problems by generating and executing Python code in a stateful sandbox.

### Core Components
- **`src/core/repl.py`**: A stateful, secure Python sandbox. Must persist variables between `execute()` calls.
- **`src/core/budget.py`**: A thread-safe singleton for tracking token usage. **CRITICAL**: Must use `threading.Lock` due to Python 3.14t's true parallelism.
- **`src/modules/`**: DSPy modules (e.g., `Coder`, `Architect`). Use `dspy.Assert` for self-correction loops.

### Directory Structure
```text
src/
  core/       # Infrastructure (REPL, Budget, Config)
  modules/    # DSPy Signatures and Modules
  utils/      # Shared helpers
tests/        # Pytest suite (mirrors src structure)
```

## 🛠️ Tech Stack & Constraints
- **Python**: `3.14.2` (Free-Threaded).
- **Package Manager**: `uv`.
- **Framework**: `DSPy` (latest).
- **Concurrency**: **ALWAYS** use `threading` or `ThreadPoolExecutor`. **NEVER** use `multiprocessing` (threads are parallel in 3.14t).

## 🚀 Developer Workflow
- **Dependency Management**:
  - Add package: `uv add <package>`
  - Sync environment: `uv sync`
- **Testing**:
  - Run all tests: `uv run pytest`
  - Run specific test: `uv run pytest tests/test_repl.py`
- **Execution**:
  - Run script: `uv run python src/main.py`

## 📝 Coding Conventions
- **Type Hints**: Python 3.10+ style (`list[str]`, `dict[str, Any]`). No `typing.List`.
- **Path Handling**: Use `pathlib.Path` exclusively. No `os.path`.
- **Docstrings**: Google Style.
- **Error Handling**:
  - In REPL: Catch exceptions and return tracebacks as strings (don't crash).
  - In DSPy: Use `dspy.Assert` to retry on failure.
- **Logging**: Use Python's `logging` module. No `print()` statements.

## ⚠️ Critical Implementation Details
- **Phased Development**: Follow `AGILE_PLAN.md`. Do not implement features from future phases.
- **Thread Safety**: Since Python 3.14t removes the GIL, race conditions are real. Protect shared state (like `BudgetManager`) with locks.