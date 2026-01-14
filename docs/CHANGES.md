# Changelog — Recent Enhancements (Issues #26–#30)

This document summarizes the feature work completed in Issues #26 through #30: artifact tracking, context preservation, final assembly enforcement, intermediate consistency checks, and prompt/signature refinements.

## Overview

The following changes improve reproducibility, traceability, and robustness of the agent's code-execute-report loop.

- Automatic artifact discovery and registration
- Artifact metadata with preserved context (prompt, section, rationale)
- Final assembly step to guarantee all artifacts are referenced in the final report
- Intermediate consistency checks and retries when artifacts declared by the coder are missing
- DSPy signature and prompt updates to expose artifact metadata and expected artifacts

## Key APIs and Usage

### `RunContext.register_artifact(filename, artifact_type, description, *, prompt=None, section=None, rationale=None)`

Register an artifact with optional context:

```py
from src.core.run_context import RunContext
rc = RunContext()
path = rc.register_artifact(
    "chart.png",
    artifact_type="image",
    description="Sales by quarter",
    prompt="Plot quarterly sales for 2025",
    section="Results",
    rationale="Shows seasonal trend",
)
```

The metadata is stored in `rc.artifacts` and is available to the `Responder` when assembling reports.

### Coder: Declaring Expected Artifacts

`Coder` can indicate files it intends to create by including an inline comment in generated code:

```py
# EXPECTED_ARTIFACTS: sales_chart.png, summary.csv
plt.savefig(f"{output_dir}/sales_chart.png")
# ...
```

The `RLMAgent` reads this from the `Coder` prediction (`expected_artifacts`) and validates that these files appear in the run's artifacts. If missing, the agent will retry coder generation up to `max_retries` (default 2) and log errors if artifacts remain missing.

### Final Assembly: `RunContext.finalize_report()`

Before saving the final report, the agent calls `finalize_report()` which:

- Scans `rc.artifacts` and ensures each filename is referenced in the report text
- Appends descriptive blocks for any missing artifact (using `section`, `rationale`, `prompt` metadata when present)
- Optionally adds an `Artifacts Summary` table to the end of the report

Example usage in agent flow (automated):

```py
rc.add_to_report(final_answer)
assembly = rc.finalize_report()
rc.save_report()
```

### Responder Embedding

`Responder` will include artifact metadata when enhancing responses. For images, it will embed the image plus the `section`, `rationale`, and `prompt` if provided.

## Module Signature Changes

- `CoderSignature` now exposes an optional `expected_artifacts` output field (parsed from `# EXPECTED_ARTIFACTS:` comments in code).
- `ArchitectSignature` and `ResponderSignature` now accept `artifacts_info` as input, allowing modules to reason about known artifacts and their sections when deciding next actions or composing reports.

## Examples

- Adding an artifact with context in generated code (coder should also call `register_artifact` via REPL when saving files):

```py
# In generated code
plt.savefig(f"{output_dir}/chart.png")
# EXPECTED_ARTIFACTS: chart.png
print('Saved chart')
```

- Expected artifact missing: the agent will retry coder up to `max_retries`.

## Debugging and Logs

- The agent logs artifact scan results, retries, and the final assembly additions. Look for messages like:

```
WARNING: Missing artifacts after execution: ['chart.png']. Retry 1/2.
INFO: Saved final report to runs/20260113_123456/report.md
```

## Tests

Unit tests were added for:

- Artifact context storage and `Responder` embedding (`tests/test_artifact_context.py`) 
- Final assembly behavior (`tests/test_final_assembly.py`)
- Intermediate consistency checks and retry flow (`tests/test_intermediate_checks.py`)
- Coder expected artifacts parsing (`tests/test_signature_prompts.py`)

## Notes for Developers

- Keep `register_artifact` calls consistent when writing files from generated code. Prefer the agent's `RunContext.register_artifact()` for metadata-rich registration.
- Use `# EXPECTED_ARTIFACTS:` comments to help the agent validate outputs and avoid silent omissions in final reports.

## Acknowledgements

These enhancements are aimed at improving the reproducibility and trustworthiness of automated code generation and reporting. They were implemented as part of ongoing work to make the RLM agent production-ready.
