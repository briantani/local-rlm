import shutil
from src.core.run_context import RunContext


def test_finalize_report_appends_missing_artifacts(tmp_path):
    rc = RunContext(run_id="fa1", base_dir=tmp_path)
    # Create two artifacts; only one is referenced in the report
    (rc.artifacts_dir / "a1.png").write_bytes(b"x")
    rc.register_artifact("a1.png", artifact_type="image", description="A1", section="Results", rationale="Show A1", prompt="plot a1")
    (rc.artifacts_dir / "a2.csv").write_text("c1,c2\n1,2\n")
    rc.register_artifact("a2.csv", artifact_type="data", description="A2", section="Data", rationale="Provide data", prompt="export a2")

    # Current report only references a1
    rc.add_to_report("We present A1 here: ![A1](a1.png)")

    res = rc.finalize_report()
    assert "a2.csv" in res["added"]

    report = rc.get_report()
    assert "a2.csv" in report
    assert "Artifacts Summary" in report

    shutil.rmtree(rc.artifacts_dir)
