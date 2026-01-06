# Project Instructions for RLM Agent

## 🧠 Project Context & Architecture

This project implements a **Recursive Language Model (RLM)** based on MIT CSAIL's research (arXiv:2512.24601v1).
It uses **Python 3.14.2 (Free-Threaded)** and **DSPy** to build an agent that recursively solves problems by generating and executing Python code in a stateful sandbox.

### Core Architecture

The agent operates in a **recursive decision loop**:

1. **Architect** (`src/modules/architect.py`) decides: ANSWER, CODE, or DELEGATE
2. **Coder** (`src/modules/coder.py`) generates Python when CODE is chosen
3. **REPL** (`src/core/repl.py`) executes code in a persistent sandbox
4. **Responder** (`src/modules/responder.py`) formats final answers
5. **Delegator** (`src/modules/delegator.py`) spawns parallel sub-agents for DELEGATE

### Service Layer (Phase 12)

The project uses a **service layer pattern** to share business logic between CLI and Web interfaces:

- **`src/rlm/services/task_service.py`**: Orchestrates agent execution with callbacks for streaming
- **`src/rlm/services/config_service.py`**: Loads, lists, and validates configuration profiles
- **`src/rlm/services/session_service.py`**: Manages sessions with API keys (in-memory only, never persisted)

**API Key Security**: API keys are stored only in session memory. They are NEVER persisted to disk or database.

### Critical Components

- **`src/core/repl.py`**: Stateful Python sandbox. Variables MUST persist across `execute()` calls. Uses `exec()` with shared `globals`/`locals` dicts.
- **`src/core/budget.py`**: Thread-safe singleton tracking token usage per model. **CRITICAL**: Uses `threading.Lock` - Python 3.14t has true parallelism (no GIL).
- **`src/core/config_loader.py`**: YAML-based multi-model configuration. Root agent can use GPT-5, delegates use GPT-5-mini, Coder uses Ollama, etc.
- **`src/core/agent.py`**: Main orchestrator. Implements recursive delegation with depth limits. Uses Protocol-based dependency injection for testing.
- **`src/config.py`**: Model factory using `match/case`. Returns DSPy LM objects (`dspy.Google`, `dspy.OllamaLocal`, `dspy.OpenAI`).

### Directory Structure

```text
src/
  rlm/        # Core library package (Phase 12+)
    services/ # Service layer: TaskService, ConfigService, SessionService
  core/       # Infrastructure (REPL, Budget, Config, Agent orchestration)
  modules/    # DSPy Signatures and Modules (Architect, Coder, Responder, Delegator)
  optimization/  # DSPy compilation/optimization scripts (MIPROv2)
  tools/      # External capabilities (web search via DuckDuckGo)
  utils/      # Shared helpers
  web/        # Web application (Phase 13+, coming soon)
configs/      # YAML profiles (paper-gpt5.yaml, hybrid.yaml, local-only.yaml, etc.)
tests/        # Pytest suite (mirrors src structure, uses conftest.py for mocks)
```

## 🛠️ Tech Stack & Constraints

- **Python**: `3.14.2` (Free-Threaded) - GIL is removed, threads run in parallel
- **Package Manager**: `uv` (Astral's fast package manager)
- **Framework**: `DSPy` (latest) - Chain-of-Thought, optimizer-based prompt tuning
- **LLM Providers**: Gemini (via `google-generativeai`), OpenAI, Ollama (local)
- **Web Stack**: FastAPI + HTMX + Alpine.js + Tailwind (Phase 13+)
- **Persistence**: SQLite for task history (Phase 13+)
- **Concurrency**: **ALWAYS** use `threading` or `ThreadPoolExecutor`. **NEVER** use `multiprocessing` (unnecessary in 3.14t).

## 🚀 Developer Workflow

### Running the Agent

```bash
# Required format: task + --config flag
uv run python src/main.py "Calculate fibonacci(100)" --config configs/paper-gpt5.yaml

# With context (files in a directory)
uv run python src/main.py "Summarize sales.csv" --config configs/hybrid.yaml --context ./data

# With verbose task from file
uv run python src/main.py --prompt-file tasks/research.txt --config configs/high-quality.yaml
```

### Configuration Profiles

Profiles live in `configs/`. Key profiles:

- **`paper-gpt5.yaml`**: Replicates paper setup (GPT-5 root, GPT-5-mini delegates)
- **`local-only.yaml`**: Free Ollama models only (no API costs)
- **`hybrid.yaml`**: Best of both (Ollama for Coder, Gemini for Architect)
- **`cost-effective.yaml`**: Gemini 2.5 Flash everywhere

To add a new profile, copy an existing YAML and modify `root`, `delegate`, and `modules` sections.

### Dependency Management

```bash
uv add <package>      # Add dependency
uv sync               # Install/update all dependencies
uv run <command>      # Run commands in the virtual environment
```

### Testing

```bash
uv run pytest                     # Run all tests
uv run pytest tests/test_repl.py  # Run specific test file
uv run pytest -k "test_code"      # Run tests matching pattern
```

**Testing Strategy**: Unit tests use dependency injection (see `tests/conftest.py` for `MockArchitect`, `MockCoder`, etc.). Integration tests hit real LLMs (use `@pytest.mark.integration`).

### DSPy Module Compilation

Compile modules with training data to improve performance:

```bash
# Quick optimization (uses examples as demos)
uv run python src/optimization/optimize_coder.py --optimizer labeled

# Better optimization (bootstraps rationales, validates execution)
uv run python src/optimization/compile_architect.py --optimizer bootstrap

# Best optimization (instruction + demo tuning via Bayesian opt, needs 50+ examples)
uv run python src/optimization/compile_architect.py --optimizer mipro-light
```

Compiled weights saved to `src/modules/*.json` (e.g., `coder_compiled.json`).

### DSPy Optimization Best Practices

Training data lives in `src/optimization/data.py`. Key principles:

1. **Contrastive Pairs**: Include before/after pairs showing same query with different contexts:

   ```python
   # Before execution → CODE
   Example(query="What is 2+2?", data_desc="Execution History:\n", action="CODE")
   # After execution → ANSWER
   Example(query="What is 2+2?", data_desc="...Output: 4\n", action="ANSWER")
   ```

2. **Minimum Dataset Sizes**:
   - `LabeledFewShot`: 5-10 examples (just uses them as demos)
   - `BootstrapFewShot`: 10-20 examples (validates with metric)
   - `MIPROv2`: 50+ for instruction optimization, 200+ for full runs

3. **Always Use `.with_inputs()`**: Required for optimization to work:

   ```python
   Example(query="...", data_desc="...", action="CODE").with_inputs("query", "data_desc")
   ```

4. **Validation Sets for MIPROv2**: Use `split_train_val()` from `data.py` to prevent overfitting.

5. **Metrics Return Floats**: For finer-grained optimization, return 0.0-1.0 instead of bool.

## 📝 Coding Conventions

### Type Hints

- Python 3.10+ style: `list[str]`, `dict[str, Any]`. **NO** `typing.List` or `typing.Dict`.
- Use `| None` instead of `Optional`: `def foo(x: str | None) -> int:`

### Path Handling

- **ALWAYS** use `pathlib.Path`. **NEVER** use `os.path`.
- Example: `Path("configs") / "hybrid.yaml"` not `os.path.join("configs", "hybrid.yaml")`

### DSPy Module Patterns

- **Signatures**: Inherit from `dspy.Signature`, use `InputField` and `OutputField`.
- **Validation in `forward()`**: Raise `ValueError` for invalid outputs. The agent loop handles retries.
- **Compiled Modules**: Load with `load_compiled_module(self, "module_name")` in `__init__`.
- Example from `coder.py` - syntax validation:

  ```python
  try:
      ast.parse(code)
  except SyntaxError as e:
      raise ValueError(f"Syntax error: {e}")  # Caller handles retry logic
  ```

- **Note**: `dspy.Assert` was removed in DSPy 3.x. Use explicit validation + retry loops instead.

### DSPy Metrics (For Optimization)

- **Signature**: `def metric(example: dspy.Example, prediction, trace=None) -> float:`
- **Prediction Format**: Handle BOTH `Prediction` object (BootstrapFewShot) AND `dict` (SIMBA/GEPA):

  ```python
  # Handle both formats
  if isinstance(prediction, dict):
      code = prediction.get("python_code", prediction.get("code", ""))
  else:
      code = prediction.python_code  # Prediction object
  ```

- **Return Value**: Float 0.0-1.0 for fine-grained optimization. Avoid bool unless binary classification.
- **Feedback Metrics (GEPA)**: Return `{"score": float, "feedback": str}` for reflective optimization.

### Error Handling

- **In REPL**: Catch all exceptions, return `traceback.format_exc()` as string. Never crash.
- **In DSPy Modules**: Raise `ValueError` with descriptive messages. The agent's main loop handles retries.
- **Logging**: Use `logging.getLogger(__name__)`. No bare `print()` statements (except in REPL output).

### Docstrings

- Google Style: Brief summary, then `Args:`, `Returns:`, `Raises:` sections.
- Example:

  ```python
  def execute(self, code: str) -> str:
      """Executes Python code in the sandbox.

      Args:
          code: The Python code to execute.

      Returns:
          Captured stdout or error traceback.
      """
  ```

## ⚠️ Critical Implementation Details

### Phased Development

- Follow `AGILE_PLAN.md` strictly. Do NOT implement features from future phases.
- Current phase is tracked in the plan. Check before adding new features.

### Thread Safety (Python 3.14t Specific)

- **GIL is removed**: Race conditions are REAL. Use `threading.Lock` for shared state.
- **BudgetManager**: All methods use `with self._lock:` to prevent concurrent modification.
- Example pattern:

  ```python
  def add_usage(self, input_tokens: int, output_tokens: int):
      with self._lock:
          self.current_cost += calculate_cost(...)
  ```

### DSPy Configuration Context

- The agent uses **context-aware LM switching**: Root agent, delegate agents, and individual modules can use different models.
- `src/config.py`'s `get_lm_for_role()` handles this. It temporarily switches `dspy.settings.configure(lm=...)` for each role.
- **Never call `dspy.settings.configure()` in module code** - it's managed globally by `main.py` and `agent.py`.

### REPL Security

- Basic sanitization blocks `os.system`, `subprocess`. Not production-grade.
- Future: Use RestrictedPython or containerization.

### File Context Discovery

- When `--context` is provided, `src/core/explorer.py` scans the directory and generates a manifest.
- Manifest format: `[FILE] path/to/file.ext` for each file.
- Coder receives this in `context_summary` input field and can generate code to read files.

### Testing with Mocks

- `tests/conftest.py` provides `MockArchitect`, `MockCoder`, `MockREPL`, `MockResponder`.
- These are Protocol-compatible mocks. Example:

  ```python
  agent = RLMAgent(
      architect=MockArchitect(action="CODE"),
      coder=MockCoder(code="print(42)"),
      repl=MockREPL(output="42")
  )
  ```

- Use mocks for fast unit tests. Use real modules for integration tests.

### Common Pitfalls

1. **Forgetting `--config`**: Agent requires a config file. No defaults.
2. **Markdown in code**: Coder sometimes outputs ` ```python `. Strip in `coder.py`.
3. **Infinite loops**: Architect can get stuck in CODE → CODE loops. Max steps prevents runaway costs.
4. **Budget not shared**: Pass the same `BudgetManager` instance to all agents and DSPy LMs.
