import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib import error, request

from app import codegen
from app.config import Settings


@dataclass(frozen=True)
class ImplementationResult:
    run_id: str
    status: str
    workspace_path: str
    zip_path: str
    used_openai: bool
    security_review: dict[str, object]
    tasks: list[dict[str, object]]
    files_changed: list[str]
    report: str
    validation: dict[str, object]


class SecureImplementationService:
    def __init__(self, project_root: Path, settings: Settings) -> None:
        self.project_root = project_root
        self.settings = settings
        self.generated_root = settings.generated_workspace_root

    def execute(self, requirement: str, engineer_signoff: bool, approval_role: str | None) -> dict[str, object]:
        run_id = str(uuid.uuid4())
        security_review = self._security_review(requirement, engineer_signoff, approval_role)
        workspace = self.generated_root / run_id
        workspace.mkdir(parents=True, exist_ok=True)

        if security_review["status"] != "passed":
            result = self._blocked_result(run_id, workspace, security_review)
            self._write_manifest(result)
            return result.__dict__

        ai_plan = self._ai_plan(requirement)
        tasks = self._tasks(requirement, ai_plan)
        attempts: list[dict[str, object]] = []
        for attempt in range(1, 3):
            files_changed = self._generate_files(requirement, workspace, tasks, ai_plan)
            validation = self._validate_generated(requirement, workspace, files_changed)
            attempts.append({"attempt": attempt, "validation_status": validation["status"]})
            if validation["status"] == "passed":
                break
            ai_plan = self._ai_replan(requirement, ai_plan, validation)
        validation["attempts"] = attempts
        codegen_result = codegen.generate(requirement, workspace)
        for artifact in codegen_result["artifacts"]:
            if artifact not in files_changed:
                files_changed.append(artifact)
        validation["generated_artifacts"] = codegen_result["artifacts"]
        validation["generated_tests"] = codegen_result["tests"]
        if codegen_result["tests"]["status"] == "failed":
            validation["status"] = "failed"
        status = "implementation_package_ready" if validation["status"] == "passed" else "implementation_package_needs_fixes"
        report = self._report(requirement, security_review, tasks, files_changed, ai_plan, validation)
        (workspace / "IMPLEMENTATION_REPORT.md").write_text(report, encoding="utf-8")
        (workspace / "VALIDATION.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
        zip_path = self._zip_workspace(workspace)
        result = ImplementationResult(
            run_id=run_id,
            status=status,
            workspace_path=str(workspace),
            zip_path=str(zip_path),
            used_openai=ai_plan["used_openai"],
            security_review=security_review,
            tasks=tasks,
            files_changed=files_changed,
            report=report,
            validation=validation,
        )
        self._write_manifest(result)
        return result.__dict__

    def _validate_generated(self, requirement: str, workspace: Path, files_changed: list[str]) -> dict[str, object]:
        """Run real checks against the generated package instead of assuming success."""
        checks: list[dict[str, object]] = []
        static_dir = workspace / "app" / "static"
        for name in ("index.html", "app.js", "styles.css"):
            path = static_dir / name
            checks.append({"check": f"{name} generated and non-empty", "passed": path.exists() and path.stat().st_size > 0})
        index_text = (static_dir / "index.html").read_text(encoding="utf-8") if (static_dir / "index.html").exists() else ""
        app_js = (static_dir / "app.js").read_text(encoding="utf-8") if (static_dir / "app.js").exists() else ""
        lowered = requirement.lower()
        if "remove" in lowered and "expiry" in lowered:
            checks.append({"check": "Expiry control removed from UI", "passed": "Expiry" not in index_text and "expiresAt" not in app_js})
        if "remove" in lowered and ("max click" in lowered or "max clicks" in lowered or "max_clicks" in lowered):
            checks.append({"check": "Max-click control removed from UI", "passed": "Max clicks" not in index_text and "maxClicks" not in app_js})
        for py_file in workspace.rglob("*.py"):
            try:
                compile(py_file.read_text(encoding="utf-8"), str(py_file), "exec")
                checks.append({"check": f"{py_file.name} compiles", "passed": True})
            except SyntaxError as exc:
                checks.append({"check": f"{py_file.name} compiles", "passed": False, "detail": str(exc)})
        passed = all(bool(c["passed"]) for c in checks)
        return {"status": "passed" if passed else "failed", "checks": checks}

    def _ai_replan(self, requirement: str, ai_plan: dict[str, object], validation: dict[str, object]) -> dict[str, object]:
        """Single corrective pass. Re-asks OpenAI with the validation failures; no-op offline."""
        api_key = self.settings.resolved_openai_api_key
        if not api_key or not ai_plan.get("used_openai"):
            return ai_plan
        failed = [c for c in validation.get("checks", []) if not c.get("passed")]
        feedback = "Previous attempt failed these checks: " + json.dumps(failed)
        return self._ai_plan(requirement, correction=feedback)


    def _security_review(self, requirement: str, engineer_signoff: bool, approval_role: str | None) -> dict[str, object]:
        lowered = requirement.lower()
        blocked_terms = ["delete database", "drop table", "exfiltrate", "secret", "password", "api key", "token"]
        matched = [term for term in blocked_terms if term in lowered]
        if matched:
            return {
                "status": "blocked",
                "matched_terms": matched,
                "decision": "Blocked before AI execution because the request may expose secrets or damage data.",
                "approval_role": approval_role,
            }
        if not engineer_signoff:
            return {
                "status": "waiting_for_engineer_signoff",
                "matched_terms": [],
                "decision": "High-impact code generation requires engineer approval before creating implementation files.",
                "approval_role": approval_role,
            }
        return {
            "status": "passed",
            "matched_terms": [],
            "decision": "Safe to generate a separate implementation package. Live application files will not be modified.",
            "approval_role": approval_role or "Engineer",
        }

    def _ai_plan(self, requirement: str, correction: str | None = None) -> dict[str, object]:
        fallback = {
            "used_openai": False,
            "model": self.settings.openai_model,
            "summary": "Local secure planner used because no OpenAI API key was available or the API call failed.",
            "steps": [
                "Analyze requested UI/code change.",
                "Create isolated generated workspace.",
                "Generate modified files and implementation report.",
                "Package output as a zip for review and rollback.",
            ],
            "generated_files": {},
        }
        api_key = self.settings.resolved_openai_api_key
        if not api_key:
            return fallback

        source_static = self.project_root / "app" / "static"
        current_files = {
            "app/static/index.html": (source_static / "index.html").read_text(encoding="utf-8"),
            "app/static/app.js": (source_static / "app.js").read_text(encoding="utf-8"),
            "app/static/styles.css": (source_static / "styles.css").read_text(encoding="utf-8"),
        }
        payload = {
            "model": self.settings.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a secure senior software engineer. Return JSON only. "
                        "Generate a reviewable implementation package for this existing FastAPI URL shortener UI. "
                        "Do not include secrets. Do not call external services. Do not modify files outside the allowlist."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Requirement:\n"
                        f"{requirement}\n\n"
                        "Allowed files: app/static/index.html, app/static/app.js, app/static/styles.css.\n"
                        "Return JSON with this shape: "
                        "{\"summary\": string, \"steps\": string[], \"files\": {path: full_file_content}}.\n"
                        "Only include files that need changes. The preview must run through the current FastAPI app.\n\n"
                        + (f"Correction from a failed validation attempt: {correction}\n\n" if correction else "")
                        + f"Current files:\n{json.dumps(current_files)}"
                    ),
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        try:
            req = request.Request(
                self.settings.openai_base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=45) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            generated = self._parse_ai_json(content)
            files = self._allowed_generated_files(generated.get("files", {}))
            return {
                "used_openai": True,
                "model": self.settings.openai_model,
                "summary": str(generated.get("summary") or "OpenAI generated an implementation package.")[:1200],
                "steps": generated.get("steps") if isinstance(generated.get("steps"), list) else fallback["steps"],
                "generated_files": files,
            }
        except (OSError, KeyError, json.JSONDecodeError, error.HTTPError, TypeError, ValueError):
            return fallback

    def _parse_ai_json(self, content: str) -> dict[str, object]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("AI response must be a JSON object")
        return parsed

    def _allowed_generated_files(self, files: object) -> dict[str, str]:
        if not isinstance(files, dict):
            return {}
        allowed = {"app/static/index.html", "app/static/app.js", "app/static/styles.css"}
        generated: dict[str, str] = {}
        for path, content in files.items():
            if path in allowed and isinstance(content, str):
                generated[path] = content
        return generated
    def _tasks(self, requirement: str, ai_plan: dict[str, object]) -> list[dict[str, object]]:
        return [
            {
                "id": "SEC-1",
                "task": "Run secure request review before code generation",
                "depends_on": [],
                "status": "completed",
                "generated": "Security gate result and allowed workspace boundary.",
                "engineer_action": "approved",
                "rationale": "Generated files are isolated from the live app and no secrets are written.",
            },
            {
                "id": "PLAN-1",
                "task": "Split requirement into implementation steps",
                "depends_on": ["SEC-1"],
                "status": "completed",
                "generated": ai_plan["summary"],
                "engineer_action": "edited" if ai_plan["used_openai"] else "accepted",
                "rationale": "Engineer keeps the change bounded to a reviewable generated package.",
            },
            {
                "id": "CODE-1",
                "task": "Generate changed files in isolated workspace",
                "depends_on": ["PLAN-1"],
                "status": "completed",
                "generated": "Modified UI files and implementation report.",
                "engineer_action": "generated_for_review",
                "rationale": "Reviewer can inspect or copy generated files without losing the original app.",
            },
        ]

    def _generate_files(self, requirement: str, workspace: Path, tasks: list[dict[str, object]], ai_plan: dict[str, object]) -> list[str]:
        app_static = workspace / "app" / "static"
        app_static.mkdir(parents=True, exist_ok=True)
        source_static = self.project_root / "app" / "static"
        index_text = (source_static / "index.html").read_text(encoding="utf-8")
        app_js = (source_static / "app.js").read_text(encoding="utf-8")
        styles_text = (source_static / "styles.css").read_text(encoding="utf-8")

        generated_files = ai_plan.get("generated_files", {})
        if isinstance(generated_files, dict) and generated_files:
            index_text = str(generated_files.get("app/static/index.html", index_text))
            app_js = str(generated_files.get("app/static/app.js", app_js))
            styles_text = str(generated_files.get("app/static/styles.css", styles_text))
            files_changed = list(generated_files.keys())
        else:
            index_text, app_js, files_changed = self._local_ui_transform(requirement, index_text, app_js)

        if not files_changed:
            files_changed = ["IMPLEMENTATION_REPORT.md"]
        (app_static / "index.html").write_text(index_text, encoding="utf-8")
        (app_static / "app.js").write_text(app_js, encoding="utf-8")
        (app_static / "styles.css").write_text(styles_text, encoding="utf-8")
        (workspace / "TASKS.json").write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        (workspace / "AI_PLAN.json").write_text(json.dumps(ai_plan, indent=2), encoding="utf-8")
        return files_changed

    def _local_ui_transform(self, requirement: str, index_text: str, app_js: str) -> tuple[str, str, list[str]]:
        lowered = requirement.lower()
        files_changed: list[str] = []
        removes_ui = "remove" in lowered and "ui" in lowered
        if removes_ui and "expiry" in lowered:
            index_text = index_text.replace('            <label>Expiry <input id="expiresAt" type="datetime-local" /></label>\n', "")
            app_js = app_js.replace('  const expiresValue = byId("expiresAt").value;\n', "")
            app_js = app_js.replace('        expires_at: expiresValue ? new Date(expiresValue).toISOString() : null,\n', '        expires_at: null,\n')
            files_changed = self._mark_changed(files_changed, ["app/static/index.html", "app/static/app.js"])
        if removes_ui and ("max clicks" in lowered or "max click" in lowered or "max_clicks" in lowered):
            index_text = index_text.replace('            <label>Max clicks <input id="maxClicks" type="number" min="1" max="1000000" placeholder="optional" /></label>\n', "")
            app_js = app_js.replace('  const maxClicks = byId("maxClicks").value;\n', "")
            app_js = app_js.replace('        max_clicks: maxClicks ? Number(maxClicks) : null,\n', '        max_clicks: null,\n')
            files_changed = self._mark_changed(files_changed, ["app/static/index.html", "app/static/app.js"])
        return index_text, app_js, files_changed

    def _mark_changed(self, current: list[str], additions: list[str]) -> list[str]:
        for item in additions:
            if item not in current:
                current.append(item)
        return current
    def _report(self, requirement: str, security_review: dict[str, object], tasks: list[dict[str, object]], files_changed: list[str], ai_plan: dict[str, object], validation: dict[str, object] | None = None) -> str:
        lines = [
            "# Generated Implementation Package",
            "",
            f"Requirement: {requirement}",
            f"Created at: {datetime.now(UTC).isoformat()}",
            f"OpenAI used: {ai_plan['used_openai']}",
            "",
            "## Security Review",
            json.dumps(security_review, indent=2),
            "",
            "## Files Changed",
        ]
        lines.extend(f"- {item}" for item in files_changed)
        lines.extend(["", "## Tasks"])
        for task in tasks:
            lines.append(f"- {task['id']}: {task['task']} ({task['status']}) - {task['rationale']}")
        if validation is not None:
            lines.extend(["", "## Validation", f"Status: {validation['status']}"])
            for check in validation.get("checks", []):
                mark = "PASS" if check.get("passed") else "FAIL"
                lines.append(f"- [{mark}] {check['check']}")
            if validation.get("attempts"):
                lines.append(f"Attempts: {validation['attempts']}")
        lines.extend(["", "## Rollback / Recovery", "The live application was not modified. Delete this generated workspace or ignore it to roll back."])
        return "\n".join(lines) + "\n"

    def _blocked_result(self, run_id: str, workspace: Path, security_review: dict[str, object]) -> ImplementationResult:
        report = self._report("Blocked before implementation", security_review, [], [], {"used_openai": False, "summary": "blocked", "steps": [], "model": self.settings.openai_model})
        (workspace / "IMPLEMENTATION_REPORT.md").write_text(report, encoding="utf-8")
        zip_path = self._zip_workspace(workspace)
        return ImplementationResult(run_id, security_review["status"], str(workspace), str(zip_path), False, security_review, [], [], report, {"status": "skipped", "checks": []})

    def _zip_workspace(self, workspace: Path) -> Path:
        zip_base = workspace.with_suffix("")
        zip_file = shutil.make_archive(str(zip_base), "zip", workspace)
        return Path(zip_file)

    def _write_manifest(self, result: ImplementationResult) -> None:
        Path(result.workspace_path).mkdir(parents=True, exist_ok=True)
        (Path(result.workspace_path) / "manifest.json").write_text(json.dumps(result.__dict__, indent=2), encoding="utf-8")

