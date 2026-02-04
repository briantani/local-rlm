"""
Fallback and RAG-based summarization for RLM Agent.

Provides alternative response generation when primary methods fail or context is too large.
"""

from typing import TYPE_CHECKING

from src.core.logger import logger

if TYPE_CHECKING:
    from src.core.run_context import RunContext
    from src.core.context_summarizer import ContextSummarizer


class AgentFallbacks:
    """Manages fallback answer generation and RAG-based summarization."""

    def __init__(
        self,
        run_context: "RunContext | None" = None,
        context_summarizer: "ContextSummarizer | None" = None,
        responder: object | None = None,
    ):
        """
        Initialize fallback handler.

        Args:
            run_context: Optional run context for artifact tracking
            context_summarizer: Optional summarizer for RAG approach
            responder: Optional responder module for enhancing with artifacts
        """
        self.run_context = run_context
        self.context_summarizer = context_summarizer
        self.responder = responder

    def generate_fallback_answer(self, task: str, history: list[tuple[str, str]]) -> str:
        """
        Generate a fallback answer when Responder returns None.

        This happens when context is too long or model fails to produce output.
        Uses execution history to summarize what was accomplished.

        Args:
            task: The original task query
            history: Execution history as list of (action, output) tuples

        Returns:
            A summary of what was accomplished based on execution history
        """
        if not history:
            return "Task completed but no summary available."

        # Count artifacts if available
        artifact_info = ""
        if self.run_context:
            images = self.run_context.list_images()
            if images:
                artifact_info = f"\n\nGenerated {len(images)} visualization(s):\n"
                for img in images:
                    artifact_info += f"- {img['filename']}\n"

        # Count code executions
        code_count = sum(1 for action, _ in history if "Code" in action or "Executed" in action)

        # Get last few outputs (last 3 meaningful ones)
        recent_outputs = []
        for action, output in reversed(history[-5:]):
            if output and output.strip() and len(output) < 500:
                recent_outputs.append(output.strip())
            if len(recent_outputs) >= 2:
                break

        summary = f"Task completed after {len(history)} steps with {code_count} code executions."
        if artifact_info:
            summary += artifact_info
        if recent_outputs:
            summary += "\n\nRecent outputs:\n" + "\n".join(recent_outputs[:2])

        return summary

    def summarize_with_rag(self, task: str, context: str, indent: str) -> str:
        """
        Use RAG-like chunked summarization for large contexts.

        This method:
        1. Saves the full context to artifacts (preserves research)
        2. Splits context into chunks
        3. Summarizes each chunk independently
        4. Synthesizes into final response

        Args:
            task: The original task query
            context: The full execution history (potentially very large)
            indent: Log indentation for depth tracking

        Returns:
            Synthesized response from chunked summaries
        """
        if not self.context_summarizer:
            logger.warning(f"{indent}No context summarizer available. Using basic fallback.")
            # For RAG fallback, we need to pass history but we don't have direct access
            # This is a limitation - caller should use generate_fallback_answer directly
            return "Task completed but detailed summary unavailable (no summarizer)."

        # Build artifacts info for the summarizer
        artifacts_info = ""
        if self.run_context:
            images = self.run_context.list_images()
            if images:
                artifacts_info = "Generated visualizations:\n"
                for img in images:
                    artifacts_info += f"- {img['filename']}: {img.get('description', 'Image')}\n"

        try:
            logger.info(f"{indent}Running RAG-like summarization on {len(context)} chars...")
            result = self.context_summarizer(
                query=task,
                context=context,
                artifacts_info=artifacts_info
            )

            response = result.response
            if response:
                # Enhance with artifact images if responder has run_context
                if self.responder and self.run_context and hasattr(self.responder, '_enhance_with_artifacts'):
                    response = self.responder._enhance_with_artifacts(response)
                return response
            else:
                logger.warning(f"{indent}RAG summarization returned None. Needs fallback from caller.")
                return ""  # Signal to caller to use generate_fallback_answer

        except Exception as e:
            logger.error(f"{indent}RAG summarization failed: {e}")
            return ""  # Signal to caller to use generate_fallback_answer
