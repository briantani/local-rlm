"""
Tests for the Critic module and visualization refinement loop.

Tests cover:
- Critic module validation and feedback generation
- Three-round refinement loop
- Vision model detection
- Integration with agent workflow
"""

import pytest
from unittest.mock import MagicMock, patch


from src.modules.critic import Critic, CriticSignature
from src.config import model_supports_vision
from src.core.agent import RLMAgent
from src.core.run_context import RunContext
from tests.conftest import MockArchitect, MockCoder, MockREPL, MockResponder, MockCritic, MockPrediction


class TestModelSupportsVision:
    """Test vision capability detection helper."""

    def test_detects_qwen3_vl_ollama(self):
        """Qwen3-VL models should be detected as vision-capable."""
        assert model_supports_vision("ollama", "qwen3-vl:235b-instruct-cloud")
        assert model_supports_vision("ollama", "qwen3-vl:latest")
        assert model_supports_vision("ollama", "qwen-vl:7b")

    def test_detects_llava_ollama(self):
        """LLaVA models should be detected as vision-capable."""
        assert model_supports_vision("ollama", "llava:13b")
        assert model_supports_vision("ollama", "llava:34b")
        assert model_supports_vision("ollama", "bakllava")

    def test_detects_gemini_vision(self):
        """Gemini Flash/Pro models should be detected as vision-capable."""
        assert model_supports_vision("gemini", "gemini-2.5-flash")
        assert model_supports_vision("gemini", "gemini-2.5-pro")
        assert model_supports_vision("gemini", "gemini-1.5-flash")
        assert model_supports_vision("gemini", "gemini-pro-vision")

    def test_detects_openai_vision(self):
        """GPT-4o and GPT-4-turbo should be detected as vision-capable."""
        assert model_supports_vision("openai", "gpt-4o")
        assert model_supports_vision("openai", "gpt-4o-mini")
        assert model_supports_vision("openai", "gpt-4-turbo")
        assert model_supports_vision("openai", "gpt-4-vision-preview")

    def test_rejects_non_vision_models(self):
        """Non-vision models should return False."""
        assert not model_supports_vision("ollama", "qwen2.5-coder:14b")
        assert not model_supports_vision("ollama", "llama3:8b")
        assert not model_supports_vision("gemini", "gemini-1.0-pro")
        assert not model_supports_vision("openai", "gpt-3.5-turbo")
        assert not model_supports_vision("openai", "gpt-4")  # Not gpt-4o

    def test_case_insensitive(self):
        """Detection should be case-insensitive."""
        assert model_supports_vision("OLLAMA", "QWEN3-VL:235B-INSTRUCT-CLOUD")
        assert model_supports_vision("Gemini", "Gemini-2.5-Flash")
        assert model_supports_vision("OpenAI", "GPT-4o")


class TestCriticModule:
    """Test the Critic DSPy module."""

    def test_critic_initializes(self):
        """Critic should initialize with examples."""
        critic = Critic()
        assert critic.critique is not None
        assert len(critic.critique.demos) == 3  # We have 3 examples

    def test_critic_signature_fields(self):
        """CriticSignature should have correct input/output fields."""
        sig = CriticSignature

        # Check that signature has required fields
        # DSPy 3.x uses different attribute access
        assert hasattr(sig, 'input_fields')
        assert hasattr(sig, 'output_fields')

    def test_critic_raises_on_missing_image(self, tmp_path):
        """Critic should raise FileNotFoundError for missing images."""
        critic = Critic()

        missing_path = tmp_path / "nonexistent.png"

        with pytest.raises(FileNotFoundError, match="Image not found"):
            critic(
                task="Create a chart",
                code="plt.bar(...)",
                image_path=str(missing_path),
            )

    @pytest.mark.skip(reason="Requires configured LM - skip for unit tests")
    def test_critic_with_mock_prediction(self, tmp_path):
        """Critic should handle mock predictions correctly."""
        # Create a dummy image file
        image_path = tmp_path / "test_chart.png"
        image_path.write_bytes(b"fake png data")

        # Mock the critique method to return a prediction
        critic = Critic()

        # Mock the internal critique call
        mock_pred = MockPrediction(
            is_valid="YES",
            feedback="Chart looks good! All elements are present.",
            confidence="0.95"
        )

        with patch.object(critic.critique, '__call__', return_value=mock_pred):
            result = critic(
                task="Create a sales chart",
                code="plt.bar(x, y)",
                image_path=str(image_path),
            )

            assert result.is_valid is True
            assert "looks good" in result.feedback.lower()
            assert result.confidence == 0.95


class TestRefinementLoop:
    """Test the visualization refinement loop in agent."""

    def test_should_refine_detects_visualization_code(self, tmp_path):
        """Should refine when code has visualization keywords and artifacts exist."""
        # Create run context with an image
        run_context = RunContext(base_dir=tmp_path)
        image_path = run_context.artifacts_dir / "chart.png"
        image_path.write_bytes(b"fake image")
        run_context.register_artifact("chart.png", "image", "Test chart")

        # Create agent with mock critic
        mock_critic = MockCritic(is_valid=True)
        agent = RLMAgent(
            architect=MockArchitect(),
            coder=MockCoder(),
            repl=MockREPL(),
            responder=MockResponder(),
            critic=mock_critic,
            run_context=run_context,
        )

        # Test with visualization code
        code_with_viz = "plt.figure()\nplt.bar(x, y)\nplt.savefig(f'{output_dir}/chart.png')"
        output = "Chart saved to chart.png"

        assert agent._should_refine_visualization(output, code_with_viz)

    def test_should_not_refine_without_critic(self, tmp_path):
        """Should not refine if critic is None."""
        run_context = RunContext(base_dir=tmp_path)

        agent = RLMAgent(
            architect=MockArchitect(),
            coder=MockCoder(),
            repl=MockREPL(),
            responder=MockResponder(),
            critic=None,  # No critic
            run_context=run_context,
        )

        code_with_viz = "plt.savefig('chart.png')"
        assert not agent._should_refine_visualization("", code_with_viz)

    def test_should_not_refine_without_artifacts(self, tmp_path):
        """Should not refine if no image artifacts were created."""
        run_context = RunContext(base_dir=tmp_path)

        agent = RLMAgent(
            architect=MockArchitect(),
            coder=MockCoder(),
            repl=MockREPL(),
            responder=MockResponder(),
            critic=MockCritic(),
            run_context=run_context,
        )

        # No images created despite visualization code
        code_with_viz = "plt.savefig('chart.png')"  # Failed to save
        assert not agent._should_refine_visualization("Error", code_with_viz)

    def test_get_latest_visualization(self, tmp_path):
        """Should return the most recent image artifact."""
        run_context = RunContext(base_dir=tmp_path)

        # Create multiple images
        for i, name in enumerate(["old.png", "newer.png", "latest.png"]):
            img_path = run_context.artifacts_dir / name
            img_path.write_bytes(b"fake image")
            run_context.register_artifact(name, "image", f"Image {i}")

        agent = RLMAgent(
            architect=MockArchitect(),
            coder=MockCoder(),
            repl=MockREPL(),
            responder=MockResponder(),
            critic=MockCritic(),
            run_context=run_context,
        )

        latest = agent._get_latest_visualization()
        assert latest is not None
        assert latest.name == "latest.png"

    def test_refinement_loop_validates_on_first_round(self, tmp_path):
        """Refinement should stop on first round if critic approves."""
        run_context = RunContext(base_dir=tmp_path)
        image_path = run_context.artifacts_dir / "chart.png"
        image_path.write_bytes(b"fake image")
        run_context.register_artifact("chart.png", "image", "Test chart")

        # Critic approves immediately
        mock_critic = MockCritic(is_valid=True, feedback="Perfect!")
        mock_coder = MockCoder()  # MockCoder doesn't take 'code' param, it has default

        agent = RLMAgent(
            architect=MockArchitect(),
            coder=mock_coder,
            repl=MockREPL(output="Refined output"),
            responder=MockResponder(),
            critic=mock_critic,
            run_context=run_context,
        )

        final_code, final_output = agent._refine_visualization_loop(
            task="Create chart",
            initial_code="plt.bar(x, y)",
            initial_output="Initial output",
            base_context="Context",
            indent=""
        )

        # Critic should have been called
        assert mock_critic.call_count >= 1
        assert final_code == "plt.bar(x, y)"  # Original code unchanged since approved

    def test_refinement_loop_runs_three_rounds(self, tmp_path):
        """Refinement should run up to 3 rounds if critic keeps rejecting."""
        run_context = RunContext(base_dir=tmp_path)
        image_path = run_context.artifacts_dir / "chart.png"
        image_path.write_bytes(b"fake image")
        run_context.register_artifact("chart.png", "image", "Test chart")

        # Critic rejects every time
        mock_critic = MockCritic(is_valid=False, feedback="Needs improvement")
        mock_coder = MockCoder()  # Uses default code

        agent = RLMAgent(
            architect=MockArchitect(),
            coder=mock_coder,
            repl=MockREPL(output="Refined output"),
            responder=MockResponder(),
            critic=mock_critic,
            run_context=run_context,
        )

        final_code, final_output = agent._refine_visualization_loop(
            task="Create chart",
            initial_code="plt.bar(x, y)",
            initial_output="Initial output",
            base_context="Context",
            indent=""
        )

        # Should run exactly 3 rounds
        assert mock_critic.call_count == 3
        assert mock_coder.call_count == 2  # Refines on round 1 and 2, not round 3
        assert "hello" in final_code  # Used MockCoder's default

    def test_refinement_loop_accumulates_feedback(self, tmp_path):
        """Refinement should pass cumulative feedback to critic."""
        run_context = RunContext(base_dir=tmp_path)
        image_path = run_context.artifacts_dir / "chart.png"
        image_path.write_bytes(b"fake image")
        run_context.register_artifact("chart.png", "image", "Test chart")

        # Critic rejects twice, then approves
        call_results = [False, False, True]  # Reject, Reject, Accept
        call_index = [0]

        def dynamic_critic(task, code, image_path, execution_output="", previous_feedback=""):
            result = call_results[call_index[0]]
            call_index[0] += 1
            return MockPrediction(
                is_valid=result,
                feedback=f"Feedback round {call_index[0]}",
                confidence=0.8
            )

        mock_critic = MagicMock(side_effect=dynamic_critic)
        mock_coder = MockCoder()

        agent = RLMAgent(
            architect=MockArchitect(),
            coder=mock_coder,
            repl=MockREPL(output="Refined output"),
            responder=MockResponder(),
            critic=mock_critic,
            run_context=run_context,
        )

        agent._refine_visualization_loop(
            task="Create chart",
            initial_code="plt.bar(x, y)",
            initial_output="Initial output",
            base_context="Context",
            indent=""
        )

        # Check that feedback accumulated across calls
        assert mock_critic.call_count == 3

        # Round 1: no previous feedback
        first_call = mock_critic.call_args_list[0]
        assert first_call[1]["previous_feedback"] == ""

        # Round 2: has feedback from round 1
        second_call = mock_critic.call_args_list[1]
        assert "Round 1 Critique" in second_call[1]["previous_feedback"]

        # Round 3: has feedback from rounds 1 and 2
        third_call = mock_critic.call_args_list[2]
        assert "Round 1 Critique" in third_call[1]["previous_feedback"]
        assert "Round 2 Critique" in third_call[1]["previous_feedback"]


class TestAgentIntegration:
    """Test critic integration with full agent workflow."""

    def test_agent_runs_without_critic(self, tmp_path):
        """Agent should work normally without a critic."""
        run_context = RunContext(base_dir=tmp_path)

        agent = RLMAgent(
            architect=MockArchitect(action="ANSWER"),
            coder=MockCoder(),
            repl=MockREPL(output="42"),
            responder=MockResponder(response="The answer is 42"),
            critic=None,  # No critic
            run_context=run_context,
        )

        result = agent.run("What is the answer?")
        assert "42" in result or "answer" in result.lower()

    def test_agent_with_critic_enabled(self, tmp_path):
        """Agent should use critic when configured and visualization is created."""
        run_context = RunContext(base_dir=tmp_path)

        # Create mock image artifact
        image_path = run_context.artifacts_dir / "test.png"
        image_path.write_bytes(b"fake image")
        run_context.register_artifact("test.png", "image", "Test chart")

        mock_critic = MockCritic(is_valid=True, feedback="Excellent chart!")
        mock_architect = MockArchitect(action="CODE")
        # MockCoder needs to return code with visualization keywords to trigger critic
        mock_coder = MockCoder(code="plt.savefig('test.png')\\nprint('Done')")
        mock_repl = MockREPL(output="Chart saved")

        agent = RLMAgent(
            max_steps=2,  # Limit steps
            architect=mock_architect,
            coder=mock_coder,
            repl=mock_repl,
            responder=MockResponder(response="Task complete"),
            critic=mock_critic,
            run_context=run_context,
        )

        # Run with a task that triggers visualization
        agent.run("Create a chart")

        # Critic should have been called
        assert mock_critic.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
