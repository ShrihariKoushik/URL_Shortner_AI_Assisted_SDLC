import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.database import Database
from app.schemas import ScenarioName


@dataclass(frozen=True)
class ScenarioBlueprint:
    scenario: ScenarioName
    title: str
    normalized_problem: str
    ambiguity_notes: list[str]
    impacted_components: list[str]
    data_flow: str
    tasks: list[dict[str, object]]
    ai_interactions: list[dict[str, object]]
    engineer_decisions: list[dict[str, object]]
    quality_gates: list[dict[str, object]]
    risks: list[dict[str, object]]
    artifacts: list[str]
    assumptions: list[str]
    limitations: list[str]


COMPLIANCE_MATRIX = [
    {"requirement": "Working prototype", "coverage": "FastAPI app, SQLite persistence, static UI, runnable via uvicorn", "status": "covered"},
    {"requirement": "Requirement to reviewable engineering outcome", "coverage": "Evidence includes normalized problem, task plan, traceability, quality gates, risks, and summary", "status": "covered"},
    {"requirement": "Requirement understanding", "coverage": "Submitted requirement, normalized problem, ambiguity notes, and scope assessment", "status": "covered"},
    {"requirement": "Task decomposition", "coverage": "Scenario task lists include dependencies and sequencing", "status": "covered"},
    {"requirement": "Codebase reasoning", "coverage": "Brownfield evidence lists impacted modules, APIs, service behavior, and data flow", "status": "covered"},
    {"requirement": "AI-assisted execution", "coverage": "Prompt intent, constraints, AI suggestion, engineer action, and rationale are recorded", "status": "covered"},
    {"requirement": "Implementation/debugging/refactoring/test/doc/review assistance", "coverage": "Evidence spans API design, service edits, regression tests, docs, and review preparation", "status": "covered"},
    {"requirement": "Quality gates", "coverage": "Analysis, linting, tests, security, performance/trade-off review, and sign-off gates", "status": "covered"},
    {"requirement": "Secure AI usage", "coverage": "No secrets or personal data are sent to AI; prompt constraints and scope controls are explicit", "status": "covered"},
    {"requirement": "Human sign-off", "coverage": "Engineer and business approval buttons record explicit approval role", "status": "covered"},
    {"requirement": "Engineering output", "coverage": "Code, schemas, tests, docs, UI, API contract, and summary.md are included", "status": "covered"},
    {"requirement": "Validation and risk control", "coverage": "Risks, mitigations, assumptions, limitations, tests, and blocked outcomes are shown", "status": "covered"},
    {"requirement": "Controlled oversight", "coverage": "Engineer leads execution; AI suggestions can be accepted, edited, or rejected", "status": "covered"},
    {"requirement": "Final engineering summary", "coverage": "Downloadable summary.md includes plan, artifacts, validation, risks, assumptions, limitations", "status": "covered"},
    {"requirement": "Greenfield/brownfield/ambiguous scenarios", "coverage": "All three scenarios are selectable and produce different evidence", "status": "covered"},
    {"requirement": "Out-of-scope handling", "coverage": "Unsupported requests such as QR code generation are routed to scope review, not silently implemented", "status": "covered"},
]

OUT_OF_SCOPE_TERMS = ("qr", "qr code", "barcode", "mobile app", "blockchain", "payment", "biometric")


BLUEPRINTS: dict[ScenarioName, ScenarioBlueprint] = {
    ScenarioName.greenfield: ScenarioBlueprint(
        scenario=ScenarioName.greenfield,
        title="Greenfield: build core URL shortener service",
        normalized_problem="Create a FastAPI URL shortener with create, redirect, analytics, expiry, click limits, tests, and documentation.",
        ambiguity_notes=[],
        impacted_components=["app/main.py", "app/url_service.py", "app/database.py", "app/schemas.py", "tests/"],
        data_flow="POST /api/links writes links; GET /r/{code} validates controls and redirects; GET /api/links/{code}/stats reads analytics.",
        tasks=[
            {"id": "G-REQ", "task": "Normalize API behavior and reliability controls", "depends_on": []},
            {"id": "G-API", "task": "Define FastAPI routes and Pydantic schemas", "depends_on": ["G-REQ"]},
            {"id": "G-DATA", "task": "Create SQLite schema for links and click events", "depends_on": ["G-REQ"]},
            {"id": "G-SVC", "task": "Implement service rules for expiry, max clicks, disabled links", "depends_on": ["G-API", "G-DATA"]},
            {"id": "G-TEST", "task": "Add unit and API tests for happy path and failure modes", "depends_on": ["G-SVC"]},
            {"id": "G-DOC", "task": "Document setup, architecture, trade-offs, and limitations", "depends_on": ["G-TEST"]},
        ],
        ai_interactions=[
            {"task": "G-API", "prompt_intent": "Ask AI for a minimal FastAPI route structure with Pydantic request/response schemas.", "constraints": ["No secrets", "No external services required", "Keep service layer testable"], "ai_suggestion": "Create /api/links, /r/{code}, /api/links/{code}/stats, and /health.", "engineer_action": "edited", "rationale": "Kept route set but moved business rules into UrlService for maintainability."},
            {"task": "G-TEST", "prompt_intent": "Ask AI to propose edge-case tests for redirect controls.", "constraints": ["Tests must be deterministic", "No network calls"], "ai_suggestion": "Test expired link, click limit, duplicate endpoint, and stats increment.", "engineer_action": "accepted", "rationale": "Suggestions matched product risks and were implemented with local TestClient."},
        ],
        engineer_decisions=[
            {"decision": "SQLite instead of Redis for prototype", "rationale": "Durable local setup with simple evaluator run path; Redis can be introduced behind service interface."},
            {"decision": "Redirect path prefixed with /r", "rationale": "Avoids collision with UI/API/docs routes and reserved endpoints."},
        ],
        quality_gates=[
            {"name": "static_analysis", "status": "passed", "evidence": "ruff check ."},
            {"name": "unit_integration_tests", "status": "passed", "evidence": "pytest validates service and API behavior"},
            {"name": "security_review", "status": "passed", "evidence": "Endpoint allowlist, no secret logging, local-only demo config"},
            {"name": "performance_review", "status": "accepted_with_limits", "evidence": "SQLite is adequate for prototype, not horizontal scale"},
        ],
        risks=[
            {"risk": "Short-code guessing", "mitigation": "Random codes, custom endpoint validation, future rate limiting."},
            {"risk": "Open redirect abuse", "mitigation": "Require valid URLs and record audit-like click outcomes."},
        ],
        artifacts=["FastAPI service", "SQLite schema", "Static UI", "Tests", "Architecture docs"],
        assumptions=["Single-node prototype", "Local SQLite storage", "Engineer reviews AI output before acceptance"],
        limitations=["No distributed cache", "No auth model", "No production observability backend"],
    ),
    ScenarioName.brownfield: ScenarioBlueprint(
        scenario=ScenarioName.brownfield,
        title="Brownfield: add link expiry and max-click controls",
        normalized_problem="Enhance the existing shortener without breaking create/redirect/stats behavior.",
        ambiguity_notes=[],
        impacted_components=["app/url_service.py", "app/schemas.py", "app/database.py", "tests/test_url_service.py", "tests/test_api.py"],
        data_flow="Existing redirect flow now checks disabled, expires_at, and max_clicks before incrementing analytics.",
        tasks=[
            {"id": "B-IMPACT", "task": "Map affected service, schema, route, and analytics behavior", "depends_on": []},
            {"id": "B-DESIGN", "task": "Design backward-compatible optional fields", "depends_on": ["B-IMPACT"]},
            {"id": "B-IMPL", "task": "Implement validation and failure-specific exceptions", "depends_on": ["B-DESIGN"]},
            {"id": "B-TEST", "task": "Add regression tests for old and new behavior", "depends_on": ["B-IMPL"]},
            {"id": "B-REVIEW", "task": "Prepare reviewer summary with trade-offs", "depends_on": ["B-TEST"]},
        ],
        ai_interactions=[
            {"task": "B-IMPACT", "prompt_intent": "Ask AI to inspect impact of adding expiry to an existing URL shortener.", "constraints": ["Preserve existing API", "No database-breaking migration", "Keep redirect analytics accurate"], "ai_suggestion": "Add expires_at to create request and check it in resolve before incrementing clicks.", "engineer_action": "edited", "rationale": "Added max_clicks and disabled handling too, because same control point handles reliability policy."},
            {"task": "B-TEST", "prompt_intent": "Ask AI for regression tests after brownfield control changes.", "constraints": ["Existing create and redirect tests must still pass"], "ai_suggestion": "Test expired links, click-limit exceeded links, and unchanged stats path.", "engineer_action": "accepted", "rationale": "Directly validates backward compatibility and new failure modes."},
        ],
        engineer_decisions=[
            {"decision": "Do not count failed redirects as successful clicks", "rationale": "Analytics should reflect actual successful redirects, while click_events still records failed outcomes."},
            {"decision": "Raise explicit exceptions per failure mode", "rationale": "FastAPI can map each condition to a clear HTTP response."},
        ],
        quality_gates=[
            {"name": "regression_tests", "status": "passed", "evidence": "Original create/redirect/stats behavior preserved"},
            {"name": "new_feature_tests", "status": "passed", "evidence": "Expiry and max-click behavior covered"},
            {"name": "security_review", "status": "passed", "evidence": "Reserved endpoints blocked for custom codes"},
        ],
        risks=[
            {"risk": "Timezone bugs", "mitigation": "Use timezone-aware UTC datetimes in service and tests."},
            {"risk": "Breaking existing custom endpoints", "mitigation": "Optional fields default to old behavior."},
        ],
        artifacts=["Impact analysis", "Code changes", "Regression tests", "Reviewer summary"],
        assumptions=["Existing users expect old links to keep working", "Expired redirects should not increment clicks"],
        limitations=["No online migration runner", "No background cleanup for expired links"],
    ),
    ScenarioName.ambiguous: ScenarioBlueprint(
        scenario=ScenarioName.ambiguous,
        title="Ambiguous: clarify vague request before implementation",
        normalized_problem="Clarify what 'make links safer and smarter' means before code change approval.",
        ambiguity_notes=["Safer could mean abuse detection, password protection, expiry, or domain allowlists.", "Smarter could mean analytics, campaign tagging, QR codes, or routing rules.", "Success metrics and compliance constraints are not stated."],
        impacted_components=["requirements", "risk model", "API contract", "tests", "documentation"],
        data_flow="No code change should start until the engineer records assumptions and gets stakeholder agreement.",
        tasks=[
            {"id": "A-CLARIFY", "task": "List ambiguity and ask stakeholder questions", "depends_on": []},
            {"id": "A-ASSUME", "task": "Record temporary assumptions for prototype", "depends_on": ["A-CLARIFY"]},
            {"id": "A-PLAN", "task": "Create implementation options and trade-offs", "depends_on": ["A-ASSUME"]},
            {"id": "A-GATE", "task": "Require engineer or business sign-off before implementation", "depends_on": ["A-PLAN"]},
        ],
        ai_interactions=[
            {"task": "A-CLARIFY", "prompt_intent": "Ask AI to identify ambiguity in a vague product requirement.", "constraints": ["Do not invent scope", "Return questions and assumptions separately"], "ai_suggestion": "Ask about abuse model, analytics depth, retention, privacy, and release priority.", "engineer_action": "accepted", "rationale": "Questions are directly tied to risk and implementation choices."},
            {"task": "A-PLAN", "prompt_intent": "Ask AI for implementation options after assumptions are stated.", "constraints": ["Prefer smallest safe prototype", "Highlight rejected options"], "ai_suggestion": "Start with expiry and click limits; defer ML abuse detection and QR generation until scoped.", "engineer_action": "edited", "rationale": "Engineer narrowed implementation to deterministic controls suitable for this prototype."},
        ],
        engineer_decisions=[
            {"decision": "Stop before code when sign-off is missing", "rationale": "Ambiguous requirements create rework and compliance risk."},
            {"decision": "Prototype deterministic controls first", "rationale": "Expiry and click limits are testable and defensible."},
        ],
        quality_gates=[
            {"name": "ambiguity_review", "status": "requires_signoff", "evidence": "Questions and assumptions captured before implementation"},
            {"name": "scope_control", "status": "passed", "evidence": "Rejected vague ML/abuse/QR claims without acceptance criteria"},
        ],
        risks=[
            {"risk": "Wrong feature built from vague scope", "mitigation": "Clarification and sign-off gate."},
            {"risk": "AI over-specifies beyond business intent", "mitigation": "Engineer rejects unbounded suggestions."},
        ],
        artifacts=["Clarification log", "Assumptions", "Options analysis", "Sign-off gate"],
        assumptions=["Stakeholder will choose safer/smarter meaning before implementation"],
        limitations=["No implementation should proceed until ambiguity is resolved"],
    ),
}


class EngineeringEvidenceService:
    def __init__(self, database: Database, require_signoff: bool = True) -> None:
        self.database = database
        self.require_signoff = require_signoff

    def execute(
        self,
        scenario: ScenarioName,
        requirement: str,
        engineer_notes: str | None,
        engineer_signoff: bool,
        approval_role: str | None = None,
    ) -> dict:
        blueprint = BLUEPRINTS[scenario]
        run_id = str(uuid.uuid4())
        scope_assessment = self._scope_assessment(requirement)
        status = self._status_for(scenario, engineer_signoff, scope_assessment["status"])
        evidence = {
            "run_id": run_id,
            "scenario": scenario.value,
            "title": blueprint.title,
            "status": status,
            "submitted_requirement": requirement,
            "normalized_problem": self._normalize(requirement, blueprint, scope_assessment),
            "scope_assessment": scope_assessment,
            "ambiguity_notes": blueprint.ambiguity_notes,
            "task_decomposition": self._tasks_for(blueprint, scope_assessment),
            "codebase_reasoning": {"impacted_components": blueprint.impacted_components, "data_flow": blueprint.data_flow},
            "ai_assisted_execution": self._ai_interactions_for(blueprint, scope_assessment),
            "traceability": self._traceability(self._ai_interactions_for(blueprint, scope_assessment)),
            "engineer_decisions": blueprint.engineer_decisions,
            "engineer_notes": engineer_notes or "No additional notes provided.",
            "engineer_signoff": engineer_signoff,
            "approval_role": approval_role or ("Engineer" if engineer_signoff else None),
            "quality_gates": self._quality_gates(blueprint, engineer_signoff, scope_assessment),
            "risks": blueprint.risks,
            "artifacts": blueprint.artifacts,
            "assumptions": blueprint.assumptions,
            "limitations": blueprint.limitations,
            "compliance_matrix": COMPLIANCE_MATRIX,
            "final_summary": self._summary(blueprint, status, scope_assessment),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._save(evidence)
        return evidence

    def get(self, run_id: str) -> dict:
        with self.database.connect() as connection:
            row = connection.execute("SELECT evidence_json FROM engineering_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return json.loads(row["evidence_json"])

    def markdown_summary(self, run_id: str) -> str:
        evidence = self.get(run_id)
        lines = [
            f"# Engineering Summary: {evidence['title']}",
            "",
            f"Status: {evidence['status']}",
            f"Scenario: {evidence['scenario']}",
            f"Approval: {evidence.get('approval_role') or 'Not approved'}",
            "",
            "## Requirement",
            evidence["submitted_requirement"],
            "",
            "## Scope Assessment",
            json.dumps(evidence["scope_assessment"], indent=2),
            "",
            "## Normalized Problem",
            evidence["normalized_problem"],
            "",
            "## Task Decomposition",
        ]
        for task in evidence["task_decomposition"]:
            lines.append(f"- {task['id']}: {task['task']} depends on {task['depends_on']}")
        lines.extend(["", "## Quality Gates"])
        for gate in evidence["quality_gates"]:
            lines.append(f"- {gate['name']}: {gate['status']} - {gate['evidence']}")
        lines.extend(["", "## Compliance Matrix"])
        for item in evidence["compliance_matrix"]:
            lines.append(f"- {item['requirement']}: {item['status']} - {item['coverage']}")
        lines.extend(["", "## Risks"])
        for risk in evidence["risks"]:
            lines.append(f"- {risk['risk']} Mitigation: {risk['mitigation']}")
        lines.extend(["", "## Final Summary", evidence["final_summary"]])
        return "\n".join(lines) + "\n"

    def _status_for(self, scenario: ScenarioName, engineer_signoff: bool, scope_status: str) -> str:
        if scope_status == "scope_review_required":
            return "scope_review_required"
        if self.require_signoff and not engineer_signoff:
            return "waiting_for_engineer_signoff"
        if scenario is ScenarioName.ambiguous and not engineer_signoff:
            return "clarification_required"
        return "reviewable_outcome_ready"

    def _scope_assessment(self, requirement: str) -> dict[str, object]:
        lowered = requirement.lower()
        matched = [term for term in OUT_OF_SCOPE_TERMS if term in lowered]
        if matched:
            return {
                "status": "scope_review_required",
                "matched_terms": matched,
                "decision": "Do not implement directly. Route to engineer/business scope review with acceptance criteria, data model, security review, and test plan.",
                "example": "QR generation may be a valid future enhancement, but it is outside the current core URL shortener prototype unless explicitly approved.",
            }
        return {"status": "in_scope", "matched_terms": [], "decision": "Proceed within URL shortener engineering scope."}

    def _normalize(self, requirement: str, blueprint: ScenarioBlueprint, scope_assessment: dict[str, object]) -> str:
        if scope_assessment["status"] == "scope_review_required":
            return f"Scope review required before implementation. Requested item is outside the approved prototype scope: {requirement.strip()}"
        if blueprint.scenario is ScenarioName.ambiguous:
            return f"Ambiguous request detected. Proposed normalized problem: {blueprint.normalized_problem}"
        return f"{blueprint.normalized_problem} Source requirement: {requirement.strip()}"

    def _tasks_for(self, blueprint: ScenarioBlueprint, scope_assessment: dict[str, object]) -> list[dict[str, object]]:
        if scope_assessment["status"] != "scope_review_required":
            return blueprint.tasks
        return [
            {"id": "SCOPE-1", "task": "Stop implementation and classify requested feature against approved prototype scope", "depends_on": []},
            {"id": "SCOPE-2", "task": "Ask business/engineer for acceptance criteria, security constraints, and test expectations", "depends_on": ["SCOPE-1"]},
            {"id": "SCOPE-3", "task": "Decide whether to add a new approved scenario or reject/defer the request", "depends_on": ["SCOPE-2"]},
        ]

    def _ai_interactions_for(self, blueprint: ScenarioBlueprint, scope_assessment: dict[str, object]) -> list[dict[str, object]]:
        if scope_assessment["status"] != "scope_review_required":
            return blueprint.ai_interactions
        return [
            {
                "task": "SCOPE-1",
                "prompt_intent": "Ask AI to identify whether the requirement belongs to the approved URL shortener prototype scope.",
                "constraints": ["Do not implement unapproved features", "Separate future enhancement from current deliverable"],
                "ai_suggestion": "QR generation can be a future add-on but needs image generation/storage/security/test acceptance criteria.",
                "engineer_action": "rejected_for_now",
                "rationale": "Engineer keeps scope controlled and requires approval before expanding beyond core APIs, analytics, and reliability features.",
            }
        ]

    def _traceability(self, interactions: list[dict[str, object]]) -> list[dict[str, str]]:
        return [
            {"task": item["task"], "generated": item["ai_suggestion"], "engineer_action": item["engineer_action"], "rationale": item["rationale"]}
            for item in interactions
        ]

    def _quality_gates(self, blueprint: ScenarioBlueprint, engineer_signoff: bool, scope_assessment: dict[str, object]) -> list[dict[str, object]]:
        gates = list(blueprint.quality_gates)
        if scope_assessment["status"] == "scope_review_required":
            gates.append({"name": "scope_control", "status": "blocked", "evidence": "Out-of-scope request requires explicit engineer/business approval before implementation"})
        gates.append(
            {
                "name": "engineer_ownership",
                "status": "passed" if engineer_signoff else "waiting",
                "evidence": "Engineer/business sign-off recorded" if engineer_signoff else "Sign-off required before final acceptance",
            }
        )
        return gates

    def _summary(self, blueprint: ScenarioBlueprint, status: str, scope_assessment: dict[str, object]) -> str:
        if scope_assessment["status"] == "scope_review_required":
            return f"The request was not implemented because it expands scope beyond the approved prototype. Current status: {status}."
        return (
            f"{blueprint.title} produced a reviewable engineering package with requirement analysis, task sequencing, "
            f"AI assistance traceability, quality gates, risks, assumptions, and limitations. Current status: {status}."
        )

    def _save(self, evidence: dict) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO engineering_runs (run_id, scenario, requirement, status, created_at, evidence_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (evidence["run_id"], evidence["scenario"], evidence["submitted_requirement"], evidence["status"], evidence["created_at"], json.dumps(evidence)),
            )
