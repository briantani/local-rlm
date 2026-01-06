"""Tests for --prompt-file CLI argument."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

from src.main import main


def test_prompt_file_loads_correctly(tmp_path, monkeypatch):
    """Test that --prompt-file reads task from file."""
    # Create a test prompt file
    prompt_file = tmp_path / "test_prompt.txt"
    task_content = "This is a very long and detailed task description.\n\nIt spans multiple lines."
    prompt_file.write_text(task_content, encoding="utf-8")

    # Create a minimal config file
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("""
profile_name: "Test"
root:
  provider: ollama
  model: qwen2.5-coder:7b
  max_steps: 5
  max_depth: 2
delegate:
  provider: ollama
  model: qwen2.5-coder:7b
  max_steps: 3
  max_depth: 0
budget:
  max_usd: 0.0
""")

    # Mock sys.argv
    test_args = [
        "main.py",
        "--prompt-file", str(prompt_file),
        "--config", str(config_file)
    ]

    with patch.object(sys, "argv", test_args), \
         patch("src.main.RLMAgent") as mock_agent_class, \
         patch("src.main.get_lm_for_role") as mock_get_lm, \
         patch("dspy.configure"):

        # Setup mocks
        mock_agent = MagicMock()
        mock_agent.run.return_value = "Test result"
        mock_agent_class.return_value = mock_agent
        mock_get_lm.return_value = MagicMock()

        # Run main
        main()

        # Verify agent.run was called with the file content
        mock_agent.run.assert_called_once()
        actual_task = mock_agent.run.call_args[0][0]
        assert actual_task == task_content.strip()


def test_prompt_file_not_found(tmp_path, monkeypatch, caplog):
    """Test error handling when prompt file doesn't exist."""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("profile_name: Test\nroot: {provider: ollama, model: test}\ndelegate: {provider: ollama, model: test}\nbudget: {max_usd: 0}")

    test_args = [
        "main.py",
        "--prompt-file", str(tmp_path / "nonexistent.txt"),
        "--config", str(config_file)
    ]

    with patch.object(sys, "argv", test_args):
        main()

    assert "Prompt file not found" in caplog.text


def test_prompt_file_empty(tmp_path, caplog):
    """Test error handling when prompt file is empty."""
    prompt_file = tmp_path / "empty.txt"
    prompt_file.write_text("", encoding="utf-8")

    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("profile_name: Test\nroot: {provider: ollama, model: test}\ndelegate: {provider: ollama, model: test}\nbudget: {max_usd: 0}")

    test_args = [
        "main.py",
        "--prompt-file", str(prompt_file),
        "--config", str(config_file)
    ]

    with patch.object(sys, "argv", test_args):
        main()

    assert "Prompt file is empty" in caplog.text


def test_task_and_prompt_file_mutually_exclusive():
    """Test that providing both task and --prompt-file raises error."""
    test_args = [
        "main.py",
        "Some task",
        "--prompt-file", "prompt.txt",
        "--config", "config.yaml"
    ]

    with patch.object(sys, "argv", test_args), pytest.raises(SystemExit):
        main()


def test_neither_task_nor_prompt_file_raises_error():
    """Test that omitting both task and --prompt-file raises error."""
    test_args = [
        "main.py",
        "--config", "config.yaml"
    ]

    with patch.object(sys, "argv", test_args), pytest.raises(SystemExit):
        main()
