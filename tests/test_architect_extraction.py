"""
Tests for Architect's _extract_action method.

This tests the robust action extraction that handles verbose LLM outputs
like "1. CATEGORIZE THE ARTICLES..." instead of clean "ANSWER".
"""

import pytest
from src.modules.architect import Architect


class TestExtractAction:
    """Unit tests for the _extract_action method."""

    @pytest.fixture
    def architect(self) -> Architect:
        """Create an Architect instance for testing."""
        return Architect()

    # Test clean, valid actions
    @pytest.mark.parametrize("raw_action,expected", [
        ("ANSWER", "ANSWER"),
        ("CODE", "CODE"),
        ("DELEGATE", "DELEGATE"),
        ("answer", "ANSWER"),
        ("code", "CODE"),
        ("delegate", "DELEGATE"),
        ("Answer", "ANSWER"),
        ("Code", "CODE"),
        ("Delegate", "DELEGATE"),
    ])
    def test_clean_action_words(self, architect: Architect, raw_action: str, expected: str):
        """Test that clean action words are returned correctly."""
        result = architect._extract_action(raw_action)
        assert result == expected

    # Test actions with whitespace
    @pytest.mark.parametrize("raw_action,expected", [
        ("  ANSWER  ", "ANSWER"),
        ("\nCODE\n", "CODE"),
        ("\tDELEGATE\t", "DELEGATE"),
        ("  answer  ", "ANSWER"),
    ])
    def test_action_with_whitespace(self, architect: Architect, raw_action: str, expected: str):
        """Test that actions with whitespace are handled correctly."""
        result = architect._extract_action(raw_action)
        assert result == expected

    # Test verbose outputs that start with valid action
    @pytest.mark.parametrize("raw_action,expected", [
        ("ANSWER: The capital of France is Paris", "ANSWER"),
        ("CODE: I will write Python to calculate this", "CODE"),
        ("DELEGATE: This requires splitting into subtasks", "DELEGATE"),
        ("Answer - I can directly respond", "ANSWER"),
        ("Code; generating Python solution", "CODE"),
    ])
    def test_action_at_start(self, architect: Architect, raw_action: str, expected: str):
        """Test that actions at the start of verbose output are extracted."""
        result = architect._extract_action(raw_action)
        assert result == expected

    # Test verbose numbered/instructional outputs (behavior depends on keywords)
    @pytest.mark.parametrize("raw_action,expected", [
        ("1. CATEGORIZE THE ARTICLES BASED ON THEIR MAIN TOPIC", "ANSWER"),
        ("1. First, I will analyze the data", "CODE"),  # Contains ANALYZE keyword
        ("Step 1: Review the information", "ANSWER"),  # STEP keyword triggers ANSWER
        ("Here are the steps to solve this problem:", "ANSWER"),  # STEP keyword triggers ANSWER
    ])
    def test_numbered_instructions_behavior(self, architect: Architect, raw_action: str, expected: str):
        """Test numbered lists/instructions handling based on keywords."""
        result = architect._extract_action(raw_action)
        assert result == expected

    # Test embedded action keywords with heuristics
    @pytest.mark.parametrize("raw_action,expected", [
        ("First, I will CALCULATE the result using Python", "CODE"),
        ("I need to COMPUTE this mathematically", "CODE"),
        ("Let me ANALYZE this with code", "CODE"),
        ("I will EXECUTE a Python script", "CODE"),
        ("I need to DELEGATE this to subtasks", "DELEGATE"),
        ("Let me SPLIT this problem into parts", "DELEGATE"),
        ("This should be DIVIDED into smaller tasks", "DELEGATE"),
        ("I can EXPLAIN this concept directly", "ANSWER"),
        ("The response is straightforward", "ANSWER"),
        ("I know the answer directly", "ANSWER"),
    ])
    def test_heuristic_keyword_matching(self, architect: Architect, raw_action: str, expected: str):
        """Test that heuristic keywords are detected correctly."""
        result = architect._extract_action(raw_action)
        assert result == expected

    # Test word boundary detection for embedded actions
    @pytest.mark.parametrize("raw_action,expected", [
        # When both ANSWER and CODE appear, first one wins (by position)
        ("The answer is: CODE the solution", "ANSWER"),  # ANSWER appears before CODE
        ("I think we should ANSWER this directly", "ANSWER"),
        ("Perhaps DELEGATE is the best approach", "DELEGATE"),
        ("Use CODE to solve this, then ANSWER", "CODE"),  # CODE appears first
    ])
    def test_word_boundary_matching(self, architect: Architect, raw_action: str, expected: str):
        """Test that actions are found as complete words, first occurrence wins."""
        result = architect._extract_action(raw_action)
        assert result == expected

    # Test edge cases
    @pytest.mark.parametrize("raw_action,expected", [
        ("", "ANSWER"),  # Empty string defaults to ANSWER
        ("   ", "ANSWER"),  # Whitespace only defaults to ANSWER
        ("Random gibberish without any action words", "ANSWER"),
        ("CODING is not the same as CODE", "CODE"),  # But CODING contains CODE keyword
        ("ANSWERING is not ANSWER", "ANSWER"),  # ANSWERING contains ANSWER keyword
    ])
    def test_edge_cases(self, architect: Architect, raw_action: str, expected: str):
        """Test edge cases and fallback behavior."""
        result = architect._extract_action(raw_action)
        assert result == expected

    # Test real-world verbose outputs from LLMs
    @pytest.mark.parametrize("raw_action,expected", [
        # Real example from qwen2.5-coder - numbered list without keywords
        ("""1. CATEGORIZE THE ARTICLES BASED ON THEIR MAIN TOPIC
        2. EXTRACT KEY INFORMATION
        3. SUMMARIZE THE FINDINGS""", "ANSWER"),
        # Numbered list - STEP keyword triggers ANSWER even with CALCULATE
        ("""To solve this problem, I will:
        1. Parse the input
        2. Calculate the result
        3. Return the answer""", "ANSWER"),  # STEP pattern takes precedence
        # Direct answer with explanation
        ("""ANSWER

        The Fibonacci sequence starts with 0 and 1...""", "ANSWER"),
        # Code decision with reasoning
        ("""I need to write CODE to calculate this because
        it requires precise mathematical computation.""", "CODE"),
    ])
    def test_real_world_llm_outputs(self, architect: Architect, raw_action: str, expected: str):
        """Test handling of real-world verbose LLM outputs."""
        result = architect._extract_action(raw_action)
        assert result == expected

    # Test that the method doesn't mutate state
    def test_no_state_mutation(self, architect: Architect):
        """Test that _extract_action is a pure function."""
        initial_state = str(architect.__dict__)
        architect._extract_action("ANSWER")
        architect._extract_action("CODE")
        architect._extract_action("Some verbose output")
        final_state = str(architect.__dict__)
        assert initial_state == final_state
