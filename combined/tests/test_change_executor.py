from app.change_executor import ChangeExecutor


def test_change_executor_applies_expiry_feature_and_runs_tests(tmp_path):
    executor = ChangeExecutor(tmp_path / "change_runs")

    result = executor.execute(
        "Enhance the existing URL shortener with expiry dates so expired links stop redirecting.",
        auto_approve=True,
    )

    assert result["status"] == "completed"
    assert result["classification"] == "brownfield"
    assert result["selected_template"] == "link_expiry"
    assert result["patch"]["applied"] is True
    assert "ExpiredLinkError" in result["patch"]["diff"]
    assert result["validation"]["passed"] is True
    assert "passed" in result["validation"]["stdout"]


def test_change_executor_waits_for_approval_before_code_patch(tmp_path):
    executor = ChangeExecutor(tmp_path / "change_runs")

    result = executor.execute("Add expiry support to short links.", auto_approve=False)

    assert result["status"] == "waiting_for_approval"
    assert result["approval"]["required"] is True
    assert result["patch"]["applied"] is False
    assert result["validation"]["command"] == "not run"
