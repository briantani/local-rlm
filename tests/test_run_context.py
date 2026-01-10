"""
Tests for RunContext artifact management.

Tests the artifact folder creation, file registration, and report generation.
"""

import threading
import time
from pathlib import Path

import pytest

from src.core.run_context import RunContext


class TestRunContext:
    """Unit tests for RunContext."""

    @pytest.fixture
    def temp_runs_dir(self, tmp_path: Path) -> Path:
        """Create a temporary runs directory."""
        runs_dir = tmp_path / "runs"
        runs_dir.mkdir()
        return runs_dir

    @pytest.fixture
    def run_context(self, temp_runs_dir: Path) -> RunContext:
        """Create a RunContext with a temporary base directory."""
        return RunContext(base_dir=temp_runs_dir)

    def test_creates_artifacts_folder(self, run_context: RunContext):
        """Test that artifacts folder is created on initialization."""
        assert run_context.artifacts_dir.exists()
        assert run_context.artifacts_dir.is_dir()

    def test_unique_run_ids(self, temp_runs_dir: Path):
        """Test that each RunContext gets a unique run_id (with delay)."""
        ctx1 = RunContext(base_dir=temp_runs_dir)
        time.sleep(1.1)  # Wait for timestamp to change
        ctx2 = RunContext(base_dir=temp_runs_dir)
        assert ctx1.run_id != ctx2.run_id
        assert ctx1.artifacts_dir != ctx2.artifacts_dir

    def test_custom_run_id(self, temp_runs_dir: Path):
        """Test that custom run_id can be provided."""
        ctx = RunContext(base_dir=temp_runs_dir, run_id="my-custom-run")
        assert ctx.run_id == "my-custom-run"
        assert "my-custom-run" in str(ctx.artifacts_dir)

    def test_get_artifact_path(self, run_context: RunContext):
        """Test that artifact paths are generated correctly."""
        path = run_context.get_artifact_path("output.png")
        assert path.parent == run_context.artifacts_dir
        assert path.name == "output.png"

    def test_get_artifact_path_with_subdir(self, run_context: RunContext):
        """Test artifact paths with subdirectories."""
        path = run_context.get_artifact_path("charts/monthly.png")
        assert "charts" in str(path)
        assert path.name == "monthly.png"

    def test_register_artifact(self, run_context: RunContext):
        """Test registering an artifact."""
        # Create a test file
        test_file = run_context.get_artifact_path("test.txt")
        test_file.write_text("Hello, World!")

        run_context.register_artifact(
            filename="test.txt",
            artifact_type="text",
            description="Test file"
        )

        assert len(run_context.artifacts) == 1
        assert run_context.artifacts[0]["filename"] == "test.txt"
        assert run_context.artifacts[0]["type"] == "text"
        assert run_context.artifacts[0]["description"] == "Test file"

    def test_list_images(self, run_context: RunContext):
        """Test listing only image artifacts."""
        # Register mixed artifacts
        run_context.register_artifact("plot.png", "image", "A plot")
        run_context.register_artifact("data.csv", "data", "CSV data")
        run_context.register_artifact("chart.jpg", "image", "A chart")

        images = run_context.list_images()
        assert len(images) == 2
        assert all(img["type"] == "image" for img in images)

    def test_add_to_report(self, run_context: RunContext):
        """Test building report content."""
        run_context.add_to_report("# My Report")
        run_context.add_to_report("This is the content.")

        content = run_context.get_report()
        assert "# My Report" in content
        assert "This is the content." in content

    def test_add_image_to_report(self, run_context: RunContext):
        """Test adding images to report."""
        run_context.add_image_to_report("chart.png", "Sales Chart")

        content = run_context.get_report()
        assert "![Sales Chart](chart.png)" in content

    def test_save_report(self, run_context: RunContext):
        """Test saving report to file."""
        run_context.add_to_report("# Test Report")
        run_context.add_to_report("Some content.")
        run_context.save_report()

        report_path = run_context.artifacts_dir / "report.md"
        assert report_path.exists()
        assert "# Test Report" in report_path.read_text()

    def test_save_report_custom_filename(self, run_context: RunContext):
        """Test saving report with custom filename."""
        run_context.add_to_report("Custom content")
        run_context.save_report(filename="custom_report.md")

        report_path = run_context.artifacts_dir / "custom_report.md"
        assert report_path.exists()

    def test_get_working_directory(self, run_context: RunContext):
        """Test that working directory returns absolute path string."""
        wd = run_context.get_working_directory()
        assert isinstance(wd, str)
        assert Path(wd).is_absolute()
        assert wd == str(run_context.artifacts_dir.absolute())

    def test_thread_safety_of_artifact_registration(self, run_context: RunContext):
        """Test that artifact registration is thread-safe."""
        def register_artifact(name: str):
            run_context.register_artifact(f"file_{name}.txt", "text", f"File {name}")

        threads = [
            threading.Thread(target=register_artifact, args=(str(i),))
            for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(run_context.artifacts) == 10

    def test_empty_report_saved(self, run_context: RunContext):
        """Test that empty reports create empty files."""
        run_context.save_report()
        report_path = run_context.artifacts_dir / "report.md"
        assert report_path.exists()
        assert report_path.read_text() == ""

    def test_cleanup(self, temp_runs_dir: Path):
        """Test cleanup removes artifacts directory."""
        ctx = RunContext(base_dir=temp_runs_dir, run_id="cleanup-test")
        test_file = ctx.get_artifact_path("test.txt")
        test_file.write_text("test")
        ctx.register_artifact("test.txt", "text", "Test")

        assert ctx.artifacts_dir.exists()
        ctx.cleanup()

        assert not ctx.artifacts_dir.exists()
        assert len(ctx.artifacts) == 0


class TestRunContextIntegration:
    """Integration tests for RunContext with file system."""

    def test_real_file_creation(self, tmp_path: Path):
        """Test creating real files in artifact folder."""
        ctx = RunContext(base_dir=tmp_path)

        # Simulate code execution creating a file
        output_path = ctx.get_artifact_path("output.txt")
        output_path.write_text("Generated output")

        ctx.register_artifact("output.txt", "text", "Code output")

        # Verify file exists and is tracked
        assert output_path.exists()
        assert len(ctx.artifacts) == 1

    def test_image_file_registration(self, tmp_path: Path):
        """Test image file registration for visualization."""
        ctx = RunContext(base_dir=tmp_path)

        # Create a fake image file (just bytes)
        img_path = ctx.get_artifact_path("chart.png")
        img_path.write_bytes(b"fake png data")

        ctx.register_artifact("chart.png", "image", "Sales chart visualization")

        images = ctx.list_images()
        assert len(images) == 1
        assert images[0]["filename"] == "chart.png"

    def test_nested_directory_creation(self, tmp_path: Path):
        """Test that nested directories are created for artifacts."""
        ctx = RunContext(base_dir=tmp_path)

        nested_path = ctx.get_artifact_path("reports/2024/january.md")
        nested_path.parent.mkdir(parents=True, exist_ok=True)
        nested_path.write_text("January report")

        assert nested_path.exists()
        assert "reports" in str(nested_path)
