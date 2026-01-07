# local-rlm

A local implementation of the **Recursive Language Model (RLM)** agent,
inspired by the research from MIT CSAIL.

**Paper:**
[Recursive Language Models (arXiv:2512.24601v1)](<https://arxiv.org/html/2512.24601v1>)

## Overview

This project aims to replicate the core architecture of an RLM, which
solves complex problems by recursively generating, executing, and refining
Python code in a stateful environment. Unlike traditional Chain-of-Thought
(CoT) approaches, an RLM can offload computational tasks to a REPL and
manage its own context window more effectively.

## Key Features

- **Recursive Problem Solving:** Decomposes tasks into sub-problems solved
  via code generation.
- **Stateful Python Sandbox:** A secure, persistent REPL for executing
  generated code.
- **Modern Stack:** Built with **Python 3.14.2 (Free-Threaded)** and
  **DSPy**.
- **Local & Cloud Support:** Configurable to run with local models (Ollama)
  or cloud providers (Gemini, OpenAI).
- **Web Interface:** Full-featured FastAPI + HTMX + Alpine.js UI with:
  - Real-time streaming execution with WebSocket
  - Task history and management
  - Rich canvas view with export (Markdown, JSON, PDF)
  - Shareable links and task templates
  - Configuration management UI

## Project Status

📊 **Track Progress**: [View all phases on GitHub Issues →](https://github.com/briantani/local-rlm/issues?q=is%3Aissue+label%3Aphase)

**Milestones:**
- ✅ [CLI Completion](https://github.com/briantani/local-rlm/milestone/1) (Phases 0-11) - Core agent functionality complete
- ✅ [Web App MVP](https://github.com/briantani/local-rlm/milestone/2) (Phases 12-17) - Web interface complete
- 🚧 Phase 18 (Polish & Production Readiness) - In progress

**Development Plan**: See [docs/AGILE_PLAN.md](docs/AGILE_PLAN.md) for legacy documentation or [GitHub Issues](https://github.com/briantani/local-rlm/issues) for active tracking.

---

## Quick Start

### Prerequisites

- **Python 3.14+** (Free-Threaded recommended)
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager
- **[Ollama](https://ollama.ai/)** (for local execution) OR API keys for cloud providers

### Installation

#### macOS / Linux

```bash
# Clone the repository
git clone https://github.com/briantani/local-rlm.git
cd local-rlm

# Install dependencies with uv
uv sync
```

#### Windows

```powershell
# Clone the repository
git clone https://github.com/briantani/local-rlm.git
cd local-rlm

# Install uv if not already installed
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install dependencies with uv
uv sync
```

**Windows-Specific Notes:**

- **Python 3.14+**: Download from [python.org](<https://www.python.org/downloads/>)
  or use the Microsoft Store version
- **PowerShell**: Use PowerShell (not CMD) for best compatibility with `uv`
  commands
- **Path Handling**: The project uses `pathlib.Path` which automatically
  handles Windows path separators

---

## Configuration

The agent uses **YAML configuration profiles** for all settings. See
**[Configuration Profiles Guide →](configs/README.md)** for complete
documentation on:

- Available profiles and when to use them
- Model pricing and selection strategies
- Creating custom configurations
- Budget management and optimization

### Quick Start Configuration

### Step 1: Set Up API Keys (Optional)

For cloud providers (Gemini, OpenAI), create a `.env` file in the project
root:

**macOS/Linux:**

```bash
echo "GEMINI_API_KEY=your-key-here" > .env
echo "OPENAI_API_KEY=your-key-here" >> .env
```

**Windows:**

```powershell
echo "GEMINI_API_KEY=your-key-here" | Out-File -FilePath .env `
  -Encoding utf8
echo "OPENAI_API_KEY=your-key-here" | Out-File -FilePath .env `
  -Append -Encoding utf8
```

### Step 2: Choose a Configuration Profile

The `configs/` directory contains pre-configured profiles. See
[configs/README.md](configs/README.md) for detailed descriptions and
performance comparisons.

**Quick Reference:**

| Profile | Best For | Cost |
| ------- | -------- | ---- |
| **`paper-gpt5.yaml`** | Research replication | ~$5/task |
| **`high-quality.yaml`** | Maximum capability | ~$5/task |
| **`cost-effective.yaml`** | Budget-friendly | ~$0.50/task |
| **`local-only.yaml`** | Privacy, offline, free | $0 |
| **`hybrid.yaml`** | Production apps | ~$2/task |

For full details on each profile, model pricing, and selection strategies, see
**[Configuration Profiles Guide →](configs/README.md)**

### Step 3: Run the Agent

#### CLI Mode

```bash
uv run python src/main.py "<your task>" --config configs/<profile>.yaml
```

#### Web UI Mode

```bash
# Start the web server
uv run python src/web/app.py

# Open browser to http://localhost:8000
# Select configuration, enter task, and watch real-time execution
```

#### Example: Local Execution (No API Keys Needed)

1. **Install Ollama** from [ollama.ai](<https://ollama.ai/>)
2. **Pull a model:**

   ```bash
   ollama pull qwen2.5-coder:7b
   ```

3. **Run with local-only profile:**

   ```bash
   uv run python src/main.py "Calculate the 100th Fibonacci number" --config configs/local-only.yaml
   ```

#### Example: Cloud Execution (Gemini)

1. **Get API key** from
   [Google AI Studio](<https://aistudio.google.com/apikey>)
2. **Add to `.env`:**

   ```bash
   echo "GEMINI_API_KEY=your-key-here" > .env
   ```

3. **Run with cost-effective profile:**

   ```bash
   uv run python src/main.py "Summarize quantum computing" --config configs/cost-effective.yaml
   ```

#### Example: Paper-Validated Setup (OpenAI)

> **📄 From the Research:** The RLM paper used **GPT-5** for the root agent
> and **GPT-5-mini** for recursive sub-calls, achieving 91.33% on
> BrowseComp+ (1K documents).

1. **Get API key** from
   [OpenAI Platform](<https://platform.openai.com/api-keys>)
2. **Add to `.env`:**

   ```bash
   echo "OPENAI_API_KEY=your-key-here" >> .env
   ```

3. **Run with paper profile:**

   ```bash
   uv run python src/main.py "Write a function to merge sorted lists" --config configs/paper-gpt5.yaml
   ```

---

## Understanding Configuration Profiles

For detailed information on configuration profiles, see the
**[Configuration Profiles Guide →](configs/README.md)**.

### Quick Reference

**Basic Profile Structure:**

```yaml
# Root agent (main orchestrator)
root:
  provider: gemini | openai | ollama
  model: model-name
  max_steps: 10
  max_depth: 3

# Sub-agents (for parallel delegation)
delegate:
  provider: gemini
  model: cheaper-model
  max_steps: 5
  max_depth: 0

# Budget control
budget:
  max_usd: 0.50
```

**Key Concepts:**

- **Root**: Main agent receiving your task
- **Delegate**: Sub-agents for parallel task decomposition
- **max_steps**: Prevents infinite CODE → EXECUTE loops
- **max_depth**: Limits delegation recursion

For complete documentation including model pricing, selection strategies,
and performance comparisons, see
**[Configuration Profiles Guide →](configs/README.md)**.

---

## Advanced Features

### Per-Module Model Overrides

You can specify different models for each DSPy module (Architect, Coder,
Responder, Delegator). See the
**[Configuration Guide →](configs/README.md#-configuration-anatomy)** for
details and examples like `configs/hybrid.yaml`.

### Handling Large Files

The agent has built-in strategies for processing large files or datasets:

#### 1. **Automatic Task Delegation**

When the `Architect` module detects a task is too complex or involves too
much data, it can choose the `DELEGATE` action:

- **Breaks down** the task into smaller sub-tasks
- **Executes in parallel** using `ThreadPoolExecutor`
- **Aggregates results** back to the main agent

**Example:** "Analyze 1000 log files and find errors"

- The agent delegates to sub-agents, each processing a chunk of files
- Results are merged into a final summary

#### 2. **Programmatic Chunking via Code**

The agent can generate Python code to chunk large files:

```python
# Example code the agent might generate:
import pandas as pd

# Read large CSV in chunks
chunk_size = 10000
results = []

for chunk in pd.read_csv('huge_file.csv', chunksize=chunk_size):
    # Process each chunk
    summary = chunk.describe()
    results.append(summary)

# Combine results
final_summary = pd.concat(results).mean()
print(final_summary)
```

#### 3. **Context Window Management**

The agent's `format_context()` method maintains execution history. For very
long histories:

- Consider increasing `max_steps` in your YAML config to give the agent
  more opportunities
- Or use the `DELEGATE` action to offload work to sub-agents with fresh
  context

#### 4. **No Separate Search Tool Needed**

The agent can already:

- Use Python's `grep`, `re`, or file I/O to search files
- Generate code to parse JSON, XML, CSV, Excel, etc.
- Call external APIs or databases via generated code

**Example Task:** "Find all TODO comments in this codebase"

```bash
uv run python src/main.py "Find all TODO comments" \
  --config configs/local-only.yaml --context /path/to/code
```

The agent will generate code like:

```python
import os
import re

todos = []
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py'):
            with open(os.path.join(root, file)) as f:
                for i, line in enumerate(f):
                    if 'TODO' in line:
                        todos.append(f"{file}:{i+1}: {line.strip()}")

for todo in todos:
    print(todo)
```

---

## Usage

### Web Interface (Recommended)

The web interface provides the easiest way to interact with the agent:

```bash
# Start the web server
uv run python src/web/app.py

# Open http://localhost:8000 in your browser
```

**Features:**
- 🎯 Select configuration profile from dropdown
- ⚡ Real-time streaming execution
- 📊 Rich canvas view with formatted output
- 💾 Export results (Markdown, JSON, PDF)
- 🔗 Share tasks with secure links
- 📝 Save tasks as reusable templates
- 📜 View task history
- 💰 Live cost tracking

See [src/web/README.md](src/web/README.md) for full web UI documentation.

### CLI Mode

#### Basic Syntax

```bash
# Short tasks: Use inline string
uv run python src/main.py "<your task>" --config <profile>.yaml [--context <path>]

# Long/complex tasks: Use prompt file
uv run python src/main.py --prompt-file <task.txt> --config <profile>.yaml [--context <path>]
```

### Arguments

| Argument | Description | Required |
| -------- | ----------- | -------- |
| `task` | The natural language task to perform (inline) | Yes* |
| `--prompt-file` | Path to text file with task description (for verbose prompts) | Yes* |
| `--config` | Path to YAML configuration file | Yes |
| `--context` | Path to a directory with files to include | No |

*Either `task` or `--prompt-file` must be provided (mutually exclusive)

### Examples

```bash
# Simple math with local model
uv run python src/main.py "What is 2^100?" --config configs/local-only.yaml

# Complex research task from file
uv run python src/main.py --prompt-file tasks/ai-research.txt \
  --config configs/high-quality.yaml

# Read and analyze a file
uv run python src/main.py "What is the first line of README.md?" \
  --config configs/cost-effective.yaml --context .

# Complex task with file context
uv run python src/main.py "Analyze the sales data and find the top 3 products" \
  --config configs/high-quality.yaml --context ./data

# Paper-validated setup
uv run python src/main.py "Implement a binary search tree" \
  --config configs/paper-gpt5.yaml

# Run all unit tests (fast, no LLM required)
uv run pytest tests/test_agent.py::TestAgentUnitTests \
  tests/test_budget.py tests/test_repl.py -v

# Run all tests including integration tests (requires Ollama)
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

---

## Project Structure

```text
src/
├── core/               # Core infrastructure
│   ├── agent.py       # Main RLM Agent orchestrator
│   ├── budget.py      # Token usage tracking & limits
│   ├── logger.py      # Lazy logging configuration
│   ├── repl.py        # Stateful Python sandbox
│   └── explorer.py    # File system scanner
├── modules/            # DSPy modules
│   ├── architect.py   # Decision maker (CODE/ANSWER/DELEGATE)
│   ├── coder.py       # Python code generator
│   ├── responder.py   # Natural language responder
│   └── delegator.py   # Task decomposer for parallelism
├── rlm/                # Service layer
│   └── services/      # Business logic (TaskService, ConfigService, etc.)
├── web/                # Web application
│   ├── app.py         # FastAPI backend with WebSocket streaming
│   ├── task_runner.py # Async task executor
│   └── templates/     # HTMX + Alpine.js UI components
├── tools/
│   └── search.py      # Web search integration
├── config.py          # LLM provider configuration
└── main.py            # CLI entry point

configs/                # Configuration profiles
scripts/                # Utility scripts
tests/                  # Comprehensive test suite
```

---

## Development & Contribution

### Project Tracking

- **GitHub Issues**: [View all phases →](https://github.com/briantani/local-rlm/issues?q=is%3Aissue+label%3Aphase)
- **Milestones**: [CLI Completion](https://github.com/briantani/local-rlm/milestone/1) ✅ | [Web App MVP](https://github.com/briantani/local-rlm/milestone/2) ✅
- **Legacy Docs**: [docs/AGILE_PLAN.md](docs/AGILE_PLAN.md) - Original development plan (archived)

### Current Development

Phase documentation is tracked via GitHub Issues for active collaboration:

- ✅ **Phases 0-17**: Complete (CLI + Web UI)
- 🚧 **Phase 18**: Polish & Production Readiness (in progress)
- 📋 **Future**: Performance optimization, advanced features

See [scripts/MIGRATION_SUMMARY.md](scripts/MIGRATION_SUMMARY.md) for migration details.

```bash
# View all phase issues
gh issue list --label phase

# View CLI-specific phases
gh issue list --label cli

# View Web App phases
gh issue list --label webapp
```

### Contributing

1. Pick an open issue from [GitHub Issues](https://github.com/briantani/local-rlm/issues)
2. Comment to claim the issue
3. Create a branch: `git checkout -b feature/phase-X`
4. Make changes with tests
5. Submit PR linking to the issue

---

## License

MIT License - see [LICENSE](LICENSE) for details.
