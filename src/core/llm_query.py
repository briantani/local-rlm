"""
LLM Query Function for REPL - Paper-inspired recursive sub-LM calls.

Based on MIT CSAIL's RLM paper (arXiv:2512.24601v1), this module provides
an `llm_query` function that can be called from within generated code to
make recursive LLM calls on context chunks.

This enables the agent to:
1. Process large contexts by chunking and querying sub-LMs
2. Verify answers through sub-LM calls
3. Aggregate results from multiple sub-queries programmatically
"""

import logging
from typing import TYPE_CHECKING

import dspy

if TYPE_CHECKING:
    from src.core.budget import BudgetManager

logger = logging.getLogger(__name__)


class SubQuerySignature(dspy.Signature):
    """Process a chunk of context and answer a specific question about it."""
    query = dspy.InputField(desc="The question to answer about the context chunk.")
    context_chunk = dspy.InputField(desc="A chunk of text/data to analyze.")
    response = dspy.OutputField(desc="The answer based on analyzing the context chunk.")


class LLMQueryFunction:
    """
    Callable LLM query function for use in REPL.

    This allows generated code to make recursive LLM calls like:

        result = llm_query("Summarize this section", context[0:10000])
        result = llm_query("Extract all dates", document_text)
        results = [llm_query(f"Classify: {line}", line) for line in lines[:10]]

    The paper shows this is key for handling 10M+ token contexts.
    """

    def __init__(
        self,
        budget_manager: "BudgetManager | None" = None,
        max_chunk_size: int = 50000,  # ~12.5k tokens
    ):
        """
        Initialize the LLM query function.

        Args:
            budget_manager: Optional budget manager for cost tracking
            max_chunk_size: Maximum characters per chunk (auto-truncates)
        """
        self.budget_manager = budget_manager
        self.max_chunk_size = max_chunk_size
        self.sub_lm = dspy.ChainOfThought(SubQuerySignature)
        self._call_count = 0

    def __call__(self, query: str, context_chunk: str = "") -> str:
        """
        Make a recursive LLM call to process a context chunk.

        Args:
            query: The question to answer about the chunk
            context_chunk: The text to analyze (auto-truncated if too long)

        Returns:
            The LLM's response as a string

        Example:
            >>> result = llm_query("What is the main topic?", document[:5000])
            >>> dates = llm_query("Extract all dates mentioned", text)
        """
        self._call_count += 1

        # Truncate if too long
        if len(context_chunk) > self.max_chunk_size:
            context_chunk = context_chunk[:self.max_chunk_size] + "\n... [truncated]"
            logger.warning(f"llm_query: Context truncated to {self.max_chunk_size} chars")

        try:
            logger.debug(f"llm_query call #{self._call_count}: {query[:50]}...")
            result = self.sub_lm(query=query, context_chunk=context_chunk)
            response = result.response or ""
            logger.debug(f"llm_query result: {response[:100]}...")
            return response
        except Exception as e:
            logger.error(f"llm_query failed: {e}")
            return f"[Error in llm_query: {e}]"

    @property
    def call_count(self) -> int:
        """Get the number of llm_query calls made."""
        return self._call_count

    def reset_count(self) -> None:
        """Reset the call counter."""
        self._call_count = 0


def create_llm_query(budget_manager: "BudgetManager | None" = None) -> LLMQueryFunction:
    """
    Factory function to create an llm_query function for REPL.

    Args:
        budget_manager: Optional budget manager for cost tracking

    Returns:
        LLMQueryFunction instance callable as llm_query(query, context)
    """
    return LLMQueryFunction(budget_manager=budget_manager)
