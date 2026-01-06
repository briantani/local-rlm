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

1.  **Dependency Installation**:
    *   Install libraries required for the *REPL* to read files: `pandas`, `openpyxl`, `pypdf`, `python-docx`.
2.  **File Explorer (`src/core/explorer.py`):**
    *   Implement `scan_directory(path: Path) -> str`.
    *   Returns a tree-like text structure or list of available files and their paths.
    *   Does **NOT** load content.
3.  **Context Integration:**
    *   Update `RLMAgent.__init__` to accept `root_dir`.
    *   Call `explorer.scan_directory` and inject the *file list* into `data_desc`.
    *   **Crucial:** Ensure Prompts know that to *know* the content, they must generate code to *read* the content.

### **✅ Verification (Tests)**

* **Test 6.1 (Explorer):** Point to a temp folder and verify the string output lists files correctly.
* **Test 6.2 (REPL Read):** Agent is given a folder with `secret.txt`. Task: "What is the secret?".
    *   Expectation: Agent generates `open('secret.txt').read()`, executes it, sees the secret in REPL output, and answers.

### **🛑 Definition of Done**

* [x] REPL environment has necessary libraries.
* [x] Agent receives file paths in context, not content.
* [x] Agent successfully writes code to read a file and answer a question based on it.

## **🧠 Phase 7: Optimization with DSPy Compilation**

**Goal:** Use `dspy.compile` (MIPRO or BootstrapFewShot) to stop infinite loops and improve reasoning by learning from examples instead of manual prompt engineering.

### **📋 Implementation Steps**

1.  **Training Data Construction (`src/optimization/data.py`):**
    *   Create a dataset of `(task, context_state) -> action` examples.
    *   Crucially include examples where context *already has the answer*, labeled as `ANSWER`.
2.  **Optimization Script (`src/optimization/compile_architect.py`):**
    *   Initialize `teleprompter = BootstrapFewShot(metric=validate_action)`.
    *   Compile the `Architect` module.
    *   Save the optimized program to `src/modules/compiled_architect.json`.
3.  **Integration:**
    *   Update `Architect.__init__` to load the compiled JSON if it exists.

### **✅ Verification (Tests)**

*   **Test 7.1:** Run the "First line of README" task. Verify it stops after reading.
*   **Test 7.2:** Run the optimization script and verify a JSON file is produced.

### **🛑 Definition of Done**

*   [x] `compile_architect.py` runs successfully.
*   [x] Agent loads optimized weights.
*   [x] Infinite loop on file reading is resolved (Validated with `qwen2.5-coder`).

## **🛠️ Phase 8: Enhanced Tooling & Retrieval**

**Goal:** Equip the REPL with specialized libraries for complex document processing (Excel, PDF) and Web Search, enabling the Agent to handle real-world information retrieval tasks.

### **📋 Implementation Steps**

1.  **Dependency Updates:**
    *   Add primary libraries: `openpyxl` (Excel), `pdfplumber` (PDF Tables), `chromadb` (Semantic Search), `duckduckgo-search` (Web).
2.  **REPL Preloading (`src/core/repl.py`):**
    *   Ensure these libraries are importable.
    *   (Optional) Pre-import helper functions if simplifying usage is needed (e.g., a `search_web(query)` wrapper around DDGS).
3.  **Search Module (`src/tools/search.py`):**
    *   Implement a simple wrapper for `duckduckgo-search` to handle rate limits/errors gracefully.
4.  **Coder Training:**
    *   Update `src/modules/coder.py` few-shot examples to demonstrate using `pdfplumber` for tables and `openpyxl` for formulas.

### **✅ Verification (Tests)**

*   **Test 8.1 (Excel):** Given an .xlsx file with a formula, Agent must read the *formula* (using openpyxl), not just the value.
*   **Test 8.2 (PDF Table):** Given a PDF with a table, Agent must extract it as a list of lists or DataFrame.
*   **Test 8.3 (Web Search):** Agent "Who is the current president of France?" -> Uses DDGS -> Answers correctly.

### **🛑 Definition of Done**

*   [x] REPL has access to `openpyxl`, `pdfplumber`, `chromadb`, `duckduckgo-search`.
*   [ ] Agent can autonomously extract tables from PDFs.
*   [x] Agent can perform live web searches.

## **📝 Phase 9: Logging Infrastructure**

**Goal:** Replace all `print()` statements with Python's `logging` module for production-grade observability.

### **📋 Implementation Steps**

1.  **Logger Module (`src/core/logger.py`):**
    *   Create `setup_logger()` factory with console and file handlers.
    *   Support DEBUG, INFO levels.
    *   Each run creates a timestamped log file in `logs/`.
2.  **Codebase Migration:**
    *   Replace `print()` with `logger.info()` / `logger.debug()` across all modules.
3.  **Git Configuration:**
    *   Add `logs/` and `*.log` to `.gitignore`.

### **✅ Verification (Tests)**

*   **Test 9.1:** Run agent and verify log file is created in `logs/`.
*   **Test 9.2:** Verify log contains expected INFO/DEBUG entries.

### **🛑 Definition of Done**

*   [x] All `print()` replaced with `logging`.
*   [x] Log files generated per run.
*   [x] `logs/` gitignored.

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
*   **Current:** Agent creates `Architect`, `Coder`, `Responder`, `Delegator`, `REPL` internally.
*   **Proposed:** Accept these as constructor parameters with sensible defaults.
*   **Benefit:** Enables mocking for unit tests, improves testability.
*   **Risk:** Low - backward compatible with default instantiation.

#### **10.2: Protocol-Based Abstractions**
*   **Current:** Direct class dependencies between components.
*   **Proposed:** Define `Protocol` classes for `LMProvider`, `CodeExecutor`, `TaskRouter`.
*   **Benefit:** Enables swapping implementations (e.g., mock REPL for tests).
*   **Risk:** Medium - requires interface definitions.

#### **10.3: Lazy Logger Initialization**
*   **Current:** `logger = setup_logger()` runs at import time, creating log files.
*   **Proposed:** Use lazy initialization or context-based logger setup.
*   **Benefit:** Prevents spurious log files during testing/imports.
*   **Risk:** Low.

#### **10.4: BudgetManager Refactoring**
*   **Current:** Singleton with `__new__` override + `_initialized` flag.
*   **Proposed:** Use a proper singleton decorator or dependency injection.
*   **Benefit:** Cleaner code, easier reset for tests.
*   **Risk:** Low.

#### **10.5: Test Improvements**
*   **Current:** `test_parallel.py` depends on LLM correctly choosing DELEGATE.
*   **Proposed:**
    *   Mock the `Architect` to force DELEGATE action.
    *   Add unit tests for delegation logic separate from LLM integration.
*   **Benefit:** Reliable CI, faster tests.
*   **Risk:** Low.

#### **10.6: Compiled Module Loading Strategy**
*   **Current:** Modules check for compiled JSON in `__init__`.
*   **Proposed:** Centralize compiled module discovery in `config.py` or a dedicated loader.
*   **Benefit:** Single source of truth for optimization artifacts.
*   **Risk:** Low.

### **✅ Pre-Refactoring Test Coverage Requirements**

Before implementing any refactoring:
- [ ] `test_agent.py`: Add unit tests for each action branch (CODE, ANSWER, DELEGATE)
- [ ] `test_budget.py`: Ensure singleton reset works correctly ✅ (exists)
- [ ] `test_repl.py`: Cover edge cases ✅ (exists)
- [ ] Add mocking infrastructure in `conftest.py` for DSPy modules

### **📊 Current Test Coverage Summary**

| Module | Tests | Status |
|--------|-------|--------|
| `src/core/repl.py` | `test_repl.py` | ✅ Good |
| `src/core/budget.py` | `test_budget.py` | ✅ Good |
| `src/core/agent.py` | `test_agent.py`, `test_tools.py` | ⚠️ Integration only |
| `src/modules/*.py` | `test_dspy_modules.py` | ⚠️ LLM-dependent |
| `src/tools/search.py` | `test_tools.py` | ✅ Good |

### **🛑 Definition of Done**

*   [x] All refactoring items approved by stakeholder.
*   [x] Unit test coverage added before refactoring.
*   [x] Each refactoring item implemented incrementally with passing tests.
*   [x] No regression in existing functionality.

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
