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

    # Mock the TaskService.run_task method
    with patch.object(sys, "argv", test_args), \
         patch("src.main.TaskService") as mock_task_service_class:

        # Setup mocks
        mock_task_service = MagicMock()
        mock_result = MagicMock()
        mock_result.answer = "Test result"
        mock_result.model_breakdown = {}
        mock_result.total_cost = 0.0
        mock_result.duration_seconds = 1.0
        mock_result.step_count = 1
        mock_task_service.run_task.return_value = mock_result
        mock_task_service_class.return_value = mock_task_service

        # Run main
        main()

        # Verify run_task was called with the file content
        mock_task_service.run_task.assert_called_once()
        call_kwargs = mock_task_service.run_task.call_args
        actual_task = call_kwargs.kwargs.get("task") or call_kwargs.args[0]
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
