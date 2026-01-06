# **RLM Agile Implementation Plan (Python 3.14.2)**

Project: Recursive Language Model (RLM) Agent
Methodology: Iterative Sprints. Strict ATest-Driven Development (TDD). Stack: Python 3.14t (Free-Threaded), uv, DSPy, pytest.

## **🏁 Phase 0: Environment & Connectivity (The Skeleton)**

**Goal:** Establish a working environment with uv, Python 3.14t, and verify we can talk to both Local (Ollama) and Cloud (Gemini) LLMs.

### **📋 Implementation Steps**

1. **Initialize Project:**
   * Install uv.
   * Run uv init rlm-agent \--python 3.14t.
   * Set up pyproject.toml with dependencies: dspy, google-generativeai, python-dotenv, pytest, pytest-asyncio.
2. **Environment Secrets:**
   * Create .env file for GEMINI\_API\_KEY.
3. **Configuration Module (src/config.py):**
   * Create a robust factory function get\_lm(provider\_name: str) using Python 3.14 match/case.
   * Support "gemini" (via dspy.Google) and "ollama" (via dspy.OllamaLocal).

### **✅ Verification (Tests)**

* **Test 0.1:** Create tests/test\_connectivity.py.
  * Write a test that requests "Hello, World" from the configured provider.
  * Assert the response is a non-empty string.
* **Command:** uv run pytest tests/test\_connectivity.py

### **🛑 Definition of Done**

* \[ \] uv sync installs without errors.
* \[ \] pytest passes for connectivity to Gemini.
* \[ \] pytest passes for connectivity to Ollama (ensure ollama serve is running).

## **🏃 Phase 1: The Safe Sandbox (The REPL)**

**Goal:** Build the engine. A robust, secure Python interpreter that maintains state (variables) across calls.

### **📋 Implementation Steps**

1. **Core REPL Class (src/core/repl.py):**
   * Class PythonREPL.
   * **State:** Initialize self.globals \= {} and self.locals \= {}.
   * **Execution:** Implement execute(code: str) \-\> str.
   * **Capture:** Use contextlib.redirect\_stdout to capture print() output.
   * **Error Handling:** Catch Exception and return the traceback as a string (don't crash the app).
2. **Sanitization (Basic):**
   * Prevent the execution of forbidden modules (e.g., os.system block \- basic level).

### **✅ Verification (Tests)**

* **Test 1.1 (Persistence):** Run x \= 10 in call 1\. Run print(x) in call 2\. Assert output is "10".
* **Test 1.2 (Syntax Errors):** Send invalid code def func( . Assert output starts with "SyntaxError".
* **Test 1.3 (Stdout):** Run print("test"). Assert return value contains "test".
* **Command:** uv run pytest tests/test\_repl.py

### **🛑 Definition of Done**

* \[ \] The REPL remembers variables between separate execute() calls.
* \[ \] Syntax errors return text descriptions, not exceptions.

## **🛡️ Phase 2: The Guardrails (Budget & Cost)**

**Goal:** Create a thread-safe safety net to prevent recursive infinite loops from draining your wallet.

### **📋 Implementation Steps**

1. **Budget Manager (src/core/budget.py):**
   * Class BudgetManager (Singleton pattern recommended).
   * **Thread Safety:** Use threading.Lock() (Critical for Python 3.14t).
   * **Methods:** add\_usage(input\_tok, output\_tok), check\_budget().
   * **Pricing:** Hardcode approximate pricing for Gemini Flash ($0.075/1M input).
2. **Integration:**
   * Create a custom DSPy Wrapper or Hook that calls budget.check\_budget() before *every* LLM request.

### **✅ Verification (Tests)**

* **Test 2.1 (Hard Stop):** Set budget to $0.0001. Simulate 2 calls. Assert BudgetExceededError is raised on the second call.
* **Test 2.2 (Thread Safety):** Spawn 50 threads that all add costs simultaneously. Verify the final total is mathematically correct (no race conditions).
* **Command:** uv run pytest tests/test\_budget.py

### **🛑 Definition of Done**

* \[ \] Budget limits physically prevent further function calls.
* \[ \] Threading tests pass on Python 3.14t.

## **🧠 Phase 3: The DSPy Modules (The Architect)**

**Goal:** Teach the LLM to write valid Python and make decisions using DSPy.

### **📋 Implementation Steps**

1. **The Coder Module (src/modules/coder.py):**
   * **Signature:** task, context\_summary \-\> python\_code.
   * **Assertion:** Use dspy.Assert to check ast.parse(code). If it fails, DSPy backtracks.
2. **The Architect Module (src/modules/architect.py):**
   * **Signature:** query, data\_desc \-\> action.
   * **Actions:** Enum \[ANSWER, CODE, DELEGATE\].
   * **Few-Shot:** Create 3 examples of when to code vs. when to just answer.

### **✅ Verification (Tests)**

* **Test 3.1 (Valid Code):** Ask Coder to "Calculate the 10th Fibonacci number". Assert ast.parse(result) passes.
* **Test 3.2 (Decision Making):** Ask Architect "What is 2+2?" (Expect CODE or ANSWER). Ask "Summarize this 1MB file" (Expect DELEGATE).
* **Command:** uv run pytest tests/test\_dspy\_modules.py

### **🛑 Definition of Done**

* \[ \] The Coder module recovers from syntax errors automatically using DSPy assertions.
* \[ \] The Architect makes logical routing decisions.

## **🔄 Phase 4: Recursion & Integration (The Loop)**

**Goal:** Connect the Brain (DSPy) to the Hands (REPL). Build the main.py loop.

### **📋 Implementation Steps**

1. **The Recursive Controller (src/main.py):**
   * Implement Agent.run(task, context\_pointer).
   * **Step 1:** Architect decides strategy.
   * **Step 2 (If Code):** Generate code \-\> Execute in REPL \-\> Observe Output \-\> Repeat.
   * **Step 3 (If Delegate):** (Stub for now) Just print "Delegating".
2. **Context Management:**
   * Pass the REPL's output back into the DSPy context for the next turn.

### **✅ Verification (Tests)**

* **Test 4.1 (End-to-End Simple):** "Create a list of numbers 1 to 10 and calculate their sum."
  * Verify the REPL execution returns "55".
  * Verify the final LLM answer says "55".
* **Command:** uv run python src/main.py \--task "Test Task"

### **🛑 Definition of Done**

* [x] The Agent can self-correct a Python script based on REPL errors.
* [x] Simple multi-step math/logic tasks work autonomously.

## **🚀 Phase 5: Parallelism & Sub-Agents (3.14t Power)**

**Goal:** Implement the DELEGATE action using true parallelism.

### **📋 Implementation Steps**

1. **Sub-Agent Spawning:**
   * When Architect chooses DELEGATE:
     * Split the data (e.g., text chunks).
     * Use asyncio.TaskGroup or concurrent.futures.ThreadPoolExecutor (Python 3.14t optimized).
     * Spawn new Agent.run() instances for each chunk.
2. **Aggregation:**
   * Collect results from all threads.
   * Pass summarized results back to the parent agent.

### **✅ Verification (Tests)**

* **Test 5.1 (Parallelism):** Task "Wait 2 seconds" spawned 3 times.
  * Total execution time should be \~2 seconds (Parallel), not 6 seconds (Sequential).
* **Test 5.2 (Recursion Depth):** Ensure max\_depth parameter prevents infinite spawning.

### **🛑 Definition of Done**

* [x] Sub-agents run in parallel.
* [x] BudgetManager tracks costs across all threads correctly.
* [x] System handles a large text summary by splitting it.

## **📚 Phase 6: External Context & Document Ingestion**

**Goal:** Allow the Agent to discover and read external files via the REPL (Tool-Use), efficiently extending context.

### **📋 Implementation Steps**

1. **Dependency Installation**:
    * Install libraries required for the *REPL* to read files: `pandas`, `openpyxl`, `pypdf`, `python-docx`.
2. **File Explorer (`src/core/explorer.py`):**
    * Implement `scan_directory(path: Path) -> str`.
    * Returns a tree-like text structure or list of available files and their paths.
    * Does **NOT** load content.
3. **Context Integration:**
    * Update `RLMAgent.__init__` to accept `root_dir`.
    * Call `explorer.scan_directory` and inject the *file list* into `data_desc`.
    * **Crucial:** Ensure Prompts know that to *know* the content, they must generate code to *read* the content.

### **✅ Verification (Tests)**

* **Test 6.1 (Explorer):** Point to a temp folder and verify the string output lists files correctly.
* **Test 6.2 (REPL Read):** Agent is given a folder with `secret.txt`. Task: "What is the secret?".
  * Expectation: Agent generates `open('secret.txt').read()`, executes it, sees the secret in REPL output, and answers.

### **🛑 Definition of Done**

* [x] REPL environment has necessary libraries.
* [x] Agent receives file paths in context, not content.
* [x] Agent successfully writes code to read a file and answer a question based on it.

## **🧠 Phase 7: Optimization with DSPy Compilation**

**Goal:** Use `dspy.compile` (MIPRO or BootstrapFewShot) to stop infinite loops and improve reasoning by learning from examples instead of manual prompt engineering.

### **📋 Implementation Steps**

1. **Training Data Construction (`src/optimization/data.py`):**
    * Create a dataset of `(task, context_state) -> action` examples.
    * Crucially include examples where context *already has the answer*, labeled as `ANSWER`.
2. **Optimization Script (`src/optimization/compile_architect.py`):**
    * Initialize `teleprompter = BootstrapFewShot(metric=validate_action)`.
    * Compile the `Architect` module.
    * Save the optimized program to `src/modules/compiled_architect.json`.
3. **Integration:**
    * Update `Architect.__init__` to load the compiled JSON if it exists.

### **✅ Verification (Tests)**

* **Test 7.1:** Run the "First line of README" task. Verify it stops after reading.
* **Test 7.2:** Run the optimization script and verify a JSON file is produced.

### **🛑 Definition of Done**

* [x] `compile_architect.py` runs successfully.
* [x] Agent loads optimized weights.
* [x] Infinite loop on file reading is resolved (Validated with `qwen2.5-coder`).

## **🛠️ Phase 8: Enhanced Tooling & Retrieval**

**Goal:** Equip the REPL with specialized libraries for complex document processing (Excel, PDF) and Web Search, enabling the Agent to handle real-world information retrieval tasks.

### **📋 Implementation Steps**

1. **Dependency Updates:**
    * Add primary libraries: `openpyxl` (Excel), `pdfplumber` (PDF Tables), `chromadb` (Semantic Search), `duckduckgo-search` (Web).
2. **REPL Preloading (`src/core/repl.py`):**
    * Ensure these libraries are importable.
    * (Optional) Pre-import helper functions if simplifying usage is needed (e.g., a `search_web(query)` wrapper around DDGS).
3. **Search Module (`src/tools/search.py`):**
    * Implement a simple wrapper for `duckduckgo-search` to handle rate limits/errors gracefully.
4. **Coder Training:**
    * Update `src/modules/coder.py` few-shot examples to demonstrate using `pdfplumber` for tables and `openpyxl` for formulas.

### **✅ Verification (Tests)**

* **Test 8.1 (Excel):** Given an .xlsx file with a formula, Agent must read the *formula* (using openpyxl), not just the value.
* **Test 8.2 (PDF Table):** Given a PDF with a table, Agent must extract it as a list of lists or DataFrame.
* **Test 8.3 (Web Search):** Agent "Who is the current president of France?" -> Uses DDGS -> Answers correctly.

### **🛑 Definition of Done**

* [x] REPL has access to `openpyxl`, `pdfplumber`, `chromadb`, `duckduckgo-search`.
* [ ] Agent can autonomously extract tables from PDFs.
* [x] Agent can perform live web searches.

## **📝 Phase 9: Logging Infrastructure**

**Goal:** Replace all `print()` statements with Python's `logging` module for production-grade observability.

### **📋 Implementation Steps**

1. **Logger Module (`src/core/logger.py`):**
    * Create `setup_logger()` factory with console and file handlers.
    * Support DEBUG, INFO levels.
    * Each run creates a timestamped log file in `logs/`.
2. **Codebase Migration:**
    * Replace `print()` with `logger.info()` / `logger.debug()` across all modules.
3. **Git Configuration:**
    * Add `logs/` and `*.log` to `.gitignore`.

### **✅ Verification (Tests)**

* **Test 9.1:** Run agent and verify log file is created in `logs/`.
* **Test 9.2:** Verify log contains expected INFO/DEBUG entries.

### **🛑 Definition of Done**

* [x] All `print()` replaced with `logging`.
* [x] Log files generated per run.
* [x] `logs/` gitignored.

---

## **🏗️ Phase 10: Architecture Refactoring (PROPOSED - PENDING APPROVAL)**

**Goal:** Improve maintainability, testability, and performance by applying proven design patterns and addressing technical debt.

### **🔍 Current Architecture Analysis**

| Component | Current Pattern | Issues Identified |
|-----------|-----------------|-------------------|
| `BudgetManager` | Singleton + `__new__` | Re-initialization guard is fragile; singleton complicates testing |
| `RLMAgent` | God Object | Creates all dependencies internally; hard to test in isolation |
| DSPy Modules | Hardcoded demos | Demos duplicated between code and compiled JSON |
| `Logger` | Module-level singleton | Creates file on import; problematic for testing |
| `test_parallel.py` | Integration test | Relies on LLM behavior; times out frequently (120s) |

### **📋 Proposed Refactoring Items**

#### **10.1: Dependency Injection for RLMAgent**

* **Current:** Agent creates `Architect`, `Coder`, `Responder`, `Delegator`, `REPL` internally.
* **Proposed:** Accept these as constructor parameters with sensible defaults.
* **Benefit:** Enables mocking for unit tests, improves testability.
* **Risk:** Low - backward compatible with default instantiation.

#### **10.2: Protocol-Based Abstractions**

* **Current:** Direct class dependencies between components.
* **Proposed:** Define `Protocol` classes for `LMProvider`, `CodeExecutor`, `TaskRouter`.
* **Benefit:** Enables swapping implementations (e.g., mock REPL for tests).
* **Risk:** Medium - requires interface definitions.

#### **10.3: Lazy Logger Initialization**

* **Current:** `logger = setup_logger()` runs at import time, creating log files.
* **Proposed:** Use lazy initialization or context-based logger setup.
* **Benefit:** Prevents spurious log files during testing/imports.
* **Risk:** Low.

#### **10.4: BudgetManager Refactoring**

* **Current:** Singleton with `__new__` override + `_initialized` flag.
* **Proposed:** Use a proper singleton decorator or dependency injection.
* **Benefit:** Cleaner code, easier reset for tests.
* **Risk:** Low.

#### **10.5: Test Improvements**

* **Current:** `test_parallel.py` depends on LLM correctly choosing DELEGATE.
* **Proposed:**
  * Mock the `Architect` to force DELEGATE action.
  * Add unit tests for delegation logic separate from LLM integration.
* **Benefit:** Reliable CI, faster tests.
* **Risk:** Low.

#### **10.6: Compiled Module Loading Strategy**

* **Current:** Modules check for compiled JSON in `__init__`.
* **Proposed:** Centralize compiled module discovery in `config.py` or a dedicated loader.
* **Benefit:** Single source of truth for optimization artifacts.
* **Risk:** Low.

### **✅ Pre-Refactoring Test Coverage Requirements**

Before implementing any refactoring:

* [ ] `test_agent.py`: Add unit tests for each action branch (CODE, ANSWER, DELEGATE)
* [ ] `test_budget.py`: Ensure singleton reset works correctly ✅ (exists)
* [ ] `test_repl.py`: Cover edge cases ✅ (exists)
* [ ] Add mocking infrastructure in `conftest.py` for DSPy modules

### **📊 Current Test Coverage Summary**

| Module | Tests | Status |
|--------|-------|--------|
| `src/core/repl.py` | `test_repl.py` | ✅ Good |
| `src/core/budget.py` | `test_budget.py` | ✅ Good |
| `src/core/agent.py` | `test_agent.py`, `test_tools.py` | ⚠️ Integration only |
| `src/modules/*.py` | `test_dspy_modules.py` | ⚠️ LLM-dependent |
| `src/tools/search.py` | `test_tools.py` | ✅ Good |

### **🛑 Definition of Done**

* [x] All refactoring items approved by stakeholder.
* [x] Unit test coverage added before refactoring.
* [x] Each refactoring item implemented incrementally with passing tests.
* [x] No regression in existing functionality.

### **⏳ Estimated Effort**

| Item | Effort | Priority | Status |
|------|--------|----------|--------|
| 10.1 Dependency Injection | 2h | High | ✅ Complete |
| 10.2 Protocol Abstractions | 4h | Medium | ✅ Complete |
| 10.3 Lazy Logger | 1h | Low | ✅ Complete |
| 10.4 BudgetManager Cleanup | 1h | Medium | ✅ Complete |
| 10.5 Test Improvements | 3h | High | ✅ Complete |
| 10.6 Compiled Module Loader | 2h | Low | ✅ Complete |

---

**✅ Phase 10 Complete!** All refactoring items have been implemented and verified.

---

## **⚙️ Phase 11: YAML Configuration Profiles (Paper-Inspired Multi-Model Setup)**

**Goal:** Implement a flexible YAML-based configuration system that allows different models for different modules (root vs. sub-agents), inspired by the paper's use of GPT-5 for root and GPT-5-mini for recursive calls. Enable users to create reusable configuration profiles for different task types (cost-effective, high-quality, etc.).

### **📚 Research Context**

From the RLM paper (arXiv:2512.24601v1):
> "For the GPT-5 experiments, we use GPT-5-mini for the recursive LMs and GPT-5 for the root LM, as we found this choice to strike a powerful tradeoff between the capabilities of RLMs and the cost of the recursive calls."

This demonstrates the value of:

* **Asymmetric model allocation**: Use cheaper/faster models for sub-calls
* **Role-based model selection**: Different models for Architect, Coder, Delegator
* **Profile-based configuration**: Different setups for different task types

### **📋 Implementation Steps**

#### **11.1: YAML Configuration Schema Design**

Create `src/core/config_loader.py` with a schema for:

```yaml
# Example: configs/cost-effective.yaml
profile_name: "Cost-Effective Profile"
description: "Optimized for low cost, suitable for simple tasks"

# Root agent configuration (with per-model pricing)
root:
  provider: gemini
  model: gemini-2.0-flash
  max_steps: 10
  max_depth: 3
  pricing:
    input_per_1m: 0.075   # $0.075 per 1M input tokens
    output_per_1m: 0.30   # $0.30 per 1M output tokens

# Sub-agent configuration (with its own pricing)
delegate:
  provider: gemini
  model: gemini-2.0-flash
  max_steps: 5
  max_depth: 0
  pricing:
    input_per_1m: 0.075
    output_per_1m: 0.30

# Per-module model overrides (optional, each with pricing)
modules:
  architect:
    provider: gemini
    model: gemini-2.0-flash
    pricing:
      input_per_1m: 0.075
      output_per_1m: 0.30
  coder:
    provider: ollama
    model: qwen2.5-coder:7b
    pricing:
      input_per_1m: 0.0   # Local model = free
      output_per_1m: 0.0

# Global budget limit (sum of all model costs)
budget:
  max_usd: 1.0  # Total spending limit across ALL models

# DSPy configuration
dspy:
  max_retries: 3
  cache_enabled: true
```

**Key Features:**

* **Per-Model Pricing**: Each model config has its own `pricing` block
* **Global Budget Limit**: Single `max_usd` applies to sum of all model costs
* **Hierarchical**: root vs. delegate configuration
* **Per-Module Overrides**: Different models for Architect, Coder, etc.
* **Profile Inheritance**: Support `extends: base-config.yaml`
* **Environment Variable Substitution**: `${GEMINI_API_KEY}`

#### **11.2: Enhanced BudgetManager for Multi-Model Tracking**

**Current Limitation:** Single `input_price_per_1m` / `output_price_per_1m` for all models.

**New Design:**

```python
@singleton
class BudgetManager:
    def __init__(self, max_budget: float = 1.0):
        self.max_budget = max_budget
        self.current_cost = 0.0
        self._lock = threading.Lock()

        # Per-model tracking
        self.model_usage: dict[str, ModelUsage] = {}

    def register_model(self, model_id: str, input_price: float, output_price: float):
        """Register a model with its pricing info."""
        with self._lock:
            self.model_usage[model_id] = ModelUsage(
                input_price_per_1m=input_price,
                output_price_per_1m=output_price,
                total_input_tokens=0,
                total_output_tokens=0,
                total_cost=0.0
            )

    def add_usage(self, model_id: str, input_tokens: int, output_tokens: int):
        """Track usage for a specific model with its pricing."""
        with self._lock:
            usage = self.model_usage.get(model_id)
            if usage is None:
                raise ValueError(f"Model {model_id} not registered. Call register_model first.")

            input_cost = (input_tokens / 1_000_000) * usage.input_price_per_1m
            output_cost = (output_tokens / 1_000_000) * usage.output_price_per_1m
            cost = input_cost + output_cost

            usage.total_input_tokens += input_tokens
            usage.total_output_tokens += output_tokens
            usage.total_cost += cost
            self.current_cost += cost

    def get_breakdown(self) -> dict[str, float]:
        """Get cost breakdown by model."""
        with self._lock:
            return {model_id: u.total_cost for model_id, u in self.model_usage.items()}


@dataclass
class ModelUsage:
    input_price_per_1m: float
    output_price_per_1m: float
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
```

**Benefits:**

* Accurate cost tracking per model
* Single global budget limit still enforced
* Detailed breakdown for cost analysis
* Thread-safe for concurrent model calls

#### **11.3: Configuration Loader Implementation**

**File:** `src/core/config_loader.py`

**Classes:**

* `ModelConfig`: Provider, model name, pricing info
* `AgentConfig`: max_steps, max_depth
* `ProfileConfig`: Root, delegate, modules, global budget
* `ConfigLoader`: Loads YAML, validates, resolves inheritance

**Functions:**

* `load_profile(path: Path) -> ProfileConfig`
* `merge_with_env(config: ProfileConfig) -> ProfileConfig`  # Override with .env
* `validate_config(config: ProfileConfig) -> bool`
* `register_models_with_budget(config: ProfileConfig, budget_manager: BudgetManager)`

**Error Handling:**

* Missing required fields → helpful error messages
* Invalid model names → suggest alternatives
* Missing API keys → point to .env setup
* Missing pricing info → use provider defaults with warning

#### **11.4: Update `config.py` for Multi-Model Support**

**Current:** `get_lm(provider, model_name)` returns a single LM.

**New:** `get_lm_for_role(role: str, config: ProfileConfig) -> dspy.LM`

**Roles:**

* `"root"`: Main agent LM
* `"delegate"`: Sub-agent LM
* `"architect"`: Architect module LM
* `"coder"`: Coder module LM
* `"responder"`: Responder module LM
* `"delegator"`: Delegator module LM

**Logic:**

1. Check if `config.modules.{role}` exists → use that
2. Else if role is delegate → use `config.delegate`
3. Else → use `config.root`
4. Register model with `BudgetManager` using its pricing info

#### **11.5: Modify `RLMAgent` to Accept Profile**

**Current Constructor:**

```python
def __init__(self, max_steps=10, max_depth=3, ...)
```

**New Constructor:**

```python
def __init__(
    self,
    max_steps=10,
    max_depth=3,
    config: ProfileConfig | None = None,
    is_delegate: bool = False,  # Identifies sub-agents
    ...
)
```

**Behavior:**

* If `config` is provided, use it to configure modules
* If `is_delegate=True`, use `config.delegate` settings
* Create sub-agents with `is_delegate=True`

#### **11.5: Update DSPy Module Initialization**

**Current:** All modules use `dspy.settings.configure(lm=lm)` globally.

**New:** Each module gets its own LM instance:

```python
# In Architect.__init__
self.lm = get_lm_for_role("architect", config)
with dspy.context(lm=self.lm):
    self.decide = dspy.ChainOfThought(ArchitectSignature)
```

**Challenge:** DSPy 3.x uses global settings. Need to either:

* Use `dspy.context()` context manager per module
* OR create separate DSPy programs per module

#### **11.6: CLI Integration**

**Update `main.py`:**

```python
parser.add_argument(
    "--config",
    type=Path,
    help="Path to YAML configuration file (e.g., configs/high-quality.yaml)"
)
```

**Behavior:**

1. If `--config` provided, load profile
2. CLI args override profile (e.g., `--max-steps 20`)
3. `.env` provides API keys (not in YAML for security)

**Backward Compatibility:**

* If no `--config`, use current .env + CLI args behavior

#### **11.7: Create Example Configuration Profiles**

Create `configs/` directory with:

**`configs/cost-effective.yaml`**

* Gemini Flash for everything
* Low max_steps, shallow depth
* $0.50 budget

**`configs/high-quality.yaml`** (Paper-inspired)

* GPT-4o for root
* GPT-4o-mini for delegates
* Higher budget, more steps

**`configs/local-only.yaml`**

* Ollama qwen2.5-coder for all roles
* No budget limits (local is free)

**`configs/hybrid.yaml`** (Best of both worlds)

* Ollama for Coder (fast local code generation)
* Gemini for Architect/Responder (better reasoning)
* GPT-4o-mini for Delegator

### **✅ Verification (Tests)**

**Test 11.1: Configuration Loading**

```python
def test_load_valid_profile():
    config = load_profile("configs/cost-effective.yaml")
    assert config.root.provider == "gemini"
    assert config.budget.max_usd == 0.50
    assert config.root.pricing.input_per_1m == 0.075
```

**Test 11.2: Profile Inheritance**

```python
def test_profile_extends():
    # configs/derived.yaml extends configs/base.yaml
    config = load_profile("configs/derived.yaml")
    assert config.root.provider == "gemini"  # From base
    assert config.budget.max_usd == 2.0      # Overridden
```

**Test 11.3: Multi-Model Budget Tracking**

```python
def test_per_model_budget_tracking():
    budget = BudgetManager(max_budget=10.0)
    BudgetManager._clear()  # Reset singleton
    budget = BudgetManager(max_budget=10.0)

    # Register two models with different pricing
    budget.register_model("gpt-4o", input_price=2.50, output_price=10.00)
    budget.register_model("gpt-4o-mini", input_price=0.15, output_price=0.60)

    # Add usage for each model
    budget.add_usage("gpt-4o", input_tokens=100_000, output_tokens=10_000)
    budget.add_usage("gpt-4o-mini", input_tokens=500_000, output_tokens=50_000)

    # GPT-4o: (100K/1M * 2.50) + (10K/1M * 10.00) = 0.25 + 0.10 = 0.35
    # GPT-4o-mini: (500K/1M * 0.15) + (50K/1M * 0.60) = 0.075 + 0.03 = 0.105
    # Total: 0.455

    breakdown = budget.get_breakdown()
    assert abs(breakdown["gpt-4o"] - 0.35) < 0.001
    assert abs(breakdown["gpt-4o-mini"] - 0.105) < 0.001
    assert abs(budget.current_cost - 0.455) < 0.001
```

**Test 11.4: Budget Limit Across Models**

```python
def test_budget_limit_sums_all_models():
    BudgetManager._clear()
    budget = BudgetManager(max_budget=0.50)

    budget.register_model("expensive", input_price=10.0, output_price=40.0)
    budget.register_model("cheap", input_price=0.1, output_price=0.4)

    # Add usage that exceeds budget when combined
    budget.add_usage("expensive", input_tokens=40_000, output_tokens=5_000)  # $0.60

    with pytest.raises(BudgetExceededError):
        budget.check_budget()
```

**Test 11.5: Multi-Model Agent**

```python
def test_agent_uses_different_models():
    config = load_profile("configs/hybrid.yaml")
    agent = RLMAgent(config=config)

    # Verify Architect uses Gemini
    assert agent.architect.lm.model.startswith("gemini/")

    # Verify Coder uses Ollama
    assert agent.coder.lm.model.startswith("ollama/")
```

**Test 11.6: Delegate Model Separation**

```python
def test_delegate_uses_cheaper_model():
    config = load_profile("configs/high-quality.yaml")
    root_agent = RLMAgent(config=config, is_delegate=False)
    sub_agent = RLMAgent(config=config, is_delegate=True)

    # Root uses GPT-4o
    assert "gpt-4o" in root_agent.architect.lm.model

    # Delegate uses GPT-4o-mini
    assert "gpt-4o-mini" in sub_agent.architect.lm.model
```

**Test 11.7: CLI Override**

```python
def test_cli_overrides_config(capsys):
    # Run with config but override max_steps
    result = run_cli([
        "test task",
        "--config", "configs/cost-effective.yaml",
        "--max-steps", "20"
    ])
    # Agent should use 20 steps, not 10 from config
```

### **🛑 Definition of Done**

* [x] YAML schema defined with per-model pricing
* [x] `BudgetManager` enhanced for multi-model tracking
* [x] `ConfigLoader` class implemented with tests
* [x] `get_lm_for_role()` supports per-module models with pricing
* [x] `RLMAgent` accepts and uses `ProfileConfig`
* [x] At least 4 example profiles created with pricing
* [x] CLI `--config` flag working

---

**✅ Phase 11 Complete!** YAML configuration profiles with per-model pricing have been implemented and verified.

* [ ] All tests passing (unit + integration)
* [ ] Documentation updated in README.md
* [ ] Backward compatibility maintained (old .env method still works)

### **📊 Benefits**

| Benefit | Description |
|---------|-------------|
| **Accurate Cost Tracking** | Each model tracked with its own pricing, summed to global budget |
| **Cost Optimization** | Use expensive models only where needed (root), cheap for sub-calls |
| **Cost Transparency** | `get_breakdown()` shows exactly which model cost what |
| **Task-Specific Tuning** | Different profiles for research, coding, data analysis |
| **Reproducibility** | Share YAML configs for exact replication of results |
| **Experimentation** | Easily A/B test different model combinations |
| **Paper Alignment** | Implements the paper's GPT-5 + GPT-5-mini strategy |

### **⏱️ Estimated Effort**

| Task | Effort | Priority | Dependencies |
|------|--------|----------|--------------|
| 11.1 Schema Design (with pricing) | 1h | High | None |
| 11.2 Enhanced BudgetManager | 2h | High | 11.1 |
| 11.3 ConfigLoader | 3h | High | 11.1, 11.2 |
| 11.4 Multi-Model config.py | 2h | High | 11.2, 11.3 |
| 11.5 Agent Profile Support | 2h | High | 11.4 |
| 11.6 DSPy Module LM Scoping | 4h | Medium | 11.5 |
| 11.7 CLI Integration | 1h | Medium | 11.5 |
| 11.8 Example Profiles | 2h | Low | All above |
| Testing & Docs | 3h | High | All above |

**Total Estimated Time:** ~20 hours

### **🚧 Implementation Notes**

1. **DSPy Context Management**: DSPy 3.x may require `dspy.context()` for per-module LMs. Test this thoroughly.
2. **API Key Security**: YAML files should NEVER contain API keys. Use `${ENV_VAR}` syntax.
3. **Validation**: Fail fast with helpful errors if config is invalid.
4. **Caching**: Consider caching loaded profiles to avoid repeated YAML parsing.
5. **Per-Model Budget Tracking**:
   * Each model registered with its own pricing info
   * `add_usage(model_id, input_tokens, output_tokens)` calculates cost per-model
   * Global `current_cost` sums all model costs
   * `check_budget()` enforces single global limit
   * `get_breakdown()` returns per-model cost analysis

**Per-Model Pricing Example:**

```yaml
# paper-gpt5.yaml - each model has its own pricing:
root:
  model: gpt-4o
  pricing:
    input_per_1m: 2.50   # $2.50 per 1M input tokens
    output_per_1m: 10.00

delegate:
  model: gpt-4o-mini
  pricing:
    input_per_1m: 0.15   # Much cheaper!
    output_per_1m: 0.60

budget:
  max_usd: 5.0  # Global limit applies to SUM of all model costs
```

**Cost Calculation Flow:**

```
1. Agent uses GPT-4o (Architect): 100K in, 10K out
   → Cost: (100K/1M × $2.50) + (10K/1M × $10.00) = $0.35

2. Delegate uses GPT-4o-mini (Coder): 200K in, 50K out
   → Cost: (200K/1M × $0.15) + (50K/1M × $0.60) = $0.06

3. Total: $0.35 + $0.06 = $0.41

4. Budget check: $0.41 < $5.00 ✅
```

### **📈 Success Metrics**

* [ ] Can run: `uv run python src/main.py "task" --config configs/high-quality.yaml`
* [ ] Root agent uses different model than sub-agents
* [ ] Budget tracking works across all models
* [ ] Configuration reduces from 5+ CLI args to 1 (the YAML path)

---

**🎯 Phase 11 Status: PROPOSED - AWAITING APPROVAL**
