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

### Option 1: Local Execution with Ollama (Recommended for Privacy)

1. **Install Ollama**
   - **macOS/Linux**: Download from [ollama.ai](https://ollama.ai/)
   - **Windows**: Download the Windows installer from [ollama.ai](https://ollama.ai/)

2. **Pull a coding model:**
   ```bash
   # Recommended: Qwen 2.5 Coder (14B parameters)
   ollama pull qwen2.5-coder:14b

   # Alternative: Smaller model for limited hardware
   ollama pull qwen2.5-coder:7b

   # Alternative: Llama 3
   ollama pull llama3:8b
   ```

3. **Start the Ollama server:**
   - **macOS/Linux**: `ollama serve`
   - **Windows**: Ollama runs as a background service automatically after installation

4. **Run the agent:**
   ```bash
   uv run python src/main.py "Calculate the 100th Fibonacci number" --provider ollama
   ```

### Option 2: Google Gemini (Cloud)

1. **Get an API key** from [Google AI Studio](https://aistudio.google.com/apikey)

2. **Create a `.env` file** in the project root:

   **macOS/Linux (bash/zsh):**
   ```bash
   echo "GEMINI_API_KEY=your-api-key-here" > .env
   ```

   **Windows (PowerShell):**
   ```powershell
   echo "GEMINI_API_KEY=your-api-key-here" | Out-File -FilePath .env -Encoding utf8
   ```

   Or simply create a `.env` file manually with any text editor.

3. **Run the agent:**
   ```bash
   uv run python src/main.py "Summarize the key points of quantum computing" --provider gemini
   ```

   **Available Gemini models:**
   - `gemini-2.0-flash` (default, fast)
   - `gemini-2.5-pro` (more capable)
   - `gemini-3.0-pro` (latest, most capable)

### Option 3: OpenAI (Cloud) — *Paper-Validated*

> **📄 From the Research:** The RLM paper evaluated **GPT-5** with medium reasoning as the frontier closed model. The authors found that RLM(GPT-5) achieved **91.33%** on BrowseComp+ (1K documents) and **58.00%** F1 on OOLONG-Pairs, dramatically outperforming base models. For recursive sub-calls, **GPT-5-mini** was used to balance capability and cost.

1. **Get an API key** from [OpenAI Platform](https://platform.openai.com/api-keys)

2. **Add to your `.env` file:**

   **macOS/Linux (bash/zsh):**
   ```bash
   echo "OPENAI_API_KEY=your-api-key-here" >> .env
   ```

   **Windows (PowerShell):**
   ```powershell
   echo "OPENAI_API_KEY=your-api-key-here" | Out-File -FilePath .env -Append -Encoding utf8
   ```

3. **Run the agent:**
   ```bash
   uv run python src/main.py "Write a Python function to merge two sorted lists" --provider openai
   ```

   **Available OpenAI models:**
   - `gpt-4o-mini` (default, cost-effective) — *analogous to GPT-5-mini used for sub-calls*
   - `gpt-4o` (most capable) — *closest available to GPT-5 used in the paper*
   - `o1-mini` / `o1` (reasoning models) — *for complex multi-step tasks*

### Option 4: Qwen via OpenAI-Compatible API — *Paper-Validated*

> **📄 From the Research:** The RLM paper also evaluated **Qwen3-Coder-480B-A35B** as the frontier open model. This 480B parameter model (35B active) achieved **56.00%** on CodeQA and **44.66%** on BrowseComp+. The authors noted that Qwen3-Coder tends to use more aggressive sub-calling patterns, making thousands of recursive calls for complex tasks.

For local Qwen models, use Ollama (Option 1) with `qwen2.5-coder`. For cloud access to larger Qwen models:

1. **Use a provider like [Fireworks AI](https://fireworks.ai/)** or [Together AI](https://together.ai/) that offers Qwen models via OpenAI-compatible APIs.

2. **Configure the endpoint:**

   **macOS/Linux (bash/zsh):**
   ```bash
   echo "OPENAI_API_KEY=your-fireworks-key" >> .env
   echo "OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1" >> .env
   ```

   **Windows (PowerShell):**
   ```powershell
   echo "OPENAI_API_KEY=your-fireworks-key" | Out-File -FilePath .env -Append -Encoding utf8
   echo "OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1" | Out-File -FilePath .env -Append -Encoding utf8
   ```

3. **Run with the Qwen model:**
   ```bash
   uv run python src/main.py "Analyze this codebase" --provider openai --model accounts/fireworks/models/qwen3-coder-480b
   ```

---

## Usage

### Basic Syntax

```bash
uv run python src/main.py "<your task>" --provider <provider> [--model <model>] [--context <path>]
```

### Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `task` | The natural language task to perform | Required |
| `--provider` | LLM provider: `ollama`, `gemini`, `openai` | `ollama` |
| `--model` | Specific model name (optional) | Provider default |
| `--context` | Path to a directory with files to include | None |

### Examples

```bash
# Simple math with local Ollama
uv run python src/main.py "What is 2^100?" --provider ollama

# Read and analyze a file
uv run python src/main.py "What is the first line of README.md?" --context .

# Use a specific model
uv run python src/main.py "Explain recursion" --provider gemini --model gemini-2.5-pro

# Complex task with file context
uv run python src/main.py "Analyze the sales data and find the top 3 products" --context ./data --provider openai
```

---

## Running Tests

```bash
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
