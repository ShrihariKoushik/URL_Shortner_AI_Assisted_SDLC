import json
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Callable

from app.audit import AuditLogger
from app.llm import LlmClient


class NodeStatus(str, Enum):
    pending = "pending"
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    passed = "passed"
    failed = "failed"
    skipped = "skipped"
    rolled_back = "rolled_back"


class WorkflowStatus(str, Enum):
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    completed = "completed"
    failed = "failed"
    safe_stopped = "safe_stopped"


@dataclass(frozen=True)
class Gate:
    name: str
    predicate: Callable[[dict], bool]
    failure_message: str


@dataclass
class WorkflowNode:
    node_id: str
    name: str
    dependencies: list[str]
    action: Callable[[dict], dict]
    entry_gates: list[Gate] = field(default_factory=list)
    exit_gates: list[Gate] = field(default_factory=list)
    requires_approval: bool = False
    max_retries: int = 1
    fallback: Callable[[dict], dict] | None = None
    rollback: Callable[[dict], dict] | None = None


class SdlcOrchestrator:
    def __init__(self, audit: AuditLogger, llm: LlmClient, require_human_approval: bool = True) -> None:
        self.audit = audit
        self.llm = llm
        self.require_human_approval = require_human_approval
        self.runs: dict[str, dict] = {}

    def start(self, scenario: str, change_request: str | None = None, auto_approve: bool = False) -> dict:
        run_id = str(uuid.uuid4())
        context = {
            "run_id": run_id,
            "scenario": scenario,
            "change_request": change_request or self._default_requirement(scenario),
            "node_status": {},
            "decision_lineage": [],
            "approvals": {},
            "metrics": {
                "started_at": time.time(),
                "completed_at": None,
                "success_count": 0,
                "failure_count": 0,
                "retry_count": 0,
                "rollback_count": 0,
                "fallback_count": 0,
                "mttr_seconds": 0.0,
                "end_to_end_latency_seconds": 0.0,
            },
        }
        self.runs[run_id] = {"status": WorkflowStatus.running.value, "context": context}
        self.audit.record("workflow_started", {"run_id": run_id, "scenario": scenario})
        return self._execute(run_id, auto_approve=auto_approve)

    def approve(self, run_id: str, node_id: str, approved: bool, approver: str, comment: str | None) -> dict:
        run = self._get_run(run_id)
        context = run["context"]
        context["approvals"][node_id] = {
            "approved": approved,
            "approver": approver,
            "comment": comment,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        self.audit.record(
            "approval_recorded",
            {"run_id": run_id, "node_id": node_id, "approved": approved, "approver": approver},
        )
        if not approved:
            run["status"] = WorkflowStatus.safe_stopped.value
            context["node_status"][node_id] = NodeStatus.failed.value
            self.audit.record("workflow_safe_stopped", {"run_id": run_id, "node_id": node_id})
            return self._public(run_id)
        return self._execute(run_id, auto_approve=False)

    def get(self, run_id: str) -> dict:
        self._get_run(run_id)
        return self._public(run_id)

    def _execute(self, run_id: str, auto_approve: bool) -> dict:
        run = self._get_run(run_id)
        context = run["context"]
        graph = self._build_graph(context["scenario"])
        ready = self._topological_batches(graph)

        for batch in ready:
            for node_id in batch:
                if context["node_status"].get(node_id) == NodeStatus.passed.value:
                    continue
                node = graph[node_id]
                if not self._dependencies_passed(node, context):
                    continue
                approval = context["approvals"].get(node_id)
                if node.requires_approval and self.require_human_approval and not auto_approve and not approval:
                    context["node_status"][node_id] = NodeStatus.waiting_for_approval.value
                    run["status"] = WorkflowStatus.waiting_for_approval.value
                    self.audit.record("approval_required", {"run_id": run_id, "node_id": node_id})
                    return self._public(run_id)
                if approval and not approval["approved"]:
                    run["status"] = WorkflowStatus.safe_stopped.value
                    return self._public(run_id)
                self._run_node(node, context)
                if context["node_status"][node_id] != NodeStatus.passed.value:
                    run["status"] = WorkflowStatus.failed.value
                    self._finish_metrics(context)
                    return self._public(run_id)

        run["status"] = WorkflowStatus.completed.value
        self._finish_metrics(context)
        self.audit.record("workflow_completed", {"run_id": run_id, "scenario": context["scenario"]})
        return self._public(run_id)

    def _run_node(self, node: WorkflowNode, context: dict) -> None:
        context["node_status"][node.node_id] = NodeStatus.running.value
        self.audit.record("node_started", {"run_id": context["run_id"], "node_id": node.node_id})
        started = time.time()

        for gate in node.entry_gates:
            if not gate.predicate(context):
                self._fail_node(node, context, gate.failure_message, started)
                return

        for attempt in range(node.max_retries + 1):
            try:
                output = node.action(context)
                context.update(output)
                for gate in node.exit_gates:
                    if not gate.predicate(context):
                        raise ValueError(gate.failure_message)
                context["node_status"][node.node_id] = NodeStatus.passed.value
                context["metrics"]["success_count"] += 1
                self.audit.record("node_passed", {"run_id": context["run_id"], "node_id": node.node_id})
                return
            except Exception as exc:
                if attempt < node.max_retries:
                    context["metrics"]["retry_count"] += 1
                    self.audit.record(
                        "node_retry",
                        {"run_id": context["run_id"], "node_id": node.node_id, "error": str(exc)},
                    )
                    continue
                if node.fallback:
                    context["metrics"]["fallback_count"] += 1
                    context.update(node.fallback(context))
                    context["node_status"][node.node_id] = NodeStatus.passed.value
                    self.audit.record("node_fallback_used", {"run_id": context["run_id"], "node_id": node.node_id})
                    return
                self._fail_node(node, context, str(exc), started)
                if node.rollback:
                    context["metrics"]["rollback_count"] += 1
                    context.update(node.rollback(context))
                    context["node_status"][node.node_id] = NodeStatus.rolled_back.value
                return

    def _fail_node(self, node: WorkflowNode, context: dict, reason: str, started: float) -> None:
        context["node_status"][node.node_id] = NodeStatus.failed.value
        context["metrics"]["failure_count"] += 1
        context["metrics"]["mttr_seconds"] += time.time() - started
        self.audit.record(
            "node_failed",
            {"run_id": context["run_id"], "node_id": node.node_id, "reason": reason},
        )

    def _build_graph(self, scenario: str) -> dict[str, WorkflowNode]:
        nodes = [
            WorkflowNode(
                "requirements",
                "Requirement understanding",
                [],
                self._requirements,
                exit_gates=[Gate("clear_problem", lambda c: bool(c.get("normalized_requirement")), "Requirement was not normalized")],
                max_retries=1,
                fallback=self._requirements_fallback,
            ),
            WorkflowNode(
                "architecture",
                "Architecture and risk design",
                ["requirements"],
                self._architecture,
                entry_gates=[Gate("requirements_passed", lambda c: c["node_status"].get("requirements") == "passed", "Requirements incomplete")],
                exit_gates=[Gate("has_controls", lambda c: bool(c.get("guardrails")), "Guardrails missing")],
            ),
            WorkflowNode("implementation", "Implementation plan", ["architecture"], self._implementation),
            WorkflowNode("tests", "Validation strategy", ["architecture"], self._tests),
            WorkflowNode(
                "security",
                "Security and compliance policy",
                ["architecture"],
                self._security,
                exit_gates=[Gate("no_critical_security_findings", lambda c: not c.get("critical_security_findings"), "Critical security finding")],
            ),
            WorkflowNode("docs", "Documentation", ["implementation", "tests"], self._docs),
            WorkflowNode(
                "release",
                "Release readiness",
                ["implementation", "tests", "security", "docs"],
                self._release,
                requires_approval=True,
                exit_gates=[Gate("validated", lambda c: c.get("release_ready") is True, "Release readiness failed")],
                rollback=self._release_rollback,
            ),
        ]
        if scenario == "ambiguous":
            nodes.insert(
                1,
                WorkflowNode(
                    "clarification",
                    "Ambiguity clarification",
                    ["requirements"],
                    self._clarification,
                    requires_approval=True,
                    exit_gates=[Gate("ambiguity_resolved", lambda c: c.get("ambiguity_resolved") is True, "Ambiguity unresolved")],
                ),
            )
            for node in nodes:
                if node.node_id == "architecture":
                    node.dependencies = ["clarification"]
        if scenario == "brownfield":
            nodes.insert(1, WorkflowNode("impact_analysis", "Brownfield impact analysis", ["requirements"], self._impact))
            for node in nodes:
                if node.node_id == "architecture":
                    node.dependencies = ["impact_analysis"]
        return {node.node_id: node for node in nodes}

    def _requirements(self, context: dict) -> dict:
        decision = self.llm.analyze_requirement(context["change_request"])
        context["decision_lineage"].append(
            {"stage": "requirements", "summary": decision.summary, "assumptions": decision.assumptions, "risks": decision.risks}
        )
        return {"normalized_requirement": decision.summary, "assumptions": decision.assumptions, "risks": decision.risks}

    def _requirements_fallback(self, context: dict) -> dict:
        return {"normalized_requirement": context["change_request"], "assumptions": ["Fallback normalization used"], "risks": []}

    def _clarification(self, context: dict) -> dict:
        return {
            "ambiguity_resolved": True,
            "clarifications": [
                "Default retention is indefinite for the prototype.",
                "Analytics scope is click count and last accessed timestamp.",
            ],
        }

    def _impact(self, context: dict) -> dict:
        return {
            "impacted_modules": ["app/url_service.py", "app/database.py", "app/main.py", "tests/"],
            "data_flow": "POST /shorten writes urls; GET /{slug} resolves and increments analytics; GET /stats/{slug} reads metrics.",
        }

    def _architecture(self, context: dict) -> dict:
        return {
            "architecture_decisions": [
                "FastAPI boundary with a small service layer for testability.",
                "SQLite as durable local persistence; Redis can be introduced behind the same service boundary.",
                "Audit events are append-only JSONL for traceability.",
            ],
            "guardrails": ["bounded retries", "approval before release", "safe-stop on rejection", "policy gate before release"],
        }

    def _implementation(self, context: dict) -> dict:
        return {"implementation_artifacts": ["FastAPI routes", "SQLite migrations", "URL service", "workflow orchestrator"]}

    def _tests(self, context: dict) -> dict:
        return {"validation": ["unit tests for URL service", "API integration tests", "orchestrator gate and approval tests"]}

    def _security(self, context: dict) -> dict:
        return {
            "critical_security_findings": [],
            "security_controls": ["validated URL inputs", "custom slug allowlist", "no secret logging", "audit event minimization"],
        }

    def _docs(self, context: dict) -> dict:
        return {"documentation": ["README", "architecture overview", "scenario playbooks"]}

    def _release(self, context: dict) -> dict:
        return {"release_ready": True, "release_summary": "All SDLC gates passed with human approval checkpoint satisfied."}

    def _release_rollback(self, context: dict) -> dict:
        return {"release_ready": False, "rollback_summary": "Release candidate marked unavailable after failed readiness gate."}

    def _topological_batches(self, graph: dict[str, WorkflowNode]) -> list[list[str]]:
        indegree = {node_id: len(node.dependencies) for node_id, node in graph.items()}
        children = defaultdict(list)
        for node in graph.values():
            for dependency in node.dependencies:
                children[dependency].append(node.node_id)
        queue = deque([node_id for node_id, degree in indegree.items() if degree == 0])
        batches: list[list[str]] = []
        while queue:
            batch = list(queue)
            batches.append(batch)
            queue.clear()
            for node_id in batch:
                for child in children[node_id]:
                    indegree[child] -= 1
                    if indegree[child] == 0:
                        queue.append(child)
        return batches

    def _dependencies_passed(self, node: WorkflowNode, context: dict) -> bool:
        return all(context["node_status"].get(dependency) == NodeStatus.passed.value for dependency in node.dependencies)

    def _default_requirement(self, scenario: str) -> str:
        defaults = {
            "greenfield": "Build a production-grade URL shortener with create, redirect, analytics, and reliability controls.",
            "brownfield": "Enhance an existing URL shortener with analytics and reliability metrics while preserving API behavior.",
            "ambiguous": "Make links smarter and safer, but keep the product simple.",
        }
        return defaults.get(scenario, defaults["greenfield"])

    def _finish_metrics(self, context: dict) -> None:
        metrics = context["metrics"]
        metrics["completed_at"] = time.time()
        metrics["end_to_end_latency_seconds"] = round(metrics["completed_at"] - metrics["started_at"], 4)
        total = metrics["success_count"] + metrics["failure_count"]
        metrics["success_rate"] = 1.0 if total == 0 else round(metrics["success_count"] / total, 4)

    def _public(self, run_id: str) -> dict:
        run = self._get_run(run_id)
        return json.loads(json.dumps({"run_id": run_id, **run}))

    def _get_run(self, run_id: str) -> dict:
        if run_id not in self.runs:
            raise KeyError(run_id)
        return self.runs[run_id]

