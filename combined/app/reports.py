from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from textwrap import wrap
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

METRIC_EXPLANATIONS = {
    "success_rate": "Percentage of workflow stages that completed successfully. A high value means the agentic workflow is stable.",
    "retry_count": "Number of times a failed stage was tried again before succeeding or stopping.",
    "rollback_count": "Number of times the workflow had to reverse or mark a release unsafe after failure.",
    "fallback_count": "Number of times backup behavior was used when the primary path could not complete.",
    "mttr_seconds": "Mean time to recovery. This shows how long the workflow spent recovering from failures.",
    "end_to_end_latency_seconds": "Total time from workflow start to completion or checkpoint pause.",
    "replans": "Number of times the workflow changed plan because upstream information changed.",
}

SCENARIO_VALUE = {
    "overall": [
        "Shows the complete assessment story in one package: working product, governed SDLC workflow, UI demo, API docs, audit evidence, and metrics.",
        "Useful for the final submission because it connects business value with engineering evidence.",
        "Best demo path: show the UI first, then workflow approval, then CLI retry/replan trace, then PDF evidence.",
    ],
    "greenfield": [
        "Represents building a new system or feature from scratch.",
        "Value: demonstrates requirement normalization, architecture, implementation, testing, documentation, and release readiness in a clean flow.",
        "What to point out: no inherited code risk, so the focus is clear decomposition, quality gates, and release approval.",
    ],
    "brownfield": [
        "Represents changing an existing system where regressions and impacted modules matter.",
        "Value: demonstrates impact analysis, retry recovery, preservation of existing behavior, and safer change management.",
        "What to point out: this scenario is closest to real enterprise work because most production work modifies existing systems.",
    ],
    "ambiguous": [
        "Represents unclear requirements where an agent should not silently guess high-impact scope.",
        "Value: demonstrates clarification, assumption tracking, and dynamic replanning before downstream work continues.",
        "What to point out: ambiguity is treated as a governance issue, not only a product-management issue.",
    ],
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontSize=20, leading=24, spaceAfter=14),
        "h2": ParagraphStyle("Heading2", parent=base["Heading2"], fontSize=13, leading=16, spaceBefore=12, spaceAfter=8),
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontSize=9.5, leading=13, spaceAfter=6),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#475467")),
    }


def _para(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)


def _bullet(text: str, style: ParagraphStyle) -> Paragraph:
    return _para(f"- {text}", style)


def _metric_table(metrics: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    rows = [[_para("Metric", styles["small"]), _para("Value", styles["small"]), _para("What it means", styles["small"])] ]
    for key, value in metrics.items():
        if key in {"started_at", "completed_at"}:
            continue
        explanation = METRIC_EXPLANATIONS.get(key, "Operational evidence captured for audit and reliability review.")
        rows.append([_para(key, styles["small"]), _para(value, styles["small"]), _para(explanation, styles["small"])])
    table = Table(rows, colWidths=[1.65 * inch, 1.1 * inch, 4.0 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F4F1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#134E4A")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D5DD")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_analysis_pdf(scenario: str = "overall") -> Path:
    scenario = scenario.lower()
    if scenario not in SCENARIO_VALUE:
        scenario = "overall"
    path = REPORTS_DIR / f"analysis_{scenario}.pdf"
    styles = _styles()
    story = [
        _para(f"Agentic URL Shortener Analysis Report: {scenario.title()}", styles["title"]),
        _para(f"Generated: {datetime.now(UTC).isoformat()}", styles["small"]),
        _para("Executive Summary", styles["h2"]),
        _para(
            "This report explains what the project demonstrates and why it matters for the Charles Schwab take-home assessment. The URL shortener proves the engineering artifact works. The SDLC workflow proves controlled agentic autonomy with gates, approval, audit evidence, retry/replan behavior, and reliability metrics.",
            styles["body"],
        ),
        _para("Scenario Value", styles["h2"]),
    ]
    story.extend(_bullet(item, styles["body"]) for item in SCENARIO_VALUE[scenario])
    story.extend(
        [
            _para("What Each Major Part Represents", styles["h2"]),
            _bullet("URL shortener UI: the normal-user product experience.", styles["body"]),
            _bullet("FastAPI endpoints: the technical contract that reviewers can inspect in Swagger.", styles["body"]),
            _bullet("SQLite database: durable local storage for links and analytics.", styles["body"]),
            _bullet("DAG workflow: the agentic SDLC model where stages depend on upstream evidence.", styles["body"]),
            _bullet("Human approval checkpoint: controlled autonomy for high-impact release readiness.", styles["body"]),
            _bullet("Audit logs and reports: evidence that every stage, gate, approval, and metric is traceable.", styles["body"]),
            _para("Metrics And Their Meaning", styles["h2"]),
            _metric_table(
                {
                    "success_rate": "100% target in demo",
                    "retry_count": "Shows bounded recovery behavior",
                    "rollback_count": "Shows release safety control",
                    "fallback_count": "Shows backup behavior readiness",
                    "mttr_seconds": "Shows recovery duration",
                    "end_to_end_latency_seconds": "Shows workflow speed",
                    "replans": "Shows dynamic response to changed or ambiguous inputs",
                },
                styles,
            ),
            Spacer(1, 10),
            _para("How To Explain This In The Demo", styles["h2"]),
            _para(
                "The product flow is intentionally simple: create a short endpoint and track analytics. The engineering flow is intentionally governed: agents can prepare work, but release readiness requires evidence and human approval.",
                styles["body"],
            ),
        ]
    )
    _write_pdf(path, story)
    return path


def build_sdlc_pdf_from_run(run: dict[str, Any]) -> Path:
    context = run.get("context", {})
    metrics = context.get("metrics", {})
    node_status = context.get("node_status", {})
    run_id = str(run.get("run_id"))
    scenario = str(context.get("scenario", "workflow"))
    path = REPORTS_DIR / f"sdlc_report_{run_id}.pdf"
    styles = _styles()
    story = [
        _para(f"SDLC Workflow Report: {scenario.title()}", styles["title"]),
        _para(f"Generated: {datetime.now(UTC).isoformat()}", styles["small"]),
        _para(f"Run ID: {run_id}", styles["small"]),
        _para(f"Workflow status: {run.get('status')}", styles["small"]),
        _para("Change Request", styles["h2"]),
        _para(context.get("change_request", "Not provided"), styles["body"]),
        _para("Stage Status", styles["h2"]),
    ]
    for node, status in node_status.items():
        story.append(_bullet(f"{node}: {status} - this records whether the stage passed, failed, or waited for approval.", styles["body"]))
    story.extend([_para("Reliability Metrics", styles["h2"]), _metric_table(metrics, styles), Spacer(1, 10)])
    story.append(_para("Decision Lineage", styles["h2"]))
    decisions = context.get("decision_lineage", [])
    if not decisions:
        story.append(_para("No decision lineage was recorded for this run.", styles["body"]))
    for decision in decisions:
        summary = decision.get("summary", "No summary")
        for line in wrap(summary, width=120):
            story.append(_bullet(f"{decision.get('stage')}: {line}", styles["body"]))
    story.extend(
        [
            _para("Governance Evidence", styles["h2"]),
            _bullet("Entry gates control when stages are allowed to start.", styles["body"]),
            _bullet("Exit gates verify required outputs before downstream work continues.", styles["body"]),
            _bullet("Human approval protects high-impact release readiness decisions.", styles["body"]),
            _bullet("Audit logs and JSON evidence make the workflow reviewable after the fact.", styles["body"]),
            _para("Business Interpretation", styles["h2"]),
            _para(
                "This run shows that the agentic workflow can prepare engineering work, but governance controls decide whether high-impact delivery stages can complete. That is the main difference between a simple automation script and controlled agentic SDLC orchestration.",
                styles["body"],
            ),
        ]
    )
    _write_pdf(path, story)
    return path


def _write_pdf(path: Path, story: list[Any]) -> None:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=path.stem,
    )
    doc.build(story)


def save_json_report(name: str, payload: dict[str, Any]) -> Path:
    path = REPORTS_DIR / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
