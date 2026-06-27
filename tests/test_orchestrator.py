from app.audit import AuditLogger
from app.llm import LlmClient
from app.orchestrator import SdlcOrchestrator


def test_ambiguous_scenario_has_clarification_approval(tmp_path):
    orchestrator = SdlcOrchestrator(
        AuditLogger(str(tmp_path / "audit.log")),
        LlmClient(None, "test-model"),
        require_human_approval=True,
    )

    run = orchestrator.start("ambiguous", auto_approve=False)
    assert run["status"] == "waiting_for_approval"
    assert run["context"]["node_status"]["clarification"] == "waiting_for_approval"

    approved = orchestrator.approve(run["run_id"], "clarification", True, "product-owner", "scope accepted")
    assert approved["status"] == "waiting_for_approval"
    assert approved["context"]["node_status"]["release"] == "waiting_for_approval"


def test_auto_approved_brownfield_completes_with_metrics(tmp_path):
    orchestrator = SdlcOrchestrator(
        AuditLogger(str(tmp_path / "audit.log")),
        LlmClient(None, "test-model"),
        require_human_approval=True,
    )

    run = orchestrator.start("brownfield", auto_approve=True)
    metrics = run["context"]["metrics"]
    assert run["status"] == "completed"
    assert run["context"]["node_status"]["impact_analysis"] == "passed"
    assert metrics["success_rate"] == 1.0
    assert metrics["end_to_end_latency_seconds"] >= 0

