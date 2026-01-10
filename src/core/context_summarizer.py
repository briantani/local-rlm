"""
Context Summarizer for handling large execution contexts.

When the execution context becomes too large for the LLM's context window,
this module provides RAG-like functionality to:
1. Save the full context to the artifacts folder
2. Split context into manageable chunks
3. Summarize each chunk
4. Combine summaries into a coherent final summary

This preserves research results even when context overflow occurs.
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING

import dspy

from src.core.logger import logger

if TYPE_CHECKING:
    from src.core.run_context import RunContext


class ChunkSummarizerSignature(dspy.Signature):
    """Summarize a chunk of execution history, preserving key findings."""
    chunk = dspy.InputField(desc="A section of execution history with code and outputs.")
    task_context = dspy.InputField(desc="Brief description of the overall task being performed.")
    summary = dspy.OutputField(desc="Concise summary of key findings, data, and results from this chunk.")


class FinalSynthesizerSignature(dspy.Signature):
    """Synthesize multiple chunk summaries into a coherent final answer."""
    query = dspy.InputField(desc="The original user query/task.")
    chunk_summaries = dspy.InputField(desc="Summaries from different parts of the execution history.")
    artifacts_info = dspy.InputField(desc="Information about generated files and visualizations.")
    response = dspy.OutputField(
        desc="A well-formatted Markdown response synthesizing all findings into a complete answer."
    )


class ContextSummarizer(dspy.Module):
    """
    RAG-like context summarizer for handling large execution histories.

    When context is too large:
    1. Saves full context to artifacts folder for preservation
    2. Splits context into chunks based on execution steps
    3. Summarizes each chunk independently
    4. Synthesizes chunk summaries into final response
    """

    # Approximate token limit per chunk (conservative estimate: ~4 chars per token)
    CHUNK_SIZE_CHARS = 8000  # ~2000 tokens per chunk
    MAX_CONTEXT_CHARS = 32000  # ~8000 tokens before triggering chunking

    def __init__(self, run_context: "RunContext | None" = None):
        super().__init__()
        self.run_context = run_context
        self.chunk_summarizer = dspy.ChainOfThought(ChunkSummarizerSignature)
        self.synthesizer = dspy.ChainOfThought(FinalSynthesizerSignature)

    def should_chunk(self, context: str) -> bool:
        """Check if context is large enough to require chunking."""
        return len(context) > self.MAX_CONTEXT_CHARS

    def save_full_context(self, context: str, task: str) -> Path | None:
        """Save the full context to artifacts folder for preservation.

        Args:
            context: The full execution history context
            task: The original task description

        Returns:
            Path to saved file, or None if no run_context
        """
        if not self.run_context:
            return None

        # Save as markdown file
        filename = "full_execution_history.md"
        filepath = self.run_context.register_artifact(
            filename,
            artifact_type="data",
            description="Complete execution history with all code and outputs"
        )

        content = "# Full Execution History\n\n"
        content += f"## Task\n\n{task}\n\n"
        content += f"## Execution Details\n\n{context}"

        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Saved full execution history to {filepath}")

        return filepath

    def split_into_chunks(self, context: str) -> list[str]:
        """Split context into manageable chunks based on execution steps.

        Args:
            context: The full execution history

        Returns:
            List of context chunks, each containing complete steps
        """
        # Split by step markers
        step_pattern = r"(--- Step \d+ ---)"
        parts = re.split(step_pattern, context)

        # Recombine step markers with their content
        chunks = []
        current_chunk = ""

        i = 0
        while i < len(parts):
            part = parts[i]

            # Check if this is a step marker
            if re.match(step_pattern, part) and i + 1 < len(parts):
                step_content = part + parts[i + 1]
                i += 2
            else:
                step_content = part
                i += 1

            # Check if adding this step would exceed chunk size
            if len(current_chunk) + len(step_content) > self.CHUNK_SIZE_CHARS and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = step_content
            else:
                current_chunk += step_content

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # If no steps found, split by character count
        if len(chunks) <= 1 and len(context) > self.CHUNK_SIZE_CHARS:
            chunks = []
            for i in range(0, len(context), self.CHUNK_SIZE_CHARS):
                chunk = context[i:i + self.CHUNK_SIZE_CHARS]
                # Try to break at a newline for cleaner chunks
                if i + self.CHUNK_SIZE_CHARS < len(context):
                    last_newline = chunk.rfind("\n")
                    if last_newline > self.CHUNK_SIZE_CHARS // 2:
                        chunk = chunk[:last_newline]
                chunks.append(chunk)

        logger.info(f"Split context into {len(chunks)} chunks")
        return chunks

    def summarize_chunk(self, chunk: str, task_brief: str) -> str:
        """Summarize a single chunk of context.

        Args:
            chunk: A portion of the execution history
            task_brief: Brief description of the task (first 200 chars)

        Returns:
            Summary of the chunk's key findings
        """
        try:
            result = self.chunk_summarizer(chunk=chunk, task_context=task_brief)
            return result.summary or ""
        except Exception as e:
            logger.warning(f"Chunk summarization failed: {e}")
            # Return first and last parts of chunk as fallback
            if len(chunk) > 500:
                return f"[Partial] {chunk[:200]}...\n...[End] {chunk[-200:]}"
            return chunk

    def forward(
        self,
        query: str,
        context: str,
        artifacts_info: str = ""
    ) -> dspy.Prediction:
        """Summarize large context using RAG-like chunking approach.

        Args:
            query: The original task/query
            context: The full execution history (potentially very large)
            artifacts_info: Information about generated artifacts

        Returns:
            Prediction with synthesized response
        """
        # Save full context first (for preservation)
        saved_path = self.save_full_context(context, query)
        if saved_path:
            artifacts_info += f"\n\nFull execution history saved to: {saved_path.name}"

        # Split into chunks
        chunks = self.split_into_chunks(context)

        # Get task brief for context
        task_brief = query[:200] + "..." if len(query) > 200 else query

        # Summarize each chunk
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Summarizing chunk {i + 1}/{len(chunks)}")
            summary = self.summarize_chunk(chunk, task_brief)
            if summary:
                chunk_summaries.append(f"### Section {i + 1}\n{summary}")

        # Combine summaries
        combined_summaries = "\n\n".join(chunk_summaries)

        # Final synthesis
        try:
            result = self.synthesizer(
                query=query,
                chunk_summaries=combined_summaries,
                artifacts_info=artifacts_info
            )
            return result
        except Exception as e:
            logger.error(f"Final synthesis failed: {e}")
            # Fallback: return combined summaries directly
            fallback_response = f"# Task Summary\n\n{combined_summaries}"
            if artifacts_info:
                fallback_response += f"\n\n## Generated Artifacts\n\n{artifacts_info}"
            return dspy.Prediction(response=fallback_response)
