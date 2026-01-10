# Configuration Guide

Complete guide to configuring the RLM agent with YAML profiles.

## Configuration System Overview

The RLM agent uses YAML configuration files to specify:

- Which LLM provider to use (Ollama, Gemini, OpenAI)
- Which model for each role (root, delegate, modules)
- Budget limits and execution constraints
- Per-module overrides

Configuration files live in the `configs/` directory.

## Quick Reference

| Profile | Use Case | Cost |
|---------|----------|------|
| `local-only.yaml` | Free local execution | Free |
| `cost-effective.yaml` | Cloud execution, minimal cost | $ |
| `hybrid.yaml` | Best balance of cost/quality | $$ |
| `high-quality.yaml` | Maximum quality | $$$ |
| `paper-gpt5.yaml` | Replicates MIT paper setup | $$$$ |

## Configuration File Structure

```yaml
# configs/example.yaml

# Root agent configuration
root:
  provider: gemini          # gemini, openai, or ollama
  model: gemini-2.5-flash   # Model name for this provider

# Delegate agent configuration (for sub-tasks)
delegate:
  provider: ollama
  model: qwen2.5-coder:7b

# Per-module overrides (optional)
modules:
  architect:
    provider: gemini
    model: gemini-2.5-pro
  coder:
    provider: ollama
    model: qwen2.5-coder:14b
  responder:
    provider: gemini
    model: gemini-2.5-flash

# Execution limits
limits:
  max_steps: 25             # Maximum execution steps
  max_budget: 1.00          # Maximum cost in USD
  max_depth: 3              # Maximum delegation depth
```

## Profile Details

### local-only.yaml

**Best for:** Development, testing, zero-cost execution

```yaml
root:
  provider: ollama
  model: qwen2.5-coder:14b

delegate:
  provider: ollama
  model: qwen2.5-coder:7b

limits:
  max_steps: 30
  max_budget: 0.00
  max_depth: 2
```

**Requirements:**

- Ollama installed and running
- Models downloaded: `ollama pull qwen2.5-coder:14b`

### cost-effective.yaml

**Best for:** Production with minimal API costs

```yaml
root:
  provider: gemini
  model: gemini-2.5-flash

delegate:
  provider: gemini
  model: gemini-2.5-flash

limits:
  max_steps: 20
  max_budget: 0.50
  max_depth: 2
```

**Requirements:**

- Gemini API key in `.env`

### hybrid.yaml

**Best for:** Balance of quality and cost

```yaml
root:
  provider: gemini
  model: gemini-2.5-pro

delegate:
  provider: ollama
  model: qwen2.5-coder:7b

modules:
  coder:
    provider: ollama
    model: qwen2.5-coder:14b

limits:
  max_steps: 25
  max_budget: 1.00
  max_depth: 3
```

**Requirements:**

- Gemini API key
- Ollama running with models

### high-quality.yaml

**Best for:** Complex tasks requiring best reasoning

```yaml
root:
  provider: gemini
  model: gemini-2.5-pro

delegate:
  provider: gemini
  model: gemini-2.5-flash

modules:
  architect:
    provider: gemini
    model: gemini-2.5-pro
  coder:
    provider: gemini
    model: gemini-2.5-pro

limits:
  max_steps: 30
  max_budget: 5.00
  max_depth: 4
```

### paper-gpt5.yaml

**Best for:** Replicating MIT paper results

```yaml
root:
  provider: openai
  model: gpt-5

delegate:
  provider: openai
  model: gpt-5-mini

limits:
  max_steps: 50
  max_budget: 10.00
  max_depth: 5
```

**Requirements:**

- OpenAI API key
- Access to GPT-5 models

## Creating Custom Profiles

### Step 1: Copy an existing profile

```bash
cp configs/hybrid.yaml configs/my-custom.yaml
```

### Step 2: Edit the configuration

```yaml
# configs/my-custom.yaml
root:
  provider: ollama
  model: llama3:70b

delegate:
  provider: ollama
  model: llama3:8b

modules:
  coder:
    provider: gemini
    model: gemini-2.5-pro  # Use cloud for code generation

limits:
  max_steps: 40
  max_budget: 2.00
  max_depth: 3
```

### Step 3: Use your profile

```bash
uv run python src/main.py "Your task" --config configs/my-custom.yaml
```

## Provider Configuration

### Ollama (Local)

```yaml
provider: ollama
model: qwen2.5-coder:14b  # Model name as shown in `ollama list`
```

**Available models:**

- `qwen2.5-coder:7b` - Fast, good for simple tasks
- `qwen2.5-coder:14b` - Better quality, slower
- `llama3:8b` - General purpose
- `codellama:34b` - Specialized for code

### Gemini (Google)

```yaml
provider: gemini
model: gemini-2.5-flash   # or gemini-2.5-pro
```

**Requires:** `GEMINI_API_KEY` in `.env`

**Available models:**

- `gemini-2.5-flash` - Fast, cost-effective
- `gemini-2.5-pro` - Highest quality

### OpenAI

```yaml
provider: openai
model: gpt-4o            # or gpt-4o-mini
```

**Requires:** `OPENAI_API_KEY` in `.env`

**Available models:**

- `gpt-4o-mini` - Fast, cost-effective
- `gpt-4o` - High quality
- `gpt-5` - Highest quality (if available)

## Module Roles

The RLM agent has four specialized modules:

| Module | Role | Recommended Model |
|--------|------|-------------------|
| **Architect** | Decides next action (CODE/ANSWER/DELEGATE) | Best reasoning model |
| **Coder** | Generates Python code | Code-specialized model |
| **Responder** | Formats final answers | Fast model |
| **Delegator** | Manages sub-agents | Same as root |

### Per-Module Override Example

```yaml
root:
  provider: gemini
  model: gemini-2.5-flash

# Override specific modules
modules:
  architect:
    provider: gemini
    model: gemini-2.5-pro    # Better reasoning for decisions
  coder:
    provider: ollama
    model: qwen2.5-coder:14b  # Free code generation
  responder:
    provider: gemini
    model: gemini-2.5-flash   # Fast for formatting
```

## Budget Management

### Setting Limits

```yaml
limits:
  max_steps: 25    # Prevents runaway execution
  max_budget: 1.00  # Hard stop when cost exceeds
  max_depth: 3      # Limits recursive delegation
```

### Cost Estimation

Approximate costs per 1000 tokens:

| Provider | Model | Input | Output |
|----------|-------|-------|--------|
| Ollama | Any | Free | Free |
| Gemini | Flash | $0.00025 | $0.00050 |
| Gemini | Pro | $0.00125 | $0.00500 |
| OpenAI | GPT-4o-mini | $0.00015 | $0.00060 |
| OpenAI | GPT-4o | $0.00250 | $0.01000 |

### Monitoring Costs

The agent displays cost information after each run:

```text
Total cost: $0.0234
Tokens used: 15,432 input, 2,341 output
Steps: 12/25
```

## Environment Variables

Create a `.env` file in the project root:

```env
# Required for cloud providers
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Optional: Ollama configuration
OLLAMA_HOST=http://localhost:11434

# Optional: Logging
LOG_LEVEL=INFO
```

## Validation

Validate your configuration:

```bash
# Dry run to check configuration
uv run python src/main.py "test" --config configs/your-profile.yaml --dry-run
```

Common validation errors:

- **Provider not configured:** Missing API key for specified provider
- **Model not found:** Ollama model not downloaded
- **Invalid YAML:** Syntax error in configuration file

## Next Steps

- [Quick Start Guide](../README.md#quick-start)
- [RLM Theory](THEORY.md)
- [Installation Guide](INSTALLATION.md)
