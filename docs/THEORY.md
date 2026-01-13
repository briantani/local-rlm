# Recursive Language Model (RLM) Theory

This document explains the theoretical foundation of the RLM agent, based on
the research from MIT CSAIL.

## Research Paper

**Title:** Recursive Language Models
**Authors:** MIT CSAIL
**Reference:** [arXiv:2512.24601v1](https://arxiv.org/html/2512.24601v1)

## What is an RLM?

A **Recursive Language Model** is an agentic architecture that solves
complex problems by recursively generating, executing, and refining Python
code in a stateful environment. Unlike traditional Chain-of-Thought (CoT)
approaches, an RLM can:

1. **Offload computation** to a Python REPL (Read-Eval-Print Loop)
2. **Manage its own context window** more effectively
3. **Spawn sub-agents** via `recursive_llm()` in generated code
4. **Learn from execution feedback** to refine its approach

## Core Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                      User Task                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      ARCHITECT                              │
│  Decides: CODE | ANSWER                                     │
│  Uses compiled DSPy module with few-shot examples           │
└─────────────────────────────────────────────────────────────┘
         │                         │
         ▼                         ▼
    ┌─────────┐              ┌──────────┐
    │  CODER  │              │RESPONDER │
    │Generate │              │ Answer   │
    │ Python  │              │ directly │
    │  code   │              │          │
    └────┬────┘              └──────────┘
         │
         ▼
    ┌─────────────────────┐
    │        REPL         │
    │   Execute code      │
    │  recursive_llm()    │◄─── spawns sub-agents
    └─────────┬───────────┘
              │
              ▼
    ┌─────────┐
    │ Output  │
    │ + State │
    └─────────┘
         │
         └──────────► Back to ARCHITECT (loop)
```

## The Decision Loop

The agent operates in a **recursive decision loop**:

### Step 1: Architect Decides

The Architect module receives:

- The original query
- Current execution history (code run, outputs received)
- Available context (files, previous results)

It outputs one of two actions:

| Action | When Used | Next Step |
|--------|-----------|-----------||
| **CODE** | Need computation, data processing, file ops, or complex sub-tasks | Generate and execute Python (can call `recursive_llm()`) |
| **ANSWER** | Have enough information to respond | Generate final answer |

### Step 2: Execute Action

**If CODE:**

1. **Coder** generates Python code
2. **REPL** executes in stateful sandbox
3. Output (stdout/errors) captured
4. Code can call `recursive_llm(sub_query, context)` to spawn sub-agents
5. Loop back to Architect with new context

**If ANSWER:**

1. **Responder** formats final answer
2. Include any generated artifacts (images, reports)
3. Return to user

## Key Innovations

### 1. Stateful REPL

Unlike one-shot code generation, the REPL maintains state:

```python
# Step 1: Load data
df = pd.read_csv('data.csv')

# Step 2: (separate execution) Use previously loaded data
result = df.groupby('category').sum()
```

Variables persist across executions, enabling iterative problem-solving.

### 2. Emergent Recursion via recursive_llm()

For complex tasks, generated code can spawn sub-agents using `recursive_llm()`:

```python
# Generated code can call recursive_llm() for sub-tasks
results = []
for doc in documents[:4]:
    result = recursive_llm(f"Analyze this document: {doc}", context)
    results.append(result)
print("\n".join(results))
```

Each sub-agent has its own REPL and context, with depth limits to prevent
infinite recursion. Sub-agents use the `delegate` config section for model selection.

### 3. DSPy Optimization

Modules are optimized using DSPy's compiler:

- **BootstrapFewShot**: Learns from examples
- **MIPROv2**: Bayesian optimization of prompts
- Compiled weights stored in JSON files

## Paper Results

The original research achieved impressive results:

| Benchmark | RLM Score | Base Model Score |
|-----------|-----------|------------------|
| BrowseComp+ (1K docs) | 91.33% | 0% |
| OOLONG-Pairs | 58.00% F1 | 0.04% |
| CodeQA | 62.00% | 24% |

These results used GPT-5 for root agent and GPT-5-mini for sub-agents.

## Implementation Details

### Thread Safety

This implementation uses **Python 3.14.2 (Free-Threaded)**, which removes
the GIL. This enables true parallel execution of delegate agents but
requires careful thread-safety:

- `BudgetManager` uses `threading.Lock` for cost tracking
- REPL instances are per-agent (no shared state)
- Artifacts use run-specific directories

### Budget Control

Token costs are tracked per-model with configurable limits:

```yaml
budget:
  max_usd: 10.0
  input_price_per_1m: 0.075
  output_price_per_1m: 0.30
```

Exceeding budget raises `BudgetExceededError` and halts execution.

### Artifact Management

Generated files (images, reports, data) are saved to run-specific
directories:

```text
runs/
└── 20260110_093322/
    ├── report.md
    ├── chart.png
    └── data.csv
```

Code can access `__artifacts_dir__` to save outputs.

## Further Reading

- [Original Paper (arXiv)](https://arxiv.org/html/2512.24601v1)
- [Configuration Guide](CONFIGURATION.md)
- [Installation Guide](INSTALLATION.md)
