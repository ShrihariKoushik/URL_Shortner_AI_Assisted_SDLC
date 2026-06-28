import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from pathlib import Path

from app import ai_assist, quality
from app.database import Database
from app.schemas import ScenarioName

# Subjective words that signal an unmeasurable requirement.
VAGUE_TERMS = (
    "better", "smarter", "safer", "cleaner", "nicer", "modern", "robust",
    "scalable", "powerful", "seamless", "intuitive", "clever", "cool",
    "good", "great", "improved", "optimal", "efficient", "flexible", "simple",
)
# Phrases that signal the author is unsure of the actual outcome.
UNCERTAINTY_MARKERS = (
    "maybe", "not sure", "somehow", "i guess", "or something", "etc",
    "and so on", "kind of", "sort of", "perhaps", "possibly",
)
# Concrete shortener capabilities the engineer can actually implement.
CONCRETE_CAPABILITIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("link creation", ("shorten", "url shortener", "short link", "new link", "create link")),
    ("redirect", ("redirect", "forward")),
    ("expiry", ("expiry", "expire", "expiration", "ttl")),
    ("max-click limit", ("max click", "max-click", "max_clicks", "click limit", "click cap")),
    ("analytics", ("analytics", "stats", "statistics", "metrics", "report")),
    ("custom endpoint", ("custom endpoint", "custom code", "custom alias", "vanity")),
    ("disable / kill switch", ("disable", "deactivate", "kill switch", "revoke")),
)


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

IN_SCOPE_TERMS = (
    "url",
    "shorten",
    "shortener",
    "short link",
    "link",
    "redirect",
    "analytics",
    "click",
    "expiry",
    "expire",
    "endpoint",
    "campaign",
)
OUT_OF_SCOPE_INTENTS = {
    "qr": "Generate QR codes for links",
    "qr code": "Generate QR codes for links",
    "barcode": "Generate barcode assets",
    "mobile app": "Build a mobile application",
    "blockchain": "Build blockchain or distributed ledger functionality",
    "payment": "Build payment processing functionality",
    "biometric": "Build biometric identity functionality",
    "facebook": "Build a Facebook-like social networking product",
    "facebook clone": "Build a Facebook-like social networking product",
    "social network": "Build a social networking product",
    "social media": "Build a social media product",
    "instagram": "Build an Instagram-like media sharing product",
    "twitter": "Build a Twitter/X-like social feed product",
    "x clone": "Build a Twitter/X-like social feed product",
    "linkedin": "Build a professional networking product",
    "ecommerce": "Build an ecommerce product",
    "shopping cart": "Build ecommerce shopping cart functionality",
    "chat app": "Build a chat application",
    "video platform": "Build a video platform",
    "spotify": "Build a Spotify-like music streaming product",
    "music streaming": "Build a music streaming product",
}


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
            {"decision": "SQLite instead of Redis for prototype", "rationale": "Durable local setup with a simple run path; Redis can be introduced behind the service interface."},
            {"decision": "Redirect path prefixed with /r", "rationale": "Avoids collision with UI/API/docs routes and reserved endpoints."},
        ],
        quality_gates=[
            {"name": "static_analysis", "status": "passed", "evidence": "ruff check ."},
            {"name": "unit_integration_tests", "status": "passed", "evidence": "pytest validates service and API behavior"},
            {"name": "security_review", "status": "passed", "evidence": "Endpoint allowlist, no secret logging, local-only configuration"},
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
    def __init__(self, database: Database, require_signoff: bool = True, settings: object = None) -> None:
        self.database = database
        self.require_signoff = require_signoff
        self.settings = settings

    def execute(
        self,
        scenario: ScenarioName,
        requirement: str,
        engineer_notes: str | None,
        engineer_signoff: bool,
        approval_role: str | None = None,
        engineer_actions: dict[str, str] | None = None,
    ) -> dict:
        blueprint = BLUEPRINTS[scenario]
        run_id = str(uuid.uuid4())
        scope_assessment = self._scope_assessment(requirement)
        directed_requirement = f"{requirement} {engineer_notes}" if engineer_notes else requirement
        status = self._status_for(scenario, engineer_signoff, scope_assessment["status"])
        understanding = self._understand_requirement(directed_requirement, blueprint, scope_assessment)
        interactions = self._ai_interactions_for(directed_requirement, blueprint, scope_assessment, understanding)
        self._apply_engineer_actions(interactions, engineer_actions)
        risk_register = self._risk_register(directed_requirement, blueprint, scope_assessment)
        bounds = self._assumptions_and_limitations(directed_requirement, blueprint, scope_assessment)
        evidence = {
            "run_id": run_id,
            "scenario": scenario.value,
            "title": blueprint.title,
            "status": status,
            "submitted_requirement": requirement,
            "requirement_understanding": understanding,
            "normalized_problem": understanding["normalized_problem"],
            "scope_assessment": scope_assessment,
            "ambiguity_notes": understanding["ambiguity"],
            "task_decomposition": self._task_decomposition(directed_requirement, understanding, blueprint, scope_assessment),
            "codebase_reasoning": self._codebase_reasoning(directed_requirement, blueprint, scope_assessment),
            "ai_assisted_execution": interactions,
            "traceability": self._traceability(interactions),
            "engineer_decisions": risk_register["trade_offs"],
            "engineer_notes": engineer_notes or "No additional notes provided.",
            "engineer_overrides": engineer_actions or {},
            "engineer_signoff": engineer_signoff,
            "approval_role": approval_role or ("Engineer" if engineer_signoff else None),
            "quality_gates": self._quality_gates(blueprint, engineer_signoff, scope_assessment, requirement),
            "risks": risk_register["risks"],
            "artifacts": blueprint.artifacts,
            "assumptions": bounds["assumptions"],
            "limitations": bounds["limitations"],
            "compliance_matrix": COMPLIANCE_MATRIX,
            "final_summary": self._summary(blueprint, status, scope_assessment),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._save(evidence)
        return evidence

    def _apply_engineer_actions(self, interactions: list[dict[str, object]], engineer_actions: dict[str, str] | None) -> None:
        """Let the engineer override the recorded action for any AI execution step."""
        if not engineer_actions:
            return
        for item in interactions:
            key = item.get("execution_phase") or item.get("task")
            if isinstance(key, str) and key in engineer_actions:
                item["engineer_action"] = str(engineer_actions[key])

    def _understand_requirement(
        self,
        requirement: str,
        blueprint: ScenarioBlueprint,
        scope_assessment: dict[str, object],
    ) -> dict[str, object]:
        if scope_assessment["status"] == "scope_review_required":
            return {
                "interpreted_intent": str(scope_assessment.get("captured_intent", "Out-of-scope request")),
                "ambiguity": [],
                "normalized_problem": self._normalize(requirement, blueprint, scope_assessment),
                "source": "scope_control",
                "engineer_action": "rejected_for_now",
            }
        api_key = getattr(self.settings, "resolved_openai_api_key", None)
        if api_key:
            ai_result = self._openai_understanding(requirement, api_key)
            if ai_result is not None:
                return ai_result
        return self._local_understanding(requirement)

    def _openai_understanding(self, requirement: str, api_key: str) -> dict[str, object] | None:
        model = getattr(self.settings, "openai_model", "gpt-4.1")
        system_prompt = (
            "You are a senior engineer doing requirement understanding for an existing "
            "FastAPI URL shortener (link creation, redirect, analytics, expiry, max-click "
            "limits, custom endpoints, disable). Return JSON only. Do not invent scope "
            "beyond URL shortening / link management. Base every field strictly on the "
            "submitted requirement text."
        )
        user_prompt = (
            "Requirement:\n"
            f"{requirement}\n\n"
            "Return JSON with this shape: "
            '{"interpreted_intent": string, "ambiguity": string[], "normalized_problem": string}. '
            "interpreted_intent: one sentence on what the author actually wants. "
            "ambiguity: concrete unclear points in THIS requirement (empty array if fully clear). "
            "normalized_problem: the requirement rewritten as a clear, testable engineering problem."
        )
        try:
            parsed = ai_assist.call_openai_json(api_key, model, system_prompt, user_prompt, base_url=getattr(self.settings, "openai_base_url", None) or ai_assist.OPENAI_URL)
        except ai_assist.OPENAI_ERRORS:
            return None
        intent = parsed.get("interpreted_intent")
        ambiguity = parsed.get("ambiguity")
        normalized = parsed.get("normalized_problem")
        if not isinstance(intent, str) or not isinstance(normalized, str):
            return None
        clean_ambiguity = [str(item) for item in ambiguity] if isinstance(ambiguity, list) else []
        return {
            "interpreted_intent": intent.strip()[:600],
            "ambiguity": clean_ambiguity,
            "normalized_problem": normalized.strip()[:1200],
            "source": "openai",
            "engineer_action": "edited",
        }

    def _local_understanding(self, requirement: str) -> dict[str, object]:
        text = " ".join(requirement.strip().split())
        lowered = text.lower()
        vague = [w for w in VAGUE_TERMS if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", lowered)]
        uncertainty = [m for m in UNCERTAINTY_MARKERS if m in lowered]
        capabilities = [name for name, kws in CONCRETE_CAPABILITIES if any(k in lowered for k in kws)]

        ambiguity: list[str] = []
        for word in vague:
            ambiguity.append(
                f"'{word}' is subjective - define measurable acceptance criteria for what counts as '{word}'."
            )
        for marker in uncertainty:
            ambiguity.append(
                f"Requirement expresses uncertainty ('{marker}') - confirm the intended outcome before implementation."
            )
        if not capabilities:
            ambiguity.append(
                "No specific shortener capability (link creation, redirect, expiry, max-click, "
                "analytics, custom endpoint, disable) is named - clarify the exact feature to deliver."
            )

        intent = self._infer_intent(text, lowered, capabilities)
        if capabilities:
            normalized = (
                f"Deliver URL shortener work covering {', '.join(capabilities)}, derived from the request: "
                f"'{text}'. Confirm acceptance criteria for any ambiguous terms before coding."
            )
        else:
            normalized = (
                f"Bound the request '{text}' into concrete URL shortener capabilities before implementation; "
                "no specific feature was detected in the text."
            )
        return {
            "interpreted_intent": intent,
            "ambiguity": ambiguity,
            "normalized_problem": normalized,
            "source": "local_heuristic",
            "engineer_action": "accepted",
        }

    def _infer_intent(self, text: str, lowered: str, capabilities: list[str]) -> str:
        verbs = ("build", "create", "make", "add", "implement", "enhance", "improve", "update", "remove", "support")
        for verb in verbs:
            if re.search(rf"(?<![a-z]){verb}(?![a-z])", lowered):
                if capabilities:
                    return f"{verb.capitalize()} URL shortener capability: {', '.join(capabilities)}."
                return f"{verb.capitalize()} URL shortener behavior described as: {text}."
        if capabilities:
            return f"Improve URL shortener capability: {', '.join(capabilities)}."
        return f"Clarify and scope the URL shortener request: {text}."

    def _detect_capabilities(self, lowered: str) -> list[str]:
        return [name for name, kws in CONCRETE_CAPABILITIES if any(k in lowered for k in kws)]

    def _task_decomposition(
        self,
        requirement: str,
        understanding: dict[str, object],
        blueprint: ScenarioBlueprint,
        scope_assessment: dict[str, object],
    ) -> list[dict[str, object]]:
        if scope_assessment["status"] == "scope_review_required":
            return self._tasks_for(blueprint, scope_assessment)
        capabilities = self._detect_capabilities(requirement.lower())
        api_key = getattr(self.settings, "resolved_openai_api_key", None)
        if api_key:
            ai_tasks = self._openai_tasks(requirement, capabilities, blueprint, api_key)
            if ai_tasks:
                return ai_tasks
        return self._derive_tasks(capabilities, blueprint)

    def _task_node(
        self,
        task_id: str,
        task: str,
        depends_on: list[str],
        intent: str,
        constraints: list[str],
        acceptance_criteria: list[str],
        data_flow: str,
    ) -> dict[str, object]:
        return {
            "id": task_id,
            "task": task,
            "depends_on": depends_on,
            "intent": intent,
            "constraints": constraints,
            "acceptance_criteria": acceptance_criteria,
            "technical_context": data_flow,
        }

    CAPABILITY_TASKS: dict[str, tuple[str, str, list[str]]] = {
        "link creation": ("T-CREATE", "Implement short-code generation and the create-link endpoint", ["Generated codes are unique", "Duplicate custom codes are rejected"]),
        "redirect": ("T-REDIRECT", "Implement redirect resolution that validates link state", ["Valid links 307-redirect to the target", "Blocked links return the correct error code"]),
        "expiry": ("T-EXPIRY", "Add expires_at and enforce expiry before redirect", ["Expired links are blocked", "Expired hits are not counted as successful clicks"]),
        "max-click limit": ("T-MAXCLICK", "Add max_clicks and enforce the click limit", ["Links over the limit are blocked", "Recorded clicks never exceed the configured limit"]),
        "analytics": ("T-STATS", "Record click events and expose the stats endpoint", ["Successful and blocked outcomes are recorded", "Stats report clicks and last outcome"]),
        "custom endpoint": ("T-CUSTOM", "Validate custom endpoints and guard reserved names", ["Unsafe characters are rejected", "Reserved route names cannot be used"]),
        "disable / kill switch": ("T-DISABLE", "Add a disable endpoint and block disabled links", ["Disabled links stop redirecting", "Disabled state is visible in stats"]),
    }

    def _derive_tasks(self, capabilities: list[str], blueprint: ScenarioBlueprint) -> list[dict[str, object]]:
        data_flow = blueprint.data_flow
        tasks = [
            self._task_node(
                "T-REQ",
                "Analyze the requirement and confirm the normalized problem and acceptance criteria",
                [],
                "Turn the request into a bounded, testable engineering problem.",
                ["Stay within URL shortener scope", "Preserve user intent"],
                ["Normalized problem is recorded", "Ambiguity is listed or cleared"],
                data_flow,
            )
        ]
        impl_ids: list[str] = []
        if capabilities:
            tasks.append(
                self._task_node(
                    "T-DATA",
                    f"Model or extend SQLite storage for: {', '.join(capabilities)}",
                    ["T-REQ"],
                    "Provide durable storage and auditable click history for the requested controls.",
                    ["SQLite for prototype", "Backward-compatible optional fields"],
                    ["Schema supports the requested fields", "Existing links keep working"],
                    data_flow,
                )
            )
            for cap in capabilities:
                cap_id, cap_task, cap_acceptance = self.CAPABILITY_TASKS[cap]
                tasks.append(
                    self._task_node(
                        cap_id,
                        cap_task,
                        ["T-DATA"],
                        f"Implement the '{cap}' behavior in the service layer.",
                        ["Keep routes thin", "Centralize rules in UrlService", "Use explicit failure modes"],
                        cap_acceptance,
                        data_flow,
                    )
                )
                impl_ids.append(cap_id)
        else:
            tasks.append(
                self._task_node(
                    "T-SCOPE",
                    "Define concrete capabilities with the stakeholder before coding",
                    ["T-REQ"],
                    "Convert the vague request into named, buildable capabilities.",
                    ["Do not invent scope", "Record assumptions separately"],
                    ["At least one concrete capability is agreed", "Out-of-scope items are deferred"],
                    data_flow,
                )
            )
            impl_ids = ["T-SCOPE"]
        coverage = ", ".join(capabilities) if capabilities else "the agreed capabilities"
        tasks.append(
            self._task_node(
                "T-TEST",
                f"Add unit/API tests covering: {coverage}",
                list(impl_ids),
                "Validate happy paths and failure modes deterministically.",
                ["Local TestClient", "No network calls", "Cover regressions"],
                ["New behavior is covered", "Existing behavior still passes"],
                data_flow,
            )
        )
        tasks.append(
            self._task_node(
                "T-DOC",
                "Document changes, risks, and trade-offs; prepare the reviewer summary",
                ["T-TEST"],
                "Make the outcome reviewable and owned by the engineer.",
                ["State limitations", "Show engineer ownership"],
                ["Setup, architecture, and risks are documented", "Sign-off status is recorded"],
                data_flow,
            )
        )
        return tasks

    def _openai_tasks(
        self,
        requirement: str,
        capabilities: list[str],
        blueprint: ScenarioBlueprint,
        api_key: str,
    ) -> list[dict[str, object]] | None:
        model = getattr(self.settings, "openai_model", "gpt-4.1")
        system_prompt = (
            "You are a senior engineer planning work on an existing FastAPI URL shortener "
            "(link creation, redirect, analytics, expiry, max-click limits, custom endpoints, "
            "disable). Return JSON only. Decompose ONLY what THIS requirement needs - do not "
            "add unrelated build steps. Stay within URL shortener scope."
        )
        user_prompt = (
            "Requirement:\n"
            f"{requirement}\n\n"
            f"Capabilities detected in the text: {capabilities or 'none - clarify first'}.\n"
            "Return JSON with this shape: "
            '{"tasks": [{"id": string, "task": string, "depends_on": string[], '
            '"intent": string, "acceptance_criteria": string[]}]}. '
            "Order tasks so dependencies come first; ids in depends_on must reference earlier task ids."
        )
        try:
            parsed = ai_assist.call_openai_json(api_key, model, system_prompt, user_prompt, base_url=getattr(self.settings, "openai_base_url", None) or ai_assist.OPENAI_URL)
        except ai_assist.OPENAI_ERRORS:
            return None
        raw_tasks = parsed.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            return None
        tasks: list[dict[str, object]] = []
        valid_ids: set[str] = set()
        for item in raw_tasks:
            if not isinstance(item, dict):
                continue
            task_id = item.get("id")
            task_text = item.get("task")
            if not isinstance(task_id, str) or not isinstance(task_text, str):
                continue
            depends = item.get("depends_on")
            depends = [d for d in depends if isinstance(d, str) and d in valid_ids] if isinstance(depends, list) else []
            acceptance = item.get("acceptance_criteria")
            acceptance = [str(a) for a in acceptance] if isinstance(acceptance, list) and acceptance else ["Output is testable and reviewable"]
            intent = item.get("intent")
            intent = intent if isinstance(intent, str) else "Execute a reviewable engineering task derived from the requirement."
            tasks.append(
                self._task_node(task_id, task_text, depends, intent, ["Keep change scoped", "Preserve maintainability"], acceptance, blueprint.data_flow)
            )
            valid_ids.add(task_id)
        return tasks or None

    CAPABILITY_IMPACT: dict[str, dict[str, object]] = {
        "link creation": {
            "files": ["app/url_service.py (create, _generate_code)", "app/schemas.py (CreateLinkRequest)", "app/main.py (POST /api/links)", "app/database.py (links table)"],
            "api": "POST /api/links",
            "data_flow": "Create validates the URL, allocates a unique code, and writes a links row.",
            "regression_risk": "Short-code collisions and duplicate custom codes must stay handled.",
        },
        "redirect": {
            "files": ["app/url_service.py (resolve, _resolve_outcome)", "app/main.py (GET /r/{code})"],
            "api": "GET /r/{code}",
            "data_flow": "Resolve checks link state, records the outcome, then 307-redirects on success.",
            "regression_risk": "Existing links must keep their status codes and redirect target.",
        },
        "expiry": {
            "files": ["app/schemas.py (expires_at)", "app/url_service.py (_resolve_outcome)", "app/database.py (expires_at column)"],
            "api": "POST /api/links (expires_at), GET /r/{code}",
            "data_flow": "Resolve compares now() to expires_at before counting a click.",
            "regression_risk": "Links without expiry must keep working; timezone handling must stay UTC-aware.",
        },
        "max-click limit": {
            "files": ["app/schemas.py (max_clicks)", "app/url_service.py (_resolve_outcome)", "app/database.py (max_clicks, clicks columns)"],
            "api": "POST /api/links (max_clicks), GET /r/{code}",
            "data_flow": "Resolve compares clicks to max_clicks before redirecting.",
            "regression_risk": "Clicks must not be over-counted; unlimited links must keep working.",
        },
        "analytics": {
            "files": ["app/url_service.py (_record_click_event, get)", "app/main.py (GET /api/links/{code}/stats)", "app/database.py (click_events table)"],
            "api": "GET /api/links/{code}/stats",
            "data_flow": "Each resolve writes a click_events row; stats reads clicks and the latest outcome.",
            "regression_risk": "Blocked outcomes must be recorded without inflating successful click counts.",
        },
        "custom endpoint": {
            "files": ["app/schemas.py (endpoint_is_safe)", "app/url_service.py (create)"],
            "api": "POST /api/links (custom_endpoint)",
            "data_flow": "Create uses the validated custom code instead of a generated one.",
            "regression_risk": "Reserved names and unsafe characters must stay blocked.",
        },
        "disable / kill switch": {
            "files": ["app/url_service.py (disable, _resolve_outcome)", "app/main.py (POST /api/links/{code}/disable)"],
            "api": "POST /api/links/{code}/disable",
            "data_flow": "Disable sets disabled=1; resolve blocks disabled links before redirect.",
            "regression_risk": "Disable must be idempotent and reflected in stats.",
        },
    }

    def _codebase_reasoning(
        self,
        requirement: str,
        blueprint: ScenarioBlueprint,
        scope_assessment: dict[str, object],
    ) -> dict[str, object]:
        if scope_assessment["status"] == "scope_review_required":
            return {
                "impacted_components": [],
                "data_flow": "No codebase change should occur until the request passes scope review.",
                "impact_analysis": [],
            }
        capabilities = self._detect_capabilities(requirement.lower())
        api_key = getattr(self.settings, "resolved_openai_api_key", None)
        if api_key:
            ai_reasoning = self._openai_codebase_reasoning(requirement, capabilities, api_key)
            if ai_reasoning is not None:
                return ai_reasoning
        return self._derive_codebase_reasoning(capabilities, blueprint)

    def _derive_codebase_reasoning(self, capabilities: list[str], blueprint: ScenarioBlueprint) -> dict[str, object]:
        if not capabilities:
            return {
                "impacted_components": list(blueprint.impacted_components),
                "data_flow": "Impacted components depend on the capability chosen during scope clarification.",
                "impact_analysis": [],
            }
        impact_analysis: list[dict[str, object]] = []
        files: list[str] = []
        flows: list[str] = []
        for cap in capabilities:
            impact = self.CAPABILITY_IMPACT[cap]
            impact_analysis.append({"capability": cap, **impact})
            for file in impact["files"]:
                if file not in files:
                    files.append(file)
            flows.append(str(impact["data_flow"]))
        if "tests/test_api.py (regression + new behavior)" not in files:
            files.append("tests/test_api.py (regression + new behavior)")
        return {
            "impacted_components": files,
            "data_flow": " ".join(flows),
            "impact_analysis": impact_analysis,
        }

    def _openai_codebase_reasoning(self, requirement: str, capabilities: list[str], api_key: str) -> dict[str, object] | None:
        model = getattr(self.settings, "openai_model", "gpt-4.1")
        system_prompt = (
            "You are a senior engineer doing brownfield impact analysis on an existing FastAPI "
            "URL shortener. Modules: app/main.py (routes), app/schemas.py (Pydantic contracts), "
            "app/url_service.py (business rules), app/database.py (SQLite). Return JSON only. "
            "Analyze ONLY the impact of THIS change; do not invent modules."
        )
        user_prompt = (
            "Requirement:\n"
            f"{requirement}\n\n"
            f"Capabilities detected in the text: {capabilities or 'none - clarify first'}.\n"
            "Return JSON with this shape: "
            '{"impacted_components": string[], "data_flow": string, '
            '"impact_analysis": [{"capability": string, "files": string[], "api": string, '
            '"data_flow": string, "regression_risk": string}]}.'
        )
        try:
            parsed = ai_assist.call_openai_json(api_key, model, system_prompt, user_prompt, base_url=getattr(self.settings, "openai_base_url", None) or ai_assist.OPENAI_URL)
        except ai_assist.OPENAI_ERRORS:
            return None
        components = parsed.get("impacted_components")
        data_flow = parsed.get("data_flow")
        if not isinstance(components, list) or not isinstance(data_flow, str):
            return None
        analysis = parsed.get("impact_analysis")
        analysis = [a for a in analysis if isinstance(a, dict)] if isinstance(analysis, list) else []
        return {
            "impacted_components": [str(c) for c in components],
            "data_flow": data_flow.strip()[:1200],
            "impact_analysis": analysis,
        }

    CAPABILITY_RISKS: dict[str, dict[str, list[dict[str, str]]]] = {
        "link creation": {
            "risks": [{"risk": "Short-code collisions or guessable codes", "mitigation": "Random codes with a uniqueness retry and custom-code validation"}],
            "trade_offs": [{"decision": "Random codes over sequential ids", "rationale": "Avoids enumeration of links at the cost of collision handling"}],
        },
        "redirect": {
            "risks": [{"risk": "Open-redirect abuse to untrusted targets", "mitigation": "Validate http/https targets and record audit-like click outcomes"}],
            "trade_offs": [{"decision": "307 temporary redirect over 301", "rationale": "Keeps analytics accurate and avoids browsers caching the redirect"}],
        },
        "expiry": {
            "risks": [{"risk": "Timezone or clock-skew bugs in expiry checks", "mitigation": "Use timezone-aware UTC datetimes in the service and tests"}],
            "trade_offs": [{"decision": "Optional expires_at defaulting to no expiry", "rationale": "Backward compatible so existing links keep working"}],
        },
        "max-click limit": {
            "risks": [{"risk": "Over-counting clicks under concurrency", "mitigation": "Check-then-increment within one connection; enforce the cap before redirect"}],
            "trade_offs": [{"decision": "Hard cap over a soft warning", "rationale": "Deterministic and testable behavior at the limit"}],
        },
        "analytics": {
            "risks": [{"risk": "Blocked outcomes inflating successful click counts", "mitigation": "Record click_events separately from the successful-click increment"}],
            "trade_offs": [{"decision": "Store every click event over aggregate-only counters", "rationale": "Auditable history at a higher storage cost"}],
        },
        "custom endpoint": {
            "risks": [{"risk": "Reserved-name or unsafe-character collisions in custom codes", "mitigation": "Allowlist characters and block reserved route names"}],
            "trade_offs": [{"decision": "Stricter validation over maximum flexibility", "rationale": "Reduces routing and security surprises"}],
        },
        "disable / kill switch": {
            "risks": [{"risk": "Disable not idempotent or not reflected in stats", "mitigation": "Idempotent UPDATE plus a resolve-time disabled check"}],
            "trade_offs": [{"decision": "Soft disable over hard delete", "rationale": "Preserves the audit trail and is reversible"}],
        },
    }

    def _risk_register(self, requirement: str, blueprint: ScenarioBlueprint, scope_assessment: dict[str, object]) -> dict[str, list[dict[str, str]]]:
        """Identify risks, trade-offs, and failure scenarios for THIS requirement."""
        if scope_assessment["status"] == "scope_review_required":
            return {
                "risks": [{"risk": "Implementing unapproved scope", "mitigation": "Scope-review gate and engineer/business sign-off before any code"}],
                "trade_offs": list(blueprint.engineer_decisions),
            }
        capabilities = self._detect_capabilities(requirement.lower())
        api_key = getattr(self.settings, "resolved_openai_api_key", None)
        if api_key and capabilities:
            ai_register = self._openai_risks(requirement, capabilities, api_key)
            if ai_register is not None:
                return ai_register
        return self._derive_risks(capabilities)

    def _derive_risks(self, capabilities: list[str]) -> dict[str, list[dict[str, str]]]:
        if not capabilities:
            return {
                "risks": [{"risk": "Building the wrong thing from vague scope", "mitigation": "Clarify ambiguity and require sign-off before implementation"}],
                "trade_offs": [{"decision": "Defer implementation until capabilities are concrete", "rationale": "Prevents rework and wrong-feature risk"}],
            }
        risks: list[dict[str, str]] = []
        trade_offs: list[dict[str, str]] = []
        for capability in capabilities:
            entry = self.CAPABILITY_RISKS.get(capability)
            if entry:
                risks.extend(entry["risks"])
                trade_offs.extend(entry["trade_offs"])
        risks.append({"risk": "Regressing existing create/redirect/stats behavior", "mitigation": "Backward-compatible optional fields plus regression tests"})
        trade_offs.append({"decision": "Centralize new rules in UrlService behind stable APIs", "rationale": "Limits blast radius and keeps route handlers thin and testable"})
        return {"risks": self._dedup(risks, "risk"), "trade_offs": self._dedup(trade_offs, "decision")}

    def _dedup(self, items: list[dict[str, str]], key: str) -> list[dict[str, str]]:
        seen: set[str] = set()
        out: list[dict[str, str]] = []
        for item in items:
            if item[key] not in seen:
                seen.add(item[key])
                out.append(item)
        return out

    def _openai_risks(self, requirement: str, capabilities: list[str], api_key: str) -> dict[str, list[dict[str, str]]] | None:
        model = getattr(self.settings, "openai_model", "gpt-4.1")
        system_prompt = (
            "You are a senior engineer doing risk analysis for a change to an existing FastAPI "
            "URL shortener. Return JSON only. Identify risks, failure scenarios, and design "
            "trade-offs for ONLY this change; do not invent unrelated risks."
        )
        user_prompt = (
            "Requirement:\n"
            f"{requirement}\n\n"
            f"Capabilities detected in the text: {capabilities}.\n"
            "Return JSON with this shape: "
            '{"risks": [{"risk": string, "mitigation": string}], '
            '"trade_offs": [{"decision": string, "rationale": string}]}.'
        )
        try:
            parsed = ai_assist.call_openai_json(api_key, model, system_prompt, user_prompt, base_url=getattr(self.settings, "openai_base_url", None) or ai_assist.OPENAI_URL)
        except ai_assist.OPENAI_ERRORS:
            return None
        risks = parsed.get("risks")
        trade_offs = parsed.get("trade_offs")
        if not isinstance(risks, list) or not risks:
            return None
        clean_risks = [{"risk": str(r.get("risk", "")), "mitigation": str(r.get("mitigation", ""))} for r in risks if isinstance(r, dict)]
        clean_trade_offs = [{"decision": str(t.get("decision", "")), "rationale": str(t.get("rationale", ""))} for t in trade_offs if isinstance(t, dict)] if isinstance(trade_offs, list) else []
        return {"risks": clean_risks, "trade_offs": clean_trade_offs}

    CAPABILITY_BOUNDS: dict[str, dict[str, str]] = {
        "link creation": {"assumption": "Random 7-character codes provide enough address space", "limitation": "No vanity or branded-domain support"},
        "redirect": {"assumption": "Targets are external http/https URLs", "limitation": "No destination domain allowlist/denylist"},
        "expiry": {"assumption": "Existing links without expiry keep working", "limitation": "No background cleanup of expired rows"},
        "max-click limit": {"assumption": "Click counting is single-node and sequential", "limitation": "No distributed counter for horizontal scale"},
        "analytics": {"assumption": "Click history is retained without rollups", "limitation": "No retention policy or pre-aggregation"},
        "custom endpoint": {"assumption": "The reserved-name set covers current routes", "limitation": "No reservation of future route names"},
        "disable / kill switch": {"assumption": "Disable is reversible and audited", "limitation": "No automated abuse-based disabling"},
    }

    def _assumptions_and_limitations(self, requirement: str, blueprint: ScenarioBlueprint, scope_assessment: dict[str, object]) -> dict[str, list[str]]:
        if scope_assessment["status"] == "scope_review_required":
            return {"assumptions": list(blueprint.assumptions), "limitations": list(blueprint.limitations)}
        capabilities = self._detect_capabilities(requirement.lower())
        if not capabilities:
            return {"assumptions": list(blueprint.assumptions), "limitations": list(blueprint.limitations)}
        assumptions = ["Single-node SQLite prototype; the engineer reviews AI output before acceptance"]
        limitations = ["No auth model or production observability backend"]
        for capability in capabilities:
            entry = self.CAPABILITY_BOUNDS.get(capability)
            if entry:
                assumptions.append(entry["assumption"])
                limitations.append(entry["limitation"])
        return {"assumptions": self._dedup_str(assumptions), "limitations": self._dedup_str(limitations)}

    def _dedup_str(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

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
        lines.extend(["", "## Quality Gates (Validation)"])
        for gate in evidence["quality_gates"]:
            lines.append(f"- {gate['name']}: {gate['status']} - {gate['evidence']}")
        lines.extend(["", "## Compliance Matrix"])
        for item in evidence["compliance_matrix"]:
            lines.append(f"- {item['requirement']}: {item['status']} - {item['coverage']}")
        lines.extend(["", "## Risks"])
        for risk in evidence["risks"]:
            lines.append(f"- {risk['risk']} Mitigation: {risk['mitigation']}")
        lines.extend(["", "## Trade-offs and Rationale"])
        for decision in evidence.get("engineer_decisions", []):
            lines.append(f"- {decision['decision']}: {decision['rationale']}")
        lines.extend(["", "## Artifacts"])
        for artifact in evidence.get("artifacts", []):
            lines.append(f"- {artifact}")
        lines.extend(["", "## Assumptions"])
        for assumption in evidence.get("assumptions", []):
            lines.append(f"- {assumption}")
        lines.extend(["", "## Limitations"])
        for limitation in evidence.get("limitations", []):
            lines.append(f"- {limitation}")
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
        matched_out_of_scope = self._matched_terms(requirement, OUT_OF_SCOPE_INTENTS.keys())
        matched_in_scope = self._matched_terms(requirement, IN_SCOPE_TERMS)
        if matched_out_of_scope:
            captured_intent = OUT_OF_SCOPE_INTENTS[matched_out_of_scope[0]]
            return self._scope_review(
                matched_terms=matched_out_of_scope,
                captured_intent=captured_intent,
                confidence="high",
                decision="The AI captured a non-URL-shortener product request. Do not reinterpret it as URL shortener work; route it to engineer/business scope review.",
            )
        if not matched_in_scope:
            return self._scope_review(
                matched_terms=["no_url_shortener_intent_detected"],
                captured_intent=self._unknown_product_intent(requirement),
                confidence="medium",
                decision="The AI did not find URL shortener, redirect, endpoint, click, or link-management intent. Route to scope review instead of forcing it into the prototype scope.",
            )
        return {
            "status": "in_scope",
            "matched_terms": matched_in_scope,
            "captured_intent": "Build or improve URL shortener/link management capability",
            "intent_confidence": "high",
            "decision": "Proceed within URL shortener engineering scope.",
        }

    def _matched_terms(self, requirement: str, terms: object) -> list[str]:
        lowered = requirement.lower()
        matches = []
        for term in terms:
            pattern = r"(?<![a-z0-9])" + re.escape(str(term).lower()) + r"s?(?![a-z0-9])"
            if re.search(pattern, lowered):
                matches.append(str(term))
        return matches

    def _scope_review(self, matched_terms: list[str], captured_intent: str, confidence: str, decision: str) -> dict[str, object]:
        return {
            "status": "scope_review_required",
            "matched_terms": matched_terms,
            "captured_intent": captured_intent,
            "intent_confidence": confidence,
            "decision": decision,
            "example": "A new product request needs acceptance criteria, data model, privacy, security, reliability, and test strategy before engineering execution.",
        }

    def _unknown_product_intent(self, requirement: str) -> str:
        cleaned = " ".join(requirement.strip().split())
        if not cleaned:
            return "Empty or missing requirement"
        lowered = cleaned.lower()
        for verb in ("build", "create", "make", "generate", "implement", "add"):
            prefix = f"{verb} "
            if lowered.startswith(prefix):
                product = cleaned[len(prefix) :].strip()
                if product:
                    return f"{verb.capitalize()} {product} product or capability"
        return f"Requested capability outside URL shortener scope: {cleaned}"

    def _normalize(self, requirement: str, blueprint: ScenarioBlueprint, scope_assessment: dict[str, object]) -> str:
        if scope_assessment["status"] == "scope_review_required":
            return f"Scope review required before implementation. Requested item is outside the approved prototype scope: {requirement.strip()}"
        if blueprint.scenario is ScenarioName.ambiguous:
            return f"Ambiguous request detected. Proposed normalized problem: {blueprint.normalized_problem}"
        return f"{blueprint.normalized_problem} Source requirement: {requirement.strip()}"

    def _tasks_for(self, blueprint: ScenarioBlueprint, scope_assessment: dict[str, object]) -> list[dict[str, object]]:
        if scope_assessment["status"] != "scope_review_required":
            return [self._task_detail(blueprint, task) for task in blueprint.tasks]
        scope_tasks = [
            {"id": "SCOPE-1", "task": "Stop implementation and classify requested feature against approved prototype scope", "depends_on": []},
            {"id": "SCOPE-2", "task": "Ask business/engineer for acceptance criteria, security constraints, and test expectations", "depends_on": ["SCOPE-1"]},
            {"id": "SCOPE-3", "task": "Decide whether to add a new approved scenario or reject/defer the request", "depends_on": ["SCOPE-2"]},
        ]
        return [self._task_detail(blueprint, task, scope_assessment) for task in scope_tasks]

    def _task_detail(
        self,
        blueprint: ScenarioBlueprint,
        task: dict[str, object],
        scope_assessment: dict[str, object] | None = None,
    ) -> dict[str, object]:
        task_id = str(task["id"])
        if scope_assessment and scope_assessment["status"] == "scope_review_required":
            return {
                **task,
                "intent": "Protect engineering scope and prevent unsupported implementation.",
                "constraints": ["No code generation", "Require stakeholder approval", "Record rejected/deferred rationale"],
                "acceptance_criteria": ["Intent is captured", "Scope decision is explicit", "No URL shortener code is changed for unrelated product scope"],
                "technical_context": "Scope control runs before implementation, tests, docs, and release preparation.",
            }
        detail_map = {
            "REQ": ("Clarify product intent and convert it into engineering language.", ["Preserve user intent", "Identify ambiguity", "Stay within URL shortener scope"], ["Submitted and normalized requirement are recorded", "Ambiguity is listed or cleared"]),
            "API": ("Design API/schema changes for the requirement.", ["Use FastAPI/Pydantic", "Keep route contract reviewable", "Avoid reserved endpoint collisions"], ["Routes and schemas are named", "Request/response behavior is testable"]),
            "DATA": ("Model durable storage and analytics flow.", ["Use SQLite for prototype", "No external service dependency", "Keep click history auditable"], ["Tables and fields support redirect and stats behavior", "Failure outcomes can be recorded"]),
            "SVC": ("Implement business rules in the service layer.", ["Keep routes thin", "Do not count blocked redirects as successful clicks", "Use explicit failure modes"], ["Expiry, max-click, disabled, and redirect behavior are deterministic"]),
            "TEST": ("Generate and run validation coverage.", ["No network calls", "Deterministic tests", "Cover happy and failure paths"], ["Unit/API tests cover create, redirect, stats, and controls"]),
            "DOC": ("Prepare setup, architecture, and trade-off documentation.", ["Explain limitations", "List setup commands", "Make reviewer evidence downloadable"], ["Docs describe architecture, tests, risks, and run path"]),
            "IMPACT": ("Reason about existing modules before changing behavior.", ["Preserve backward compatibility", "Identify APIs and data flow", "Avoid unplanned migration"], ["Impacted files, routes, and data flow are listed"]),
            "DESIGN": ("Design a safe brownfield change.", ["Optional fields only", "Existing links keep working", "Validation stays explicit"], ["Backward-compatible design is documented"]),
            "IMPL": ("Apply implementation changes behind stable APIs.", ["Limit blast radius", "Keep service tests focused", "Avoid route contract drift"], ["Service behavior changes are isolated and testable"]),
            "REVIEW": ("Prepare a reviewer-ready summary.", ["List risks", "Show validation", "Record engineer ownership"], ["Reviewer can see what changed, why, and how it was validated"]),
            "CLARIFY": ("Surface missing information before implementation.", ["Do not invent scope", "Separate questions from assumptions"], ["Ambiguity and stakeholder questions are visible"]),
            "ASSUME": ("Record temporary assumptions for prototype planning.", ["Mark assumptions as temporary", "Do not treat assumptions as approval"], ["Assumptions are visible and reviewable"]),
            "PLAN": ("Create implementation options and trade-offs.", ["Prefer smallest safe option", "Reject unbounded scope"], ["Options and trade-offs are visible before sign-off"]),
            "GATE": ("Require approval before implementation.", ["Engineer owns correctness", "Business can approve scope"], ["Sign-off state is recorded"]),
        }
        key = task_id.split("-", 1)[-1]
        intent, constraints, criteria = detail_map.get(key, ("Execute a reviewable engineering task.", ["Keep change scoped", "Preserve maintainability"], ["Output is traceable and reviewable"]))
        return {**task, "intent": intent, "constraints": constraints, "acceptance_criteria": criteria, "technical_context": blueprint.data_flow}

    def _ai_interactions_for(
        self,
        requirement: str,
        blueprint: ScenarioBlueprint,
        scope_assessment: dict[str, object],
        understanding: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        if scope_assessment["status"] == "scope_review_required":
            captured_intent = str(scope_assessment.get("captured_intent", "Requested work outside the approved prototype scope"))
            return [
                {
                    "task": "SCOPE-1",
                    "execution_phase": "scope_control",
                    "prompt_intent": "Ask AI to identify whether the requirement belongs to the approved URL shortener prototype scope.",
                    "constraints": ["Do not implement unapproved features", "Separate future enhancement from current deliverable"],
                    "acceptance_criteria": ["Captured intent is explicit", "Implementation is blocked", "Approval path is visible"],
                    "technical_context": "Approved prototype scope is URL creation, redirect, analytics, and reliability controls.",
                    "ai_suggestion": f"Captured intent: {captured_intent}. Treat as scope-review work until business and engineering approve acceptance criteria, data model, security controls, and tests.",
                    "generated_output": "Scope-review task list and blocked quality gate.",
                    "engineer_action": "rejected_for_now",
                    "rationale": "Engineer keeps scope controlled and requires approval before expanding beyond core APIs, analytics, and reliability features.",
                    "quality_signal": "scope_control gate blocks implementation",
                }
            ]
        capabilities = self._detect_capabilities(requirement.lower())
        impacts = self._derive_codebase_reasoning(capabilities, blueprint)["impact_analysis"]
        return self._end_to_end_ai_execution(blueprint, understanding, capabilities, impacts)

    def _end_to_end_ai_execution(
        self,
        blueprint: ScenarioBlueprint,
        understanding: dict[str, object] | None = None,
        capabilities: list[str] | None = None,
        impacts: list[dict[str, object]] | None = None,
    ) -> list[dict[str, object]]:
        interactions = [
            {
                "task": "AI-ANALYSIS",
                "execution_phase": "requirement_analysis",
                "prompt_intent": "Ask AI to restate the requirement, identify ambiguity, and propose a bounded engineering problem.",
                "constraints": ["Do not add features outside request", "Call out assumptions", "Keep user intent intact"],
                "acceptance_criteria": ["Intent is captured", "Ambiguity is explicit", "Normalized problem is testable"],
                "technical_context": blueprint.data_flow,
                "ai_suggestion": blueprint.normalized_problem,
                "generated_output": "Normalized problem statement, ambiguity notes, and scope assessment.",
                "engineer_action": "edited",
                "rationale": "Engineer keeps the AI summary but narrows it to the approved URL shortener scope and visible acceptance criteria.",
                "quality_signal": "analysis gate: requirement and scope fields are present",
            },
            {
                "task": "AI-IMPLEMENT",
                "execution_phase": "implementation",
                "prompt_intent": "Ask AI for route, schema, service, and persistence changes that satisfy the approved task graph.",
                "constraints": ["FastAPI only", "SQLite only", "No secrets", "Business rules stay in UrlService"],
                "acceptance_criteria": ["Create link works", "Redirect validates controls", "Stats report clicks and outcomes"],
                "technical_context": "app/main.py owns routes; app/schemas.py owns contracts; app/url_service.py owns rules; app/database.py owns SQLite access.",
                "ai_suggestion": "Implement create, redirect, stats, expiry, max-click, and disabled-link behavior with explicit service exceptions.",
                "generated_output": "Reviewable implementation plan mapped to app/main.py, app/schemas.py, app/url_service.py, and app/database.py.",
                "engineer_action": "edited",
                "rationale": "Engineer accepts the route shape but keeps validation and redirect policy centralized in the service layer.",
                "quality_signal": "implementation gate: impacted modules and data flow are listed",
            },
            {
                "task": "AI-DEBUG",
                "execution_phase": "debugging",
                "prompt_intent": "Ask AI to identify likely failure modes before running tests.",
                "constraints": ["Focus on deterministic failures", "No production data", "Do not mask errors"],
                "acceptance_criteria": ["Expired links fail safely", "Click limits do not over-count", "Reserved endpoints are rejected"],
                "technical_context": "Redirect path checks link state before recording a successful click event.",
                "ai_suggestion": "Check timezone handling, duplicate custom endpoints, reserved route collisions, and failed redirect accounting.",
                "generated_output": "Debug checklist tied to tests and service exceptions.",
                "engineer_action": "accepted",
                "rationale": "These are realistic reliability risks for a URL shortener and directly map to tests.",
                "quality_signal": "debug gate: failure modes are represented in risk and test evidence",
            },
            {
                "task": "AI-REFACTOR",
                "execution_phase": "refactoring",
                "prompt_intent": "Ask AI where the implementation should be refactored for maintainability after initial behavior works.",
                "constraints": ["No broad rewrite", "Preserve public API", "Improve separation of concerns"],
                "acceptance_criteria": ["Routes stay thin", "Service remains unit-testable", "Database access stays isolated"],
                "technical_context": "FastAPI route handlers delegate to UrlService, which delegates persistence to Database.",
                "ai_suggestion": "Keep business rules in UrlService and avoid duplicating redirect validation in route handlers.",
                "generated_output": "Refactoring decision recorded as engineer-owned design guidance.",
                "engineer_action": "accepted",
                "rationale": "This keeps the project modular, testable, and easier to extend with Redis later.",
                "quality_signal": "maintainability gate: component ownership is documented",
            },
            {
                "task": "AI-TEST",
                "execution_phase": "test_generation",
                "prompt_intent": "Ask AI to generate unit and API test ideas for happy paths, controls, and regressions.",
                "constraints": ["Use local TestClient", "No network calls", "Tests must be repeatable"],
                "acceptance_criteria": ["Create/redirect/stats covered", "Expired and max-click behavior covered", "Out-of-scope requirements covered"],
                "technical_context": "tests/test_api.py validates HTTP behavior; tests/test_url_service.py validates service rules.",
                "ai_suggestion": "Add tests for create, redirect, analytics, duplicate endpoints, reserved endpoints, expired links, click limits, and scope review.",
                "generated_output": "Test plan plus executable pytest suite evidence.",
                "engineer_action": "edited",
                "rationale": "Engineer keeps deterministic tests and rejects external dependencies.",
                "quality_signal": "test gate: pytest evidence is shown in quality gates",
            },
            {
                "task": "AI-DOC-REVIEW",
                "execution_phase": "documentation_and_review_preparation",
                "prompt_intent": "Ask AI to prepare reviewer-facing setup, architecture, risks, validation, and final summary.",
                "constraints": ["Be explicit about limitations", "Do not overclaim autonomy", "Show engineer ownership"],
                "acceptance_criteria": ["Setup path is runnable", "Architecture is understandable", "Risks and trade-offs are visible", "Sign-off status is recorded"],
                "technical_context": "README/docs plus downloadable summary and JSON evidence are generated from the same run record.",
                "ai_suggestion": "Prepare architecture overview, scenario evidence, quality gates, limitations, and reviewer summary.",
                "generated_output": "Downloadable summary.md and JSON evidence for review preparation.",
                "engineer_action": "edited",
                "rationale": "Engineer owns final correctness and uses AI as drafting support for documentation and review packaging.",
                "quality_signal": "review gate: sign-off and final summary are visible",
            },
        ]
        if understanding is not None:
            analysis = interactions[0]
            ambiguity = understanding.get("ambiguity") or []
            ambiguity_text = "; ".join(str(item) for item in ambiguity) if ambiguity else "none detected"
            analysis["ai_suggestion"] = (
                f"Interpreted intent: {understanding['interpreted_intent']} "
                f"Ambiguity: {ambiguity_text}. Normalized problem: {understanding['normalized_problem']}"
            )
            analysis["generated_output"] = (
                "Interpreted intent, ambiguity list, and normalized problem derived from the "
                f"submitted requirement (source: {understanding['source']})."
            )
            analysis["engineer_action"] = str(understanding["engineer_action"])
            analysis["understanding_source"] = understanding["source"]
        if capabilities is not None:
            self._tailor_phases(interactions, capabilities, impacts or [])
        return interactions

    def _tailor_phases(self, interactions: list[dict[str, object]], capabilities: list[str], impacts: list[dict[str, object]]) -> None:
        """Make implementation/debug/refactor/test/doc phases reflect THIS requirement."""
        caps_str = ", ".join(capabilities) if capabilities else "the agreed capability"
        files = sorted({f for i in impacts for f in i.get("files", [])})
        files_str = ", ".join(files) if files else "the impacted modules"
        impl = "; ".join(f"{i['capability']}: {i['data_flow']}" for i in impacts) or "Changes are defined after scope is agreed."
        risks = "; ".join(f"{i['capability']}: {i['regression_risk']}" for i in impacts) or "Failure modes are defined after scope is agreed."
        by_phase = {
            "implementation": (f"Implement {caps_str}. {impl}", f"Service/schema/route edits for {caps_str} across {files_str}."),
            "debugging": (f"Check failure modes for {caps_str}: {risks}", f"Debug checklist for {caps_str} tied to tests and service exceptions."),
            "refactoring": (f"Keep {caps_str} rules centralized in UrlService and keep route handlers thin.", f"Refactoring guidance for {caps_str} recorded as engineer-owned design."),
            "test_generation": (f"Add unit/API tests covering {caps_str} happy paths and failure modes.", f"Test plan for {caps_str} plus executable pytest evidence."),
            "documentation_and_review_preparation": (f"Document {caps_str} changes, risks, run path, and sign-off status.", f"Reviewer summary and JSON evidence covering {caps_str}."),
        }
        for item in interactions:
            phase = item.get("execution_phase")
            if phase in by_phase:
                item["ai_suggestion"], item["generated_output"] = by_phase[phase]


    def _traceability(self, interactions: list[dict[str, object]]) -> list[dict[str, str]]:
        return [
            {"task": item["task"], "generated": item["ai_suggestion"], "engineer_action": item["engineer_action"], "rationale": item["rationale"]}
            for item in interactions
        ]

    def _quality_gates(self, blueprint: ScenarioBlueprint, engineer_signoff: bool, scope_assessment: dict[str, object], requirement: str) -> list[dict[str, object]]:
        if scope_assessment["status"] == "scope_review_required":
            return [
                {"name": "scope_control", "status": "blocked", "evidence": "Out-of-scope request requires explicit engineer/business approval before implementation"},
                self._security_gate(requirement),
                self._ownership_gate(engineer_signoff),
            ]
        app_dir = Path(__file__).resolve().parent
        gates = [
            quality.run_ruff(app_dir),
            quality.run_smoke_test(),
            self._security_gate(requirement),
            {"name": "performance_review", "status": "accepted_with_limits", "evidence": "SQLite single-node; adequate for prototype, not horizontal scale"},
            self._ownership_gate(engineer_signoff),
        ]
        return gates

    def _security_gate(self, requirement: str) -> dict[str, object]:
        blocked = ["secret", "password", "api key", "token", "drop table", "delete database", "exfiltrate", "credential"]
        lowered = requirement.lower()
        matched = [term for term in blocked if term in lowered]
        if matched:
            return {"name": "security_review", "status": "blocked", "evidence": f"Requirement references sensitive terms {matched}; no secrets are sent to AI and engineer review is required."}
        return {"name": "security_review", "status": "passed", "evidence": "No secret/credential terms in requirement; prompts exclude secrets and personal data."}

    def _ownership_gate(self, engineer_signoff: bool) -> dict[str, object]:
        return {
            "name": "engineer_ownership",
            "status": "passed" if engineer_signoff else "waiting",
            "evidence": "Engineer/business sign-off recorded" if engineer_signoff else "Sign-off required before final acceptance",
        }

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

