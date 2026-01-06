# Task Prompt Files

This directory contains example task descriptions that can be used with the
`--prompt-file` CLI argument.

## Usage

```bash
uv run python src/main.py --prompt-file tasks/ai-research-example.txt \
  --config configs/high-quality.yaml
```

## Creating Your Own Prompts

Task files should be plain text (`.txt`) or markdown (`.md`) with detailed
descriptions of what you want the agent to accomplish.

### Best Practices

1. **Be Specific**: Clearly define objectives and deliverables
2. **Structure Your Request**: Use sections/headings for complex tasks
3. **Specify Output Format**: Describe what the final result should look like
4. **Include Examples**: Show what you mean when possible
5. **Define Success Criteria**: What does "done" look like?

### Example Structure

```text
# Task Title

## Objective
What you want to accomplish

## Deliverables
- Item 1
- Item 2

## Methodology
How to approach the task

## Output Format
What the result should look like

## Success Criteria
How to know if the task was completed successfully
```

## Examples Included

- `ai-research-example.txt` - Complex research analysis with visualizations
  and report generation

## Notes

- Task files are read with UTF-8 encoding
- Leading/trailing whitespace is automatically stripped
- Empty files will produce an error
- File content becomes the task description exactly as written
