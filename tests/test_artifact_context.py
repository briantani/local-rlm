import shutil
from src.core.run_context import RunContext
from src.modules.responder import Responder


def test_register_artifact_stores_context(tmp_path):
    rc = RunContext(run_id="t1", base_dir=tmp_path)
    path = rc.register_artifact(
        "fig1.png",
        artifact_type="image",
        description="Test figure",
        prompt="Generate a scatter plot of X vs Y",
        section="Results",
        rationale="Show correlation between X and Y",
    )

    assert path.exists() is False or isinstance(path, type(rc.artifacts[0]["path"]))
    assert any(a["filename"] == "fig1.png" for a in rc.artifacts)
    a = next(a for a in rc.artifacts if a["filename"] == "fig1.png")
    assert a["prompt"] == "Generate a scatter plot of X vs Y"
    assert a["section"] == "Results"
    assert a["rationale"] == "Show correlation between X and Y"


def test_responder_uses_artifact_context(tmp_path):
    rc = RunContext(run_id="t2", base_dir=tmp_path)
    (rc.artifacts_dir / "fig2.png").write_bytes(b"img")
    rc.register_artifact(
        "fig2.png",
        artifact_type="image",
        description="Figure 2",
        prompt="Plot bar chart",
        section="Discussion",
        rationale="Highlight main trend",
    )

    responder = Responder(run_context=rc)
    base_response = "Here is the analysis."
    enhanced = responder._enhance_with_artifacts(base_response)

    assert "Generated Visualizations" in enhanced
    assert "Figure 2" in enhanced
    assert "Section: Discussion" in enhanced
    assert "Rationale:" in enhanced
    assert "Prompt:" in enhanced

    shutil.rmtree(rc.artifacts_dir)
