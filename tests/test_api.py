from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app, get_database, get_orchestrator


def test_api_shortens_redirects_and_reports_stats(tmp_path):
    get_settings.cache_clear()
    get_database.cache_clear()
    get_orchestrator.cache_clear()
    app.dependency_overrides = {}

    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'api.db'}"
    settings.audit_log_path = str(tmp_path / "audit.log")
    settings.base_url = "http://testserver"

    client = TestClient(app)

    response = client.post("/shorten", json={"url": "https://example.com", "custom_slug": "abc"})
    assert response.status_code == 201
    assert response.json()["short_url"] == "http://testserver/abc"

    redirect = client.get("/abc", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://example.com/"

    stats = client.get("/stats/abc")
    assert stats.status_code == 200
    assert stats.json()["clicks"] == 1


def test_orchestrator_approval_flow(tmp_path):
    get_settings.cache_clear()
    get_database.cache_clear()
    get_orchestrator.cache_clear()
    settings = get_settings()
    settings.database_url = f"sqlite:///{tmp_path / 'workflow.db'}"
    settings.audit_log_path = str(tmp_path / "audit.log")
    settings.require_human_approval = True

    client = TestClient(app)
    started = client.post("/agent/scenarios/greenfield/run", json={"auto_approve": False})
    assert started.status_code == 200
    body = started.json()
    assert body["status"] == "waiting_for_approval"

    run_id = body["run_id"]
    approved = client.post(
        f"/agent/runs/{run_id}/approve/release",
        json={"approved": True, "approver": "qa", "comment": "ready"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"

