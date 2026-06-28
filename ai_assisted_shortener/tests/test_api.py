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
    settings.openai_enabled = False
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
            "requirement": "Make links smarter and safer for users.",
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


def test_engineering_business_approval_role_is_recorded(tmp_path):
    client = reset_app(tmp_path)

    response = client.post(
        "/engineering/execute",
        json={
            "scenario": "greenfield",
            "requirement": "Build a URL shortener service from scratch with analytics and docs.",
            "engineer_signoff": True,
            "approval_role": "Business",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "reviewable_outcome_ready"
    assert body["approval_role"] == "Business"
    assert body["compliance_matrix"]
    assert body["task_decomposition"][0]["intent"]
    assert body["task_decomposition"][0]["acceptance_criteria"]
    phases = {item["execution_phase"] for item in body["ai_assisted_execution"]}
    assert {
        "requirement_analysis",
        "implementation",
        "debugging",
        "refactoring",
        "test_generation",
        "documentation_and_review_preparation",
    }.issubset(phases)
    first_ai_step = body["ai_assisted_execution"][0]
    assert first_ai_step["constraints"]
    assert first_ai_step["acceptance_criteria"]
    assert first_ai_step["technical_context"]
    assert first_ai_step["generated_output"]
    assert first_ai_step["quality_signal"]


def test_out_of_scope_qr_requirement_requires_scope_review(tmp_path):
    client = reset_app(tmp_path)

    response = client.post(
        "/engineering/execute",
        json={
            "scenario": "brownfield",
            "requirement": "Generate QR codes for every shortened link.",
            "engineer_signoff": True,
            "approval_role": "Engineer",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scope_review_required"
    assert body["scope_assessment"]["status"] == "scope_review_required"
    assert body["task_decomposition"][0]["id"] == "SCOPE-1"
    assert body["ai_assisted_execution"][0]["engineer_action"] == "rejected_for_now"

def test_facebook_clone_requirement_captures_intent_and_requires_scope_review(tmp_path):
    client = reset_app(tmp_path)

    response = client.post(
        "/engineering/execute",
        json={
            "scenario": "greenfield",
            "requirement": "Build Facebook clone",
            "engineer_signoff": True,
            "approval_role": "Engineer",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scope_review_required"
    assert body["scope_assessment"]["status"] == "scope_review_required"
    assert body["scope_assessment"]["captured_intent"] == "Build a Facebook-like social networking product"
    assert "facebook" in body["scope_assessment"]["matched_terms"]
    assert "FastAPI URL shortener" not in body["normalized_problem"]
    assert body["task_decomposition"][0]["id"] == "SCOPE-1"
    assert body["task_decomposition"][0]["intent"] == "Protect engineering scope and prevent unsupported implementation."
    assert body["task_decomposition"][0]["acceptance_criteria"]
    assert "Facebook-like social networking product" in body["ai_assisted_execution"][:1][0]["ai_suggestion"]

def test_requirement_without_url_shortener_intent_requires_scope_review(tmp_path):
    client = reset_app(tmp_path)

    response = client.post(
        "/engineering/execute",
        json={
            "scenario": "greenfield",
            "requirement": "build spotify",
            "engineer_signoff": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scope_review_required"
    assert body["scope_assessment"]["captured_intent"] == "Build a Spotify-like music streaming product"
    assert body["scope_assessment"]["matched_terms"] == ["spotify"]
    assert "FastAPI URL shortener" not in body["normalized_problem"]


def test_unknown_product_requirement_without_shortener_terms_is_not_forced_into_scope(tmp_path):
    client = reset_app(tmp_path)

    response = client.post(
        "/engineering/execute",
        json={
            "scenario": "greenfield",
            "requirement": "create insurance quote engine",
            "engineer_signoff": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scope_review_required"
    assert body["scope_assessment"]["matched_terms"] == ["no_url_shortener_intent_detected"]
    assert body["scope_assessment"]["captured_intent"] == "Create insurance quote engine product or capability"
    assert "FastAPI URL shortener" not in body["normalized_problem"]

def test_implementation_requires_engineer_signoff(tmp_path):
    client = reset_app(tmp_path)

    response = client.post(
        "/implementation/execute",
        json={"requirement": "remove Expiry in UI", "engineer_signoff": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "waiting_for_engineer_signoff"
    assert body["security_review"]["status"] == "waiting_for_engineer_signoff"
    assert body["workspace_path"]


def test_remove_expiry_ui_generates_isolated_implementation_package(tmp_path):
    client = reset_app(tmp_path)

    response = client.post(
        "/implementation/execute",
        json={"requirement": "remove Expiry in UI", "engineer_signoff": True, "approval_role": "Engineer"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "implementation_package_ready"
    assert body["security_review"]["status"] == "passed"
    assert "app/static/index.html" in body["files_changed"]
    assert "app/static/app.js" in body["files_changed"]
    assert body["tasks"][0]["id"] == "SEC-1"
    generated_index = body["workspace_path"] + "/app/static/index.html"
    generated_js = body["workspace_path"] + "/app/static/app.js"
    with open(generated_index, encoding="utf-8") as file:
        assert "Expiry" not in file.read()
    with open(generated_js, encoding="utf-8") as file:
        js = file.read()
    assert 'byId("expiresAt")' not in js
    assert "expires_at: null" in js

    preview = client.get(f"/implementation/runs/{body['run_id']}/preview")
    assert preview.status_code == 200
    assert "Expiry" not in preview.text
    assert f"/implementation/runs/{body['run_id']}/preview/static/app.js" in preview.text

    generated_app_js = client.get(f"/implementation/runs/{body['run_id']}/preview/static/app.js")
    assert generated_app_js.status_code == 200
    assert 'byId("expiresAt")' not in generated_app_js.text

def test_remove_max_clicks_ui_generates_preview_without_max_clicks(tmp_path):
    client = reset_app(tmp_path)

    response = client.post(
        "/implementation/execute",
        json={"requirement": "Remove Max Clicks from UI", "engineer_signoff": True, "approval_role": "Engineer"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "implementation_package_ready"
    assert "app/static/index.html" in body["files_changed"]
    assert "app/static/app.js" in body["files_changed"]

    preview = client.get(f"/implementation/runs/{body['run_id']}/preview")
    assert preview.status_code == 200
    assert "Max clicks" not in preview.text

    generated_app_js = client.get(f"/implementation/runs/{body['run_id']}/preview/static/app.js")
    assert generated_app_js.status_code == 200
    assert 'byId("maxClicks")' not in generated_app_js.text
    assert "max_clicks: null" in generated_app_js.text

def _execute(client, requirement, scenario="greenfield", signoff=True):
    return client.post(
        "/engineering/execute",
        json={"scenario": scenario, "requirement": requirement, "engineer_signoff": signoff},
    ).json()


def test_requirement_understanding_is_derived_from_input(tmp_path):
    client = reset_app(tmp_path)
    a = _execute(client, "Build a URL shortener with custom endpoints and analytics")
    b = _execute(client, "Add expiry and a max-click limit to existing short links")
    assert a["normalized_problem"] != b["normalized_problem"]
    assert a["requirement_understanding"]["source"] == "local_heuristic"
    assert "custom endpoint" in a["normalized_problem"]
    assert "analytics" in a["normalized_problem"]
    assert "expiry" in b["normalized_problem"]
    assert "max-click limit" in b["normalized_problem"]


def test_vague_requirement_flags_ambiguity_even_for_greenfield(tmp_path):
    client = reset_app(tmp_path)
    vague = _execute(client, "make link stuff better for the team somehow")
    precise = _execute(client, "Build a URL shortener with custom endpoints and analytics")
    vague_text = " ".join(vague["ambiguity_notes"]).lower()
    assert vague["ambiguity_notes"]
    assert "better" in vague_text
    assert "somehow" in vague_text
    assert precise["ambiguity_notes"] == []


def test_understanding_feeds_ai_traceability(tmp_path):
    client = reset_app(tmp_path)
    body = _execute(client, "Build a URL shortener with analytics and expiry")
    analysis = body["ai_assisted_execution"][0]
    assert analysis["execution_phase"] == "requirement_analysis"
    assert analysis["understanding_source"] == "local_heuristic"
    assert body["normalized_problem"] in analysis["ai_suggestion"]


def _task_ids(body):
    return [t["id"] for t in body["task_decomposition"]]


def test_task_decomposition_is_requirement_specific(tmp_path):
    client = reset_app(tmp_path)
    only_maxclick = _execute(client, "Just add a max-click limit to existing links, nothing else")
    analytics_custom = _execute(client, "Add analytics and custom endpoints to the shortener")
    a_ids = _task_ids(only_maxclick)
    b_ids = _task_ids(analytics_custom)
    assert a_ids != b_ids
    assert "T-MAXCLICK" in a_ids
    assert "T-STATS" not in a_ids
    assert "T-CUSTOM" not in a_ids
    assert "T-STATS" in b_ids
    assert "T-CUSTOM" in b_ids
    assert "T-MAXCLICK" not in b_ids


def test_task_decomposition_has_dependencies_and_sequencing(tmp_path):
    client = reset_app(tmp_path)
    body = _execute(client, "Add expiry and a max-click limit to existing short links")
    tasks = {t["id"]: t for t in body["task_decomposition"]}
    assert tasks["T-DATA"]["depends_on"] == ["T-REQ"]
    assert tasks["T-EXPIRY"]["depends_on"] == ["T-DATA"]
    assert "T-EXPIRY" in tasks["T-TEST"]["depends_on"]
    assert "T-MAXCLICK" in tasks["T-TEST"]["depends_on"]
    assert tasks["T-DOC"]["depends_on"] == ["T-TEST"]
    seen = set()
    for task in body["task_decomposition"]:
        assert all(dep in seen for dep in task["depends_on"])
        seen.add(task["id"])


def test_vague_in_scope_requirement_decomposes_to_clarify_first(tmp_path):
    client = reset_app(tmp_path)
    body = _execute(client, "make our links better somehow")
    ids = _task_ids(body)
    assert "T-SCOPE" in ids
    assert "T-CREATE" not in ids


def _brownfield(client, requirement):
    return client.post(
        "/engineering/execute",
        json={"scenario": "brownfield", "requirement": requirement, "engineer_signoff": True, "approval_role": "Engineer"},
    ).json()


def test_codebase_reasoning_is_requirement_specific(tmp_path):
    client = reset_app(tmp_path)
    vanity = _brownfield(client, "Add custom vanity endpoints for campaign links")
    analytics = _brownfield(client, "Add click analytics and a stats endpoint")
    vanity_cr = vanity["codebase_reasoning"]
    analytics_cr = analytics["codebase_reasoning"]
    assert vanity_cr["impacted_components"] != analytics_cr["impacted_components"]
    vanity_caps = {item["capability"] for item in vanity_cr["impact_analysis"]}
    assert "custom endpoint" in vanity_caps
    assert any("schemas.py" in f for f in vanity_cr["impacted_components"])
    assert "max_clicks" not in vanity_cr["data_flow"]
    assert "expires_at" not in vanity_cr["data_flow"]
    assert any("click_events" in f for f in analytics_cr["impacted_components"])
    assert any("stats" in f for f in analytics_cr["impacted_components"])


def test_codebase_reasoning_reports_api_and_regression_risk(tmp_path):
    client = reset_app(tmp_path)
    body = _brownfield(client, "Add a disable/kill-switch endpoint for abusive links")
    analysis = body["codebase_reasoning"]["impact_analysis"]
    disable = next(item for item in analysis if item["capability"] == "disable / kill switch")
    assert disable["api"] == "POST /api/links/{code}/disable"
    assert disable["regression_risk"]
    assert disable["files"]


def _gates(body):
    return {g["name"]: g for g in body["quality_gates"]}


def test_quality_gates_actually_run(tmp_path):
    client = reset_app(tmp_path)
    body = _execute(client, "Add expiry to links")
    gates = _gates(body)
    assert gates["runtime_tests"]["status"] == "passed"
    assert "duration_ms" in gates["runtime_tests"]
    assert gates["static_analysis"]["status"] in {"passed", "skipped", "failed"}
    assert gates["security_review"]["status"] == "passed"


def test_security_gate_blocks_sensitive_requirement(tmp_path):
    client = reset_app(tmp_path)
    body = _execute(client, "Log the api key and token for each shortened link")
    gates = _gates(body)
    assert gates["security_review"]["status"] == "blocked"


def test_sdlc_phases_are_requirement_specific(tmp_path):
    client = reset_app(tmp_path)
    a = _execute(client, "Add expiry to links")
    b = _execute(client, "Add custom vanity endpoints")

    def phase(body, name):
        return next(p for p in body["ai_assisted_execution"] if p["execution_phase"] == name)

    assert phase(a, "implementation")["ai_suggestion"] != phase(b, "implementation")["ai_suggestion"]
    assert "expiry" in phase(a, "implementation")["ai_suggestion"].lower()
    assert "custom endpoint" in phase(b, "implementation")["ai_suggestion"].lower()
    assert phase(a, "debugging")["ai_suggestion"] != phase(b, "debugging")["ai_suggestion"]


def test_generated_package_is_validated(tmp_path):
    client = reset_app(tmp_path)
    response = client.post(
        "/implementation/execute",
        json={"requirement": "remove Expiry in UI", "engineer_signoff": True, "approval_role": "Engineer"},
    )
    body = response.json()
    assert body["status"] == "implementation_package_ready"
    assert body["validation"]["status"] == "passed"
    assert any(c["check"] == "Expiry control removed from UI" and c["passed"] for c in body["validation"]["checks"])
    assert body["validation"]["attempts"]


def test_generated_output_includes_code_tests_and_docs(tmp_path):
    client = reset_app(tmp_path)
    response = client.post(
        "/implementation/execute",
        json={"requirement": "Add expiry and a max-click limit to links", "engineer_signoff": True, "approval_role": "Engineer"},
    )
    body = response.json()
    validation = body["validation"]
    artifacts = validation["generated_artifacts"]
    assert any(a.endswith("expiry_rule.py") for a in artifacts)
    assert any(a.endswith("click_limit_rule.py") for a in artifacts)
    assert any("test_" in a and a.endswith(".py") for a in artifacts)
    assert any(a.endswith("GENERATED_OUTPUT.md") for a in artifacts)
    assert validation["generated_tests"]["status"] in {"passed", "skipped"}


def test_risks_and_tradeoffs_are_requirement_specific(tmp_path):
    client = reset_app(tmp_path)
    expiry = _brownfield(client, "Add expiry to links")
    disable = _brownfield(client, "Add a disable kill switch for abusive links")
    expiry_risks = " ".join(r["risk"] for r in expiry["risks"]).lower()
    disable_risks = " ".join(r["risk"] for r in disable["risks"]).lower()
    assert expiry["risks"] != disable["risks"]
    assert "timezone" in expiry_risks
    assert "timezone" not in disable_risks
    assert "idempotent" in disable_risks
    assert expiry["engineer_decisions"]
    assert all(r["mitigation"] for r in expiry["risks"])


def test_engineer_notes_steer_execution(tmp_path):
    client = reset_app(tmp_path)
    response = client.post(
        "/engineering/execute",
        json={
            "scenario": "brownfield",
            "requirement": "Add expiry to links",
            "engineer_notes": "also add a stats endpoint for analytics",
            "engineer_signoff": True,
            "approval_role": "Engineer",
        },
    )
    body = response.json()
    capabilities = {i["capability"] for i in body["codebase_reasoning"]["impact_analysis"]}
    assert "analytics" in capabilities
    assert "T-STATS" in [t["id"] for t in body["task_decomposition"]]
    assert "inflating" in " ".join(r["risk"] for r in body["risks"]).lower()


def test_engineer_can_override_ai_step_actions(tmp_path):
    client = reset_app(tmp_path)
    response = client.post(
        "/engineering/execute",
        json={
            "scenario": "brownfield",
            "requirement": "Add expiry to links",
            "engineer_signoff": True,
            "approval_role": "Engineer",
            "engineer_actions": {"refactoring": "rejected", "documentation_and_review_preparation": "accepted"},
        },
    )
    body = response.json()
    phases = {p["execution_phase"]: p["engineer_action"] for p in body["ai_assisted_execution"]}
    assert phases["refactoring"] == "rejected"
    trace = {t["task"]: t["engineer_action"] for t in body["traceability"]}
    assert trace["AI-REFACTOR"] == "rejected"
    assert body["engineer_overrides"]["refactoring"] == "rejected"


def test_final_summary_includes_all_required_sections(tmp_path):
    client = reset_app(tmp_path)
    created = client.post(
        "/engineering/execute",
        json={"scenario": "brownfield", "requirement": "Add expiry and analytics to links", "engineer_signoff": True, "approval_role": "Engineer"},
    ).json()
    md = client.get(f"/engineering/runs/{created['run_id']}/summary.md").text
    for section in [
        "## Task Decomposition",
        "## Trade-offs and Rationale",
        "## Artifacts",
        "## Quality Gates (Validation)",
        "## Risks",
        "## Assumptions",
        "## Limitations",
        "## Final Summary",
    ]:
        assert section in md


def test_assumptions_and_limitations_follow_the_requirement(tmp_path):
    client = reset_app(tmp_path)
    expiry = _brownfield(client, "Add expiry to links")
    custom = _brownfield(client, "Add custom vanity endpoints")
    assert expiry["assumptions"] != custom["assumptions"]
    assert any("expired" in limitation.lower() for limitation in expiry["limitations"])
    assert any("route names" in limitation.lower() for limitation in custom["limitations"])

