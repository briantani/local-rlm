# RLM Configuration Profiles

This directory contains YAML configuration files for different RLM agent profiles. Each profile defines model selection, budget limits, and behavior parameters optimized for specific use cases.

## 📁 Available Profiles

### `paper-gpt5.yaml` — Research Paper Replication ⭐

**Based on:** Exact RLM paper setup (arXiv:2512.24601v1)
**Use Case:** Reproduce research results, maximum quality, academic benchmarking
**Cost:** ~$5/task (paper averaged $0.99 for BrowseComp+)
**Strategy:** GPT-5 for root, GPT-5-mini for delegates (now publicly available!)

**Paper Results:**

- BrowseComp+ (1K): 91.33% accuracy (base model: 0%)
- OOLONG-Pairs: 58.00% F1 (base model: 0.04%)
- CodeQA: 62.00% accuracy (base model: 24%)

```bash
uv run python src/main.py "Complex research task" --config configs/paper-gpt5.yaml
```

### `high-quality.yaml` — Maximum Capability

**Based on:** GPT-5.2 (OpenAI's best coding/agentic model)
**Use Case:** Complex research, deep analysis, maximum accuracy
**Cost:** ~$5/task
**Strategy:** GPT-5.2 for root reasoning, GPT-5-mini for recursive sub-calls

```bash
uv run python src/main.py "Analyze quantum computing trends" --config configs/high-quality.yaml
```

### `cost-effective.yaml` — Budget-Friendly

**Use Case:** Development, testing, production tasks with cost control
**Cost:** ~$0.50/task
**Strategy:** Gemini 2.5 Flash (best price-performance) with Flash-Lite for delegates

```bash
uv run python src/main.py "Calculate Fibonacci 100" --config configs/cost-effective.yaml
```

### `local-only.yaml` — Complete Privacy

**Use Case:** Sensitive data, offline work, no API costs
**Cost:** $0 (local hardware only)
**Strategy:** Ollama qwen2.5-coder, larger model for root, smaller for delegates

```bash
uv run python src/main.py "Review this confidential document" --config configs/local-only.yaml
```

### `hybrid.yaml` — Best of Both Worlds

**Use Case:** Production applications, balanced performance
**Cost:** ~$2/task
**Strategy:** Gemini 3 Flash for reasoning, local Ollama for fast code generation

```bash
uv run python src/main.py "Build a web scraper" --config configs/hybrid.yaml
```

### `base.yaml` — Template

**Use Case:** Starting point for custom profiles
**Strategy:** Extend this to create your own configurations

## 🎯 Configuration Anatomy

```yaml
# Profile metadata
profile_name: "My Custom Profile"
description: "What this profile is for"

# Root agent (main orchestrator)
root:
  provider: gemini | openai | ollama
  model: model-name
  max_steps: 10      # Max iterations before giving up
  max_depth: 3       # Max recursion depth for delegation

# Delegate agents (sub-tasks)
delegate:
  provider: gemini | openai | ollama
  model: model-name  # Often cheaper/smaller than root
  max_steps: 5
  max_depth: 1       # Usually shallower to prevent exponential growth

# Per-module model assignment (optional)
modules:
  architect:  # Makes CODE/ANSWER/DELEGATE decisions
    provider: ...
    model: ...
  coder:      # Generates Python code
    provider: ...
    model: ...
  responder:  # Writes final natural language answers
    provider: ...
    model: ...
  delegator:  # Breaks tasks into subtasks
    provider: ...
    model: ...

# Budget control
budget:
  max_usd: 1.0
  input_price_per_1m: 0.075   # $ per million input tokens
  output_price_per_1m: 0.30   # $ per million output tokens

# DSPy framework settings
dspy:
  max_retries: 3      # Retries when code validation fails
  cache_enabled: true

# Logging
logging:
  level: INFO | DEBUG | WARNING
  file: logs/custom-run.log
```

## 🔧 Creating Custom Profiles

### Option 1: Extend Base Template

```yaml
# configs/my-profile.yaml
extends: configs/base.yaml

# Override only what you need
root:
  model: gpt-4o  # Everything else inherited from base

budget:
  max_usd: 10.0
```

### Option 2: From Scratch

Copy any existing profile and modify it:

```bash
cp configs/hybrid.yaml configs/my-task.yaml
# Edit my-task.yaml
```

## 🔑 API Keys (Security)

**NEVER** put API keys in YAML files! They belong in `.env`:

```bash
# .env (gitignored)
GEMINI_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
```

YAML configs will reference these automatically.

## � Model Pricing Reference (January 2026)

| Provider | Model | Input (per 1M tokens) | Output (per 1M tokens) | Notes |
|----------|-------|----------------------|------------------------|-------|
| **OpenAI** | GPT-5.2 | $1.75 | $14.00 | Best for coding/agentic (flagship) |
| **OpenAI** | GPT-5 | $1.25 | $10.00 | Paper's root model |
| **OpenAI** | GPT-5-mini | $0.25 | $2.00 | Paper's delegate model |
| **OpenAI** | GPT-5-nano | $0.05 | $0.40 | Ultra cheap |
| **OpenAI** | GPT-4.1 | $2.00 | $8.00 | Non-reasoning flagship |
| **Google** | Gemini 3 Pro | $2.00 | $12.00 | Best multimodal (preview) |
| **Google** | Gemini 3 Flash | $0.50 | $3.00 | Fast + intelligent (preview) |
| **Google** | Gemini 2.5 Pro | $1.25 | $10.00 | Advanced thinking model |
| **Google** | Gemini 2.5 Flash | $0.30 | $2.50 | Best price-performance |
| **Google** | Gemini 2.5 Flash-Lite | $0.10 | $0.40 | Ultra cost-effective |
| **Google** | Gemini 2.0 Flash | $0.10 | $0.40 | Workhorse model (stable) |
| **Ollama** | qwen2.5-coder:14b | $0 | $0 | Local (hardware cost only) |
| **Ollama** | qwen2.5-coder:7b | $0 | $0 | Local (lighter model) |

**Cost Calculation Example:**

```
Task uses: 100K input tokens, 20K output tokens
Model: GPT-4o

Cost = (100,000 / 1,000,000 × $2.50) + (20,000 / 1,000,000 × $10.00)
     = $0.25 + $0.20
     = $0.45
```

**Paper's Finding:** RLM(GPT-5) cost averaged $0.99 per task on BrowseComp+ (1K documents, 6-11M tokens), which was CHEAPER than feeding all 6-11M tokens to base GPT-5 (~$2.75).

## �💡 Tips

### When to Use Which Profile

| Task Type | Recommended Profile | Why |
|-----------|---------------------|-----|
| **Research replication** | `paper-gpt5` | Match academic benchmarks exactly |
| Quick calculations | `cost-effective` | Fast, cheap, sufficient quality |
| Code generation | `hybrid` | Local Ollama is fast for code |
| Deep analysis | `high-quality` | Premium models for nuance |
| Confidential data | `local-only` | Zero external API calls |
| Production app | `hybrid` | Balanced cost/performance |
| Budget testing | `cost-effective` | ~$0.50/task for development |

### Model Selection Strategy

**Root Agent (Main Orchestrator):**

- Needs strong reasoning for Architect decisions
- Consider: GPT-4o, Gemini 2.5 Pro, or large Qwen local

**Delegate Agents (Sub-Tasks):**

- Often simpler tasks (process a chunk, analyze a section)
- Consider: GPT-4o-mini, Gemini Flash, or smaller Qwen

**Coder Module:**

- Code generation benefits from specialized models
- Consider: Qwen2.5-coder (local), GPT-4o, Gemini Flash

**Responder Module:**

- Final answer quality matters
- Consider: Same as root or slightly better

### Budget Management

- Start with low budgets (`$0.50`) during development
- Monitor `logs/` for token usage patterns
- Adjust `max_steps` and `max_depth` if hitting limits frequently
- Use `local-only` profile for unlimited experimentation

## 📊 Performance Comparison

Based on the RLM paper's findings (with accurate 2026 pricing):

| Strategy | Est. Cost/Task | Quality | Speed | Use Case |
|----------|---------------|---------|-------|----------|
| Paper GPT-5 setup | $0.99-5.00 | ⭐⭐⭐⭐⭐ | 🐢🐢 | Research, benchmarking |
| Single GPT-4o (all) | $5.00-15.00 | ⭐⭐⭐⭐⭐ | 🐢🐢 | Maximum quality, cost no object |
| Root 4o + Delegate mini | $2.00-5.00 | ⭐⭐⭐⭐ | 🐢🐇 | High quality, cost-conscious |
| Hybrid (local + cloud) | $0.50-2.00 | ⭐⭐⭐⭐ | 🐇🐇 | Best balance |
| All Gemini Flash | $0.25-0.50 | ⭐⭐⭐ | 🐇🐇🐇 | Development, simple tasks |
| Local-only | $0 | ⭐⭐⭐ | 🐢🐇 | Privacy, offline, unlimited use |

**Key Insight from Paper:** The RLM approach with asymmetric models (expensive root + cheap delegates) achieved better results than base models while maintaining comparable or LOWER costs due to efficient context filtering.

## 🚀 Quick Start Examples

```bash
# Try all profiles on the same task
TASK="Analyze the trend in AI research from 2020-2025"

uv run python src/main.py "$TASK" --config configs/cost-effective.yaml
uv run python src/main.py "$TASK" --config configs/high-quality.yaml
uv run python src/main.py "$TASK" --config configs/hybrid.yaml
```

## 📚 Further Reading

- [RLM Paper (arXiv:2512.24601v1)](https://arxiv.org/html/2512.24601v1)
- [AGILE_PLAN.md - Phase 11](../AGILE_PLAN.md)
- [Main README](../README.md)
