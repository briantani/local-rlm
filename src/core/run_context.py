"""
RunContext manages artifacts (images, reports, files) for a single agent run.

Each run gets a unique folder under `runs/` with a timestamped ID.
This allows the web interface and CLI to access generated artifacts.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


# Compute project root once at module load time (before any chdir)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()


class RunContext:
    """Context for a single agent run, managing artifacts and metadata.

    Attributes:
        run_id: Unique identifier for this run (timestamp-based)
        artifacts_dir: Path to the folder storing all artifacts for this run
        artifacts: List of artifact metadata (path, type, description)
    """

    # Base directory for all runs - MUST be absolute to avoid issues with os.chdir()
    # in REPL execution (threads share cwd, causing nested runs/ folders)
    RUNS_BASE_DIR = _PROJECT_ROOT / "runs"

    def __init__(self, run_id: str | None = None, base_dir: Path | None = None):
        """Initialize a new run context.

        Args:
            run_id: Optional custom run ID. If not provided, generates timestamp-based ID.
            base_dir: Optional custom base directory for runs. Defaults to project's runs/ folder.
        """
        self.run_id = run_id or self._generate_run_id()
        # Ensure base_dir is absolute to prevent nested folder issues
        self._base_dir = (base_dir.absolute() if base_dir else self.RUNS_BASE_DIR)
        self.artifacts_dir = self._base_dir / self.run_id
        self.artifacts: list[dict[str, Any]] = []
        self._report_content: list[str] = []

        # Create the artifacts directory
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _generate_run_id() -> str:
        """Generate a unique run ID based on timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def get_artifact_path(self, filename: str) -> Path:
        """Get the full path for an artifact file.

        Args:
            filename: Name of the artifact file (e.g., 'chart.png')

        Returns:
            Full path to the artifact within this run's folder
        """
        return self.artifacts_dir / filename

    def register_artifact(
        self,
        filename: str,
        artifact_type: str = "file",
        description: str = "",
        *,
        prompt: str | None = None,
        section: str | None = None,
        rationale: str | None = None,
    ) -> Path:
        """Register a new artifact and return its path.

        Args:
            filename: Name of the artifact file
            artifact_type: Type of artifact ('image', 'report', 'data', 'file')
            description: Human-readable description of the artifact

            prompt: Optional prompt or instruction that generated this artifact
            section: Optional intended report section for the artifact
            rationale: Optional rationale or notes about why the artifact was created

        Returns:
            Full path where the artifact should be saved
        """
        path = self.get_artifact_path(filename)
        self.artifacts.append({
            "filename": filename,
            "path": str(path),
            "type": artifact_type,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "prompt": prompt,
            "section": section,
            "rationale": rationale,
        })
        return path

    def add_to_report(self, content: str) -> None:
        """Add content to the final report.

        Args:
            content: Markdown content to append to the report
        """
        self._report_content.append(content)

    def add_image_to_report(self, filename: str, caption: str = "") -> None:
        """Add an image reference to the report.

        Args:
            filename: Name of the image file (must be registered as artifact)
            caption: Optional caption for the image
        """
        # Use relative path for markdown
        img_markdown = f"![{caption or filename}]({filename})"
        if caption:
            img_markdown += f"\n*{caption}*"
        self._report_content.append(img_markdown)

    def get_report(self) -> str:
        """Get the full report content as markdown.

        Returns:
            Complete markdown report with all added content
        """
        return "\n\n".join(self._report_content)

    def save_report(self, filename: str = "report.md") -> Path:
        """Save the report to a markdown file.

        Args:
            filename: Name of the report file

        Returns:
            Path to the saved report
        """
        report_path = self.register_artifact(filename, "report", "Final run report")
        report_path.write_text(self.get_report())
        return report_path

    def list_images(self) -> list[dict[str, Any]]:
        """List all image artifacts.

        Returns:
            List of image artifact metadata
        """
        return [a for a in self.artifacts if a["type"] == "image"]

    def cleanup(self) -> None:
        """Remove the artifacts directory and all contents.

        Use with caution - this permanently deletes all artifacts for this run.
        """
        if self.artifacts_dir.exists():
            shutil.rmtree(self.artifacts_dir)
            self.artifacts.clear()
            self._report_content.clear()

    def get_working_directory(self) -> str:
        """Get the working directory path as a string for code execution.

        Returns:
            Absolute path to the artifacts directory
        """
        return str(self.artifacts_dir.absolute())

    def __repr__(self) -> str:
        return f"RunContext(run_id='{self.run_id}', artifacts={len(self.artifacts)})"
