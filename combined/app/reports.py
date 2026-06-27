from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def build_analysis_report() -> str:
    return "\n".join(
        [
            "# Agentic URL Shortener Analysis Report",
            "",
            f"Generated: {datetime.now(UTC).isoformat()}",
            "",
            "## Executive Summary",
            "This combined version merges a working FastAPI URL shortener, reviewer-friendly UI, and CLI-style agentic SDLC trace. The URL shortener proves the engineering artifact works end-to-end. The orchestrator proves governed autonomy through DAG stages, entry/exit gates, human approval checkpoints, retries, replanning, audit logs, and reliability metrics.",
            "",
            "## What The System Demonstrates",
            "- Working product: shorten URLs, redirect by slug, and track analytics.",
            "- Agentic SDLC: requirement understanding, design, implementation, testing, documentation, and release readiness.",
            "- Governance: entry gates, exit gates, high-risk approval checkpoint, bounded retry, rollback hook, and safe-stop behavior.",
            "- Observability: JSONL audit events, run summaries, decision lineage, and reliability metrics.",
            "- Scenario coverage: greenfield, brownfield, and ambiguous requests.",
            "",
            "## Why This Combination Is Stronger",
            "The UI helps non-technical reviewers understand the product and workflow visually. The API docs help technical reviewers inspect endpoints. The CLI runner gives audit-grade trace output similar to enterprise SDLC automation logs.",
            "",
            "## Trade-offs",
            "- SQLite is used for local durability; Redis can be added behind the service boundary for scale.",
            "- Human approval is modeled in the app and CLI; production would integrate identity, RBAC, and ticketing.",
            "- The CLI runner creates deterministic demo artifacts; production agents would execute real worker tasks and attach richer evidence.",
            "",
            "## Recommended Demo Order",
            "1. Show the UI shortener and analytics.",
            "2. Run a workflow without auto approval and approve it.",
            "3. Show Brownfield retry and Ambiguous replan from the CLI.",
            "4. Download this analysis report and an SDLC report from the UI.",
            "5. Open Swagger for technical API review.",
            "",
            "## Interview Positioning",
            "The project is a Python FastAPI URL shortener wrapped in a governed agentic SDLC orchestration system with DAG workflow, gates, approvals, audit logs, retries, rollback hooks, replanning, and reliability metrics.",
            "",
        ]
    )


def build_sdlc_report_from_run(run: dict[str, Any]) -> str:
    context = run.get("context", {})
    metrics = context.get("metrics", {})
    node_status = context.get("node_status", {})
    lines = [
        "# SDLC Workflow Report",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Run ID: `{run.get('run_id')}`",
        f"Status: `{run.get('status')}`",
        f"Scenario: `{context.get('scenario')}`",
        "",
        "## Change Request",
        str(context.get("change_request", "Not provided")),
        "",
        "## Node Status",
    ]
    for node, status in node_status.items():
        lines.append(f"- `{node}`: {status}")
    lines.extend(["", "## Decision Lineage"])
    for decision in context.get("decision_lineage", []):
        lines.append(f"- `{decision.get('stage')}`: {decision.get('summary')}")
    lines.extend(["", "## Reliability Metrics"])
    for key, value in metrics.items():
        if key not in {"started_at", "completed_at"}:
            lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Governance Evidence",
            "- Entry and exit gates control stage execution.",
            "- Human approval checkpoints protect high-impact release actions.",
            "- Audit logging records workflow and approval events.",
            "- Metrics track reliability, retries, fallback, rollback, MTTR, and latency.",
            "",
            "## Assumptions And Limitations",
            "- This is a local prototype using SQLite.",
            "- Approval is represented through API/UI/CLI interactions rather than enterprise identity workflow.",
            "- OpenAI API usage is optional and falls back to deterministic analysis when no key is set.",
            "",
        ]
    )
    return "\n".join(lines)


def save_report(name: str, content: str) -> Path:
    path = REPORTS_DIR / name
    path.write_text(content, encoding="utf-8")
    return path


def save_json_report(name: str, payload: dict[str, Any]) -> Path:
    path = REPORTS_DIR / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
