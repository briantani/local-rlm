# Local RLM

A Python implementation of the **Recursive Language Model (RLM)** agent architecture from MIT CSAIL.

**Paper:** [arXiv:2512.24601v1](https://arxiv.org/html/2512.24601v1) - *Recursive Language Models*

## What is RLM?

RLM is an agent architecture that recursively solves problems by:

1. **Architect** decides: generate CODE or give ANSWER
2. **Coder** writes Python code when needed
3. **REPL** executes code in a persistent sandbox (with `recursive_llm()` for sub-tasks)
4. **Responder** formats the final answer

Unlike traditional Chain-of-Thought, RLM offloads computation to a real Python interpreter. Complex tasks are handled through emergent recursion - generated code can call `recursive_llm()` to spawn sub-agents.

## Quick Start

### Prerequisites

- Python 3.14+ ([Installation Guide](docs/INSTALLATION.md))
- [uv](https://docs.astral.sh/uv/) package manager
- [Ollama](https://ollama.ai/) for local execution OR API keys for cloud providers

### Install

```bash
git clone https://github.com/briantani/local-rlm.git
cd local-rlm
uv sync
```

### Run (Local - Free)

```bash
# Pull a local model
ollama pull qwen2.5-coder:7b

# Run a task
uv run python src/main.py "Calculate fibonacci(100)" --config configs/local-only.yaml
```

### Run (Cloud - Gemini)

```bash
# Set API key
echo "GEMINI_API_KEY=your-key" > .env

# Run a task
uv run python src/main.py "Summarize quantum computing" --config configs/cost-effective.yaml
```

## Configuration Profiles

| Profile | Use Case | Cost |
|---------|----------|------|
| `local-only.yaml` | Free, offline, private | $0 |
| `cost-effective.yaml` | Budget-friendly cloud | ~$0.50/task |
| `hybrid.yaml` | Balanced cost/quality | ~$2/task |
| `high-quality.yaml` | Best results | ~$5/task |

See [Configuration Guide](docs/CONFIGURATION.md) for details.

## Recent Changes (since Issue #26)

These updates improve artifact handling, reporting, and module interfaces:

- Artifact Tracking (Issue #26): The agent now automatically scans and registers files
        created during code execution. Use `RunContext.register_artifact()` to register
        artifacts programmatically; `RLMAgent.get_artifacts()` exposes the tracked list.
- Artifact Context Preservation (Issue #27): Artifacts include `prompt`, `section`, and
        `rationale` metadata. The `Responder` now embeds this context when rendering reports.
- Final Assembly Enforcement (Issue #28): Before saving the final report the agent runs
        `RunContext.finalize_report()` to ensure every artifact is referenced and described.
        A summary table of all artifacts is appended to the report.
- Intermediate Consistency Checks (Issue #29): After major CODE steps the agent validates
        any `expected_artifacts` declared by the `Coder`. If artifacts are missing the agent
        retries generation up to a configurable limit and logs the checks.
- Prompt & Signature Refinement (Issue #30): DSPy module signatures were extended to
        include artifact/context fields. `Coder` can declare expected artifacts via an
        inline comment `# EXPECTED_ARTIFACTS: file1.png, file2.csv` which the agent uses
        for validation and retries.

See `docs/CHANGES.md` for detailed examples and guidance on using these features.

## CLI Options

```bash
uv run python src/main.py "<task>" --config configs/<profile>.yaml [options]

Options:
  --context <dir>       Include files from directory as context
  --prompt-file <file>  Read task from file instead of command line
  --verbose             Show detailed execution logs
  --dry-run             Validate config without executing
```

### Examples

```bash
# Analyze files in a directory
uv run python src/main.py "Summarize the CSV files" --config configs/hybrid.yaml --context ./data

# Complex research task
uv run python src/main.py --prompt-file tasks/research.txt --config configs/high-quality.yaml
```

## Web Interface

> 🚧 **Work in Progress** - The web UI is under development and not fully functional.
> Use the CLI for tasks. See [Web Interface Status](docs/WEB_INTERFACE.md).

## Documentation

- [Installation Guide](docs/INSTALLATION.md) - Windows/macOS setup
- [Configuration Guide](docs/CONFIGURATION.md) - YAML profiles and options
- [RLM Theory](docs/THEORY.md) - Architecture and paper details
- [Web Interface](docs/WEB_INTERFACE.md) - Status and roadmap

## Testing Locally

The project uses `uv` and `pytest`. Integration tests that contact real LLM servers
are marked with `@pytest.mark.integration` and are disabled by default. Use the
helper script below to run tests locally.

- Run unit tests (fast):

```bash
./scripts/ci/run_tests.sh
```

- Run integration tests (requires `RLM_RUN_INTEGRATION` / live LLMs):

```bash
RUN_INTEGRATION=1 ./scripts/ci/run_tests.sh
```

If you prefer to run pytest directly with `uv`:

```bash
# Unit tests only
uv run pytest -q -m "not integration"

# Integration tests (explicit opt-in)
RLM_RUN_INTEGRATION=1 uv run pytest -q -m integration --durations=20
```

## Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                     User Query                          │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    ARCHITECT                            │
│               Decides: CODE | ANSWER                    │
└───────────┬─────────────────────────┬───────────────────┘
            │                         │
    ┌───────▼───────┐                 │
    │     CODER     │                 │
    │  Generate Py  │                 │
    └───────┬───────┘                 │
            ▼                         │
    ┌───────────────┐                 │
    │     REPL      │                 │
    │  Execute Py   │                 │
    │ recursive_llm │◄──── spawns sub-agents
    └───────┬───────┘                 │
            │                         │
            ▼                         ▼
┌─────────────────────────────────────────────────────────┐
│                    RESPONDER                            │
│              Format Final Answer                        │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Python 3.14.2** (Free-Threaded) - No GIL, true parallelism
- **DSPy** - LLM framework with optimizer-based prompt tuning
- **Ollama/Gemini/OpenAI** - Configurable LLM providers

## License

MIT License - See [LICENSE](LICENSE)

## Acknowledgments

Based on research from MIT CSAIL. See the [original paper](https://arxiv.org/html/2512.24601v1) for theoretical foundations.
