# local-rlm

A local implementation of the **Recursive Language Model (RLM)** agent, inspired by the research from MIT CSAIL.

**Paper:** [Recursive Language Models (arXiv:2512.24601v1)](https://arxiv.org/html/2512.24601v1)

## Overview

This project aims to replicate the core architecture of an RLM, which solves complex problems by recursively generating, executing, and refining Python code in a stateful environment. Unlike traditional Chain-of-Thought (CoT) approaches, an RLM can offload computational tasks to a REPL and manage its own context window more effectively.

## Key Features

- **Recursive Problem Solving:** Decomposes tasks into sub-problems solved via code generation.
- **Stateful Python Sandbox:** A secure, persistent REPL for executing generated code.
- **Modern Stack:** Built with **Python 3.14.2 (Free-Threaded)** and **DSPy**.
- **Local & Cloud Support:** Configurable to run with local models (Ollama) or cloud providers (Gemini, OpenAI).

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
git clone https://github.com/yourusername/local-rlm.git
cd local-rlm

# Install dependencies with uv
uv sync
```

#### Windows

```powershell
# Clone the repository
git clone https://github.com/yourusername/local-rlm.git
cd local-rlm

# Install uv if not already installed
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install dependencies with uv
uv sync
```

**Windows-Specific Notes:**
- **Python 3.14+**: Download from [python.org](https://www.python.org/downloads/) or use the Microsoft Store version
- **PowerShell**: Use PowerShell (not CMD) for best compatibility with `uv` commands
- **Path Handling**: The project uses `pathlib.Path` which automatically handles Windows path separators

---

## Configuration

The agent uses **YAML configuration profiles** for all settings. This provides a clean, version-controllable way to manage different use cases (cost-effective, high-quality, local-only, etc.).

### Step 1: Set Up API Keys (Optional)

For cloud providers (Gemini, OpenAI), create a `.env` file in the project root:

**macOS/Linux:**
```bash
echo "GEMINI_API_KEY=your-key-here" > .env
echo "OPENAI_API_KEY=your-key-here" >> .env
```

**Windows:**
```powershell
echo "GEMINI_API_KEY=your-key-here" | Out-File -FilePath .env -Encoding utf8
echo "OPENAI_API_KEY=your-key-here" | Out-File -FilePath .env -Append -Encoding utf8
```

### Step 2: Choose a Configuration Profile

The `configs/` directory contains pre-configured profiles:

| Profile | Description | Best For |
|---------|-------------|----------|
| **`local-only.yaml`** | Free Ollama models only | Privacy, offline work, no API costs |
| **`cost-effective.yaml`** | Gemini 2.5 Flash | Low-cost cloud tasks |
| **`paper-gpt5.yaml`** | GPT-5 (root) + GPT-5-mini (delegates) | Replicating paper results |
| **`high-quality.yaml`** | GPT-5.2 flagship | Maximum capability |
| **`hybrid.yaml`** | Ollama for code, Gemini for reasoning | Best of both worlds |

### Step 3: Run the Agent

```bash
uv run python src/main.py "<your task>" --config configs/<profile>.yaml
```

#### Example: Local Execution (No API Keys Needed)

1. **Install Ollama** from [ollama.ai](https://ollama.ai/)
2. **Pull a model:**
   ```bash
   ollama pull qwen2.5-coder:7b
   ```
3. **Run with local-only profile:**
   ```bash
   uv run python src/main.py "Calculate the 100th Fibonacci number" --config configs/local-only.yaml
   ```

#### Example: Cloud Execution (Gemini)

1. **Get API key** from [Google AI Studio](https://aistudio.google.com/apikey)
2. **Add to `.env`:**
   ```bash
   echo "GEMINI_API_KEY=your-key-here" > .env
   ```
3. **Run with cost-effective profile:**
   ```bash
   uv run python src/main.py "Summarize quantum computing" --config configs/cost-effective.yaml
   ```

#### Example: Paper-Validated Setup (OpenAI)

> **📄 From the Research:** The RLM paper used **GPT-5** for the root agent and **GPT-5-mini** for recursive sub-calls, achieving 91.33% on BrowseComp+ (1K documents).

1. **Get API key** from [OpenAI Platform](https://platform.openai.com/api-keys)
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

### Profile Structure

Each YAML profile defines:

```yaml
profile_name: "Cost-Effective Profile"
description: "Optimized for low cost using Gemini 2.5 Flash"

# Root agent configuration
root:
  provider: gemini
  model: gemini-2.5-flash
  max_steps: 10
  max_depth: 3
  pricing:
    input_per_1m: 0.30   # $0.30 per 1M input tokens
    output_per_1m: 2.50  # $2.50 per 1M output tokens

# Sub-agent (delegate) configuration
delegate:
  provider: gemini
  model: gemini-2.5-flash-lite
  max_steps: 5
  max_depth: 0
  pricing:
    input_per_1m: 0.10
    output_per_1m: 0.40

# Global budget limit (sum of all model costs)
budget:
  max_usd: 0.50
```

### Key Concepts

**Root vs. Delegate:**
- **Root**: The main agent that receives your task
- **Delegate**: Sub-agents spawned for parallel task decomposition
- Using a cheaper/faster model for delegates reduces costs

**Per-Model Pricing:**
- Each model tracks its own token usage and costs
- The `budget.max_usd` limit applies to the **sum** of all model costs
- Cost breakdown is printed at the end of each run

**Max Steps & Depth:**
- `max_steps`: Prevents infinite CODE → EXECUTE loops
- `max_depth`: Limits delegation recursion (prevents exponential sub-agent spawning)

### Creating Custom Profiles

1. **Copy an existing profile:**
   ```bash
   cp configs/cost-effective.yaml configs/my-profile.yaml
   ```

2. **Edit the YAML file** to customize:
   - Models (see available models below)
   - Budget limits
   - Max steps/depth
   - Per-module overrides (optional)

3. **Run with your profile:**
   ```bash
   uv run python src/main.py "your task" --config configs/my-profile.yaml
   ```

### Available Models (January 2026)

**OpenAI:**
- `gpt-5.2` - Flagship model ($1.75/$14.00 per 1M tokens)
- `gpt-5` - Paper root model ($1.25/$10.00)
- `gpt-5-mini` - Paper delegate model ($0.25/$2.00)
- `gpt-5-nano` - Ultra cost-effective ($0.05/$0.40)

**Google Gemini:**
- `gemini-3-pro` - Preview, most capable ($2.00/$12.00)
- `gemini-3-flash` - Preview, fast + intelligent ($0.50/$3.00)
- `gemini-2.5-flash` - Stable, best value ($0.30/$2.50)
- `gemini-2.5-flash-lite` - Ultra low cost ($0.10/$0.40)

**Ollama (Local, Free):**
- `qwen2.5-coder:14b` - Best for coding
- `qwen2.5-coder:7b` - Faster, lower memory
- `llama3:8b` - General purpose

---

## Advanced Configuration

### Per-Module Model Overrides

You can specify different models for each DSPy module:

```yaml
# In your custom profile
modules:
  architect:
    provider: gemini
    model: gemini-3-flash
    pricing:
      input_per_1m: 0.50
      output_per_1m: 3.00

  coder:
    provider: ollama
    model: qwen2.5-coder:7b
    pricing:
      input_per_1m: 0.0  # Local = free
      output_per_1m: 0.0
```

This is useful for:
- Using local models for code generation (fast, free)
- Using cloud models for decision-making (better reasoning)
- See `configs/hybrid.yaml` for a working example

### Handling Large Files

The agent has built-in strategies for processing large files or datasets:

#### 1. **Automatic Task Delegation**
When the `Architect` module detects a task is too complex or involves too much data, it can choose the `DELEGATE` action:

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
The agent's `format_context()` method maintains execution history. For very long histories:
- Consider increasing `max_steps` in your YAML config to give the agent more opportunities
- Or use the `DELEGATE` action to offload work to sub-agents with fresh context

#### 4. **No Separate Search Tool Needed**
The agent can already:
- Use Python's `grep`, `re`, or file I/O to search files
- Generate code to parse JSON, XML, CSV, Excel, etc.
- Call external APIs or databases via generated code

**Example Task:** "Find all TODO comments in this codebase"
```bash
uv run python src/main.py "Find all TODO comments" --config configs/local-only.yaml --context /path/to/code
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

### Basic Syntax

```bash
uv run python src/main.py "<your task>" --config <profile.yaml> [--context <path>]
```

### Arguments

| Argument | Description | Required |
|----------|-------------|----------|
| `task` | The natural language task to perform | Yes |
| `--config` | Path to YAML configuration file | Yes |
| `--context` | Path to a directory with files to include | No |

### Examples

```bash
# Simple math with local model
uv run python src/main.py "What is 2^100?" --config configs/local-only.yaml

# Read and analyze a file
uv run python src/main.py "What is the first line of README.md?" --config configs/cost-effective.yaml --context .

# Complex task with file context
uv run python src/main.py "Analyze the sales data and find the top 3 products" --config configs/high-quality.yaml --context ./data

# Paper-validated setup
uv run python src/main.py "Implement a binary search tree" --config configs/paper-gpt5.yaml
# Run all unit tests (fast, no LLM required)
uv run pytest tests/test_agent.py::TestAgentUnitTests tests/test_budget.py tests/test_repl.py -v

# Run all tests including integration tests (requires Ollama)
uv run pytest

# Run with coverage
uv run pytest --cov=src
```

---

## Project Structure

```
src/
├── core/
│   ├── agent.py       # Main RLM Agent orchestrator
│   ├── budget.py      # Token usage tracking & limits
│   ├── logger.py      # Lazy logging configuration
│   ├── repl.py        # Stateful Python sandbox
│   └── explorer.py    # File system scanner
├── modules/
│   ├── architect.py   # Decision maker (CODE/ANSWER/DELEGATE)
│   ├── coder.py       # Python code generator
│   ├── responder.py   # Natural language responder
│   └── delegator.py   # Task decomposer for parallelism
├── tools/
│   └── search.py      # Web search integration
├── config.py          # LLM provider configuration
└── main.py            # CLI entry point
```

---

## Development Roadmap

See [AGILE_PLAN.md](AGILE_PLAN.md) for the full development roadmap and current status.

---

## License

MIT License - see [LICENSE](LICENSE) for details.
