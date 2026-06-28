from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app, get_database, get_engineering_service


def reset_app(tmp_path):
    get_settings.cache_clear()
    get_database.cache_clear()
    get_engineering_service.cache_clear()
    settings = get_settings()
    settings.database_path = str(tmp_path / "api.db")
    settings.public_base_url = "http://testserver/r"
    settings.require_engineer_signoff = True
    return TestClient(app)


def test_api_create_redirect_and_stats(tmp_path):
    client = reset_app(tmp_path)

    created = client.post(
        "/api/links",
        json={"target_url": "https://example.com", "custom_endpoint": "demo", "max_clicks": 2},
    )
    assert created.status_code == 201
    assert created.json()["short_url"] == "http://testserver/r/demo"

    redirect = client.get("/r/demo", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://example.com/"

    stats = client.get("/api/links/demo/stats")
    assert stats.status_code == 200
    assert stats.json()["clicks"] == 1


def test_reserved_endpoint_validation(tmp_path):
    client = reset_app(tmp_path)

    response = client.post("/api/links", json={"target_url": "https://example.com", "custom_endpoint": "api"})

    assert response.status_code == 422


def test_engineering_evidence_requires_signoff(tmp_path):
    client = reset_app(tmp_path)

    response = client.post(
        "/engineering/execute",
        json={
            "scenario": "ambiguous",
            "requirement": "Make links smarter and safer for advisors.",
            "engineer_signoff": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "waiting_for_engineer_signoff"
    assert body["ambiguity_notes"]
    assert body["quality_gates"][-1]["status"] == "waiting"


def test_engineering_summary_download(tmp_path):
    client = reset_app(tmp_path)
    created = client.post(
        "/engineering/execute",
        json={
            "scenario": "brownfield",
            "requirement": "Enhance existing links with expiry controls and tests.",
            "engineer_signoff": True,
        },
    ).json()

    summary = client.get(f"/engineering/runs/{created['run_id']}/summary.md")

    assert summary.status_code == 200
    assert "Engineering Summary" in summary.text
    assert "Quality Gates" in summary.text
