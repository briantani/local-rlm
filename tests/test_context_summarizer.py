"""Tests for the ContextSummarizer module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import shutil

from src.core.context_summarizer import ContextSummarizer
from src.core.run_context import RunContext


class TestContextSummarizer:
    """Unit tests for ContextSummarizer."""

    def test_should_chunk_small_context(self):
        """Small context should not require chunking."""
        summarizer = ContextSummarizer()
        small_context = "Step 1: print('hello')\nOutput: hello"
        assert not summarizer.should_chunk(small_context)

    def test_should_chunk_large_context(self):
        """Large context should require chunking."""
        summarizer = ContextSummarizer()
        # Create a context larger than MAX_CONTEXT_CHARS (32000)
        large_context = "x" * 50000
        assert summarizer.should_chunk(large_context)

    def test_split_into_chunks_by_steps(self):
        """Context should be split by step markers."""
        summarizer = ContextSummarizer()

        context = """--- Step 1 ---
Input: print('hello')
Output: hello
--- Step 2 ---
Input: print('world')
Output: world
--- Step 3 ---
Input: x = 42
Output:
"""
        chunks = summarizer.split_into_chunks(context)
        # Should have at least 1 chunk (small context fits in one)
        assert len(chunks) >= 1

    def test_split_large_context_into_multiple_chunks(self):
        """Large context should be split into multiple chunks."""
        summarizer = ContextSummarizer()

        # Create context with many steps, each step is ~1000 chars
        steps = []
        for i in range(20):
            step = f"--- Step {i} ---\n"
            step += f"Input: code = {'x' * 800}\n"
            step += f"Output: result_{i}\n"
            steps.append(step)

        context = "\n".join(steps)
        chunks = summarizer.split_into_chunks(context)

        # Should have multiple chunks
        assert len(chunks) > 1

    def test_save_full_context_without_run_context(self):
        """Saving context without run_context should return None."""
        summarizer = ContextSummarizer(run_context=None)
        result = summarizer.save_full_context("test context", "test task")
        assert result is None

    def test_save_full_context_with_run_context(self):
        """Saving context with run_context should create file."""
        # Create a temporary directory for test
        temp_dir = Path(tempfile.mkdtemp())
        try:
            run_context = RunContext(run_id="test_run", base_dir=temp_dir)
            summarizer = ContextSummarizer(run_context=run_context)

            test_context = "Step 1: executed code\nOutput: result"
            test_task = "Calculate something"

            result = summarizer.save_full_context(test_context, test_task)

            assert result is not None
            assert result.exists()
            assert "full_execution_history.md" in result.name

            # Verify content
            content = result.read_text()
            assert "Calculate something" in content
            assert "Step 1: executed code" in content
        finally:
            shutil.rmtree(temp_dir)

    def test_chunk_size_constants(self):
        """Verify chunk size constants are reasonable."""
        summarizer = ContextSummarizer()
        # CHUNK_SIZE_CHARS should be less than MAX_CONTEXT_CHARS
        assert summarizer.CHUNK_SIZE_CHARS < summarizer.MAX_CONTEXT_CHARS
        # Both should be positive
        assert summarizer.CHUNK_SIZE_CHARS > 0
        assert summarizer.MAX_CONTEXT_CHARS > 0


class TestContextSummarizerIntegration:
    """Integration tests requiring LLM (marked for optional running)."""

    @pytest.mark.integration
    def test_summarize_chunk_with_mock_lm(self):
        """Test chunk summarization with mocked LLM."""
        summarizer = ContextSummarizer()

        # Mock the chunk_summarizer to avoid real LLM calls
        with patch.object(summarizer, 'chunk_summarizer') as mock_summarizer:
            mock_result = MagicMock()
            mock_result.summary = "This chunk executed print statements."
            mock_summarizer.return_value = mock_result

            result = summarizer.summarize_chunk(
                "print('hello')\nOutput: hello",
                "Test task"
            )

            assert result == "This chunk executed print statements."

    @pytest.mark.integration
    def test_forward_with_mock_lm(self):
        """Test full forward pass with mocked LLMs."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            run_context = RunContext(run_id="test_run", base_dir=temp_dir)
            summarizer = ContextSummarizer(run_context=run_context)

            # Mock both summarizers
            with patch.object(summarizer, 'chunk_summarizer') as mock_chunk, \
                 patch.object(summarizer, 'synthesizer') as mock_synth:

                mock_chunk_result = MagicMock()
                mock_chunk_result.summary = "Chunk summary"
                mock_chunk.return_value = mock_chunk_result

                mock_synth_result = MagicMock()
                mock_synth_result.response = "Final synthesized answer"
                mock_synth.return_value = mock_synth_result

                # Create a large context to trigger chunking
                large_context = "--- Step 1 ---\n" + "x" * 50000

                result = summarizer(
                    query="Test task",
                    context=large_context,
                    artifacts_info="1 image generated"
                )

                assert result.response == "Final synthesized answer"

                # Verify full context was saved
                saved_files = list(run_context.artifacts_dir.glob("*.md"))
                assert any("full_execution_history" in f.name for f in saved_files)

        finally:
            shutil.rmtree(temp_dir)
