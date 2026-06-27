import difflib
import json
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


@dataclass(frozen=True)
class ChangeTemplate:
    feature_id: str
    title: str
    trigger_terms: tuple[str, ...]
    normalized_requirement: str
    tasks: list[dict[str, object]]
    impacted_files: list[str]
    before_service: str
    after_service: str
    test_file: str


LINK_EXPIRY_TEMPLATE = ChangeTemplate(
    feature_id="link_expiry",
    title="Add link expiry support",
    trigger_terms=("expiry", "expire", "expiration", "ttl"),
    normalized_requirement="Add optional expiry timestamps to short links and block redirects after expiry.",
    impacted_files=["url_service.py", "test_url_service.py", "README.md"],
    tasks=[
        {
            "id": "REQ-1",
            "stage": "requirements",
            "task": "Normalize request into optional expires_at behavior for shortened URLs.",
            "depends_on": [],
        },
        {
            "id": "BRN-1",
            "stage": "impact_analysis",
            "task": "Identify service and validation paths affected by redirect-time expiry checks.",
            "depends_on": ["REQ-1"],
        },
        {
            "id": "IMP-1",
            "stage": "implementation",
            "task": "Extend create/resolve behavior with expires_at storage and ExpiredLinkError.",
            "depends_on": ["BRN-1"],
        },
        {
            "id": "TST-1",
            "stage": "tests",
            "task": "Add tests for active links, expired links, and no-expiry default behavior.",
            "depends_on": ["IMP-1"],
        },
        {
            "id": "DOC-1",
            "stage": "documentation",
            "task": "Document expiry semantics and release notes for reviewers.",
            "depends_on": ["TST-1"],
        },
    ],
    before_service=dedent(
        '''
        from dataclasses import dataclass
        from datetime import datetime, timezone


        @dataclass
        class ShortLink:
            slug: str
            target_url: str
            created_at: datetime
            clicks: int = 0


        class UrlService:
            def __init__(self) -> None:
                self.links: dict[str, ShortLink] = {}

            def create(self, slug: str, target_url: str) -> ShortLink:
                link = ShortLink(slug=slug, target_url=target_url, created_at=datetime.now(timezone.utc))
                self.links[slug] = link
                return link

            def resolve(self, slug: str) -> str:
                link = self.links[slug]
                link.clicks += 1
                return link.target_url
        '''
    ).strip()
    + "\n",
    after_service=dedent(
        '''
        from dataclasses import dataclass
        from datetime import datetime, timezone


        class ExpiredLinkError(Exception):
            pass


        @dataclass
        class ShortLink:
            slug: str
            target_url: str
            created_at: datetime
            expires_at: datetime | None = None
            clicks: int = 0

            def is_expired(self, now: datetime | None = None) -> bool:
                if self.expires_at is None:
                    return False
                current_time = now or datetime.now(timezone.utc)
                return current_time >= self.expires_at


        class UrlService:
            def __init__(self) -> None:
                self.links: dict[str, ShortLink] = {}

            def create(self, slug: str, target_url: str, expires_at: datetime | None = None) -> ShortLink:
                link = ShortLink(
                    slug=slug,
                    target_url=target_url,
                    created_at=datetime.now(timezone.utc),
                    expires_at=expires_at,
                )
                self.links[slug] = link
                return link

            def resolve(self, slug: str, now: datetime | None = None) -> str:
                link = self.links[slug]
                if link.is_expired(now):
                    raise ExpiredLinkError(f"short link '{slug}' has expired")
                link.clicks += 1
                return link.target_url
        '''
    ).strip()
    + "\n",
    test_file=dedent(
        '''
        from datetime import datetime, timedelta, timezone

        import pytest

        from url_service import ExpiredLinkError, UrlService


        def test_link_without_expiry_resolves_and_tracks_clicks():
            service = UrlService()
            service.create("abc", "https://example.com")

            assert service.resolve("abc") == "https://example.com"
            assert service.links["abc"].clicks == 1


        def test_unexpired_link_resolves_before_deadline():
            service = UrlService()
            now = datetime(2026, 6, 27, tzinfo=timezone.utc)
            service.create("offer", "https://schwab.com", expires_at=now + timedelta(days=1))

            assert service.resolve("offer", now=now) == "https://schwab.com"


        def test_expired_link_is_blocked_and_not_counted():
            service = UrlService()
            now = datetime(2026, 6, 27, tzinfo=timezone.utc)
            service.create("old", "https://schwab.com", expires_at=now - timedelta(seconds=1))

            with pytest.raises(ExpiredLinkError):
                service.resolve("old", now=now)
            assert service.links["old"].clicks == 0
        '''
    ).strip()
    + "\n",
)


MAX_CLICK_TEMPLATE = ChangeTemplate(
    feature_id="max_click_limit",
    title="Add max-click limit support",
    trigger_terms=("max click", "click limit", "limited clicks", "maximum clicks"),
    normalized_requirement="Add optional maximum-click limits and block redirects after the limit is reached.",
    impacted_files=["url_service.py", "test_url_service.py", "README.md"],
    tasks=[
        {"id": "REQ-1", "stage": "requirements", "task": "Define optional max_clicks behavior.", "depends_on": []},
        {"id": "IMP-1", "stage": "implementation", "task": "Track max_clicks and enforce before redirect.", "depends_on": ["REQ-1"]},
        {"id": "TST-1", "stage": "tests", "task": "Validate unlimited, below-limit, and exhausted links.", "depends_on": ["IMP-1"]},
        {"id": "DOC-1", "stage": "documentation", "task": "Document click-limit behavior.", "depends_on": ["TST-1"]},
    ],
    before_service=LINK_EXPIRY_TEMPLATE.before_service,
    after_service=dedent(
        '''
        from dataclasses import dataclass
        from datetime import datetime, timezone


        class ClickLimitExceededError(Exception):
            pass


        @dataclass
        class ShortLink:
            slug: str
            target_url: str
            created_at: datetime
            max_clicks: int | None = None
            clicks: int = 0

            def exhausted(self) -> bool:
                return self.max_clicks is not None and self.clicks >= self.max_clicks


        class UrlService:
            def __init__(self) -> None:
                self.links: dict[str, ShortLink] = {}

            def create(self, slug: str, target_url: str, max_clicks: int | None = None) -> ShortLink:
                link = ShortLink(slug=slug, target_url=target_url, created_at=datetime.now(timezone.utc), max_clicks=max_clicks)
                self.links[slug] = link
                return link

            def resolve(self, slug: str) -> str:
                link = self.links[slug]
                if link.exhausted():
                    raise ClickLimitExceededError(f"short link '{slug}' exhausted its click limit")
                link.clicks += 1
                return link.target_url
        '''
    ).strip()
    + "\n",
    test_file=dedent(
        '''
        import pytest

        from url_service import ClickLimitExceededError, UrlService


        def test_link_without_limit_resolves_multiple_times():
            service = UrlService()
            service.create("abc", "https://example.com")

            assert service.resolve("abc") == "https://example.com"
            assert service.resolve("abc") == "https://example.com"


        def test_limited_link_resolves_until_limit():
            service = UrlService()
            service.create("once", "https://schwab.com", max_clicks=1)

            assert service.resolve("once") == "https://schwab.com"
            with pytest.raises(ClickLimitExceededError):
                service.resolve("once")
        '''
    ).strip()
    + "\n",
)


TEMPLATES = (LINK_EXPIRY_TEMPLATE, MAX_CLICK_TEMPLATE)


class ChangeExecutor:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parents[1] / "change_runs"

    def execute(self, requirement: str, auto_approve: bool = False) -> dict:
        started = time.time()
        template = self._select_template(requirement)
        run_id = str(uuid.uuid4())
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        status = "completed" if auto_approve else "waiting_for_approval"
        approval = {
            "required": not auto_approve,
            "checkpoint": "apply_code_patch",
            "reason": "Code-changing action requires human approval in governed mode.",
            "approved": auto_approve,
        }

        if not auto_approve:
            result = self._base_result(run_id, requirement, template, status, approval, started)
            self._write_evidence(run_dir, result)
            return result

        src = run_dir / "url_service.py"
        test = run_dir / "test_url_service.py"
        readme = run_dir / "README.md"
        src.write_text(template.before_service, encoding="utf-8")
        before = src.read_text(encoding="utf-8")
        src.write_text(template.after_service, encoding="utf-8")
        test.write_text(template.test_file, encoding="utf-8")
        readme.write_text(
            f"# Change Execution Evidence\n\nRequirement: {requirement}\n\nImplemented: {template.normalized_requirement}\n",
            encoding="utf-8",
        )

        diff = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                template.after_service.splitlines(keepends=True),
                fromfile="before/url_service.py",
                tofile="after/url_service.py",
            )
        )
        test_result = self._run_tests(run_dir)
        completed = time.time()
        result = self._base_result(run_id, requirement, template, status, approval, started)
        result.update(
            {
                "status": "completed" if test_result["passed"] else "failed",
                "patch": {
                    "applied": True,
                    "files_changed": template.impacted_files,
                    "diff": diff,
                    "workspace": str(run_dir),
                },
                "validation": test_result,
                "metrics": {
                    **result["metrics"],
                    "completed_at": completed,
                    "end_to_end_latency_seconds": round(completed - started, 4),
                    "success_rate": 1.0 if test_result["passed"] else 0.0,
                },
            }
        )
        self._write_evidence(run_dir, result)
        return result

    def _base_result(
        self,
        run_id: str,
        requirement: str,
        template: ChangeTemplate,
        status: str,
        approval: dict[str, object],
        started: float,
    ) -> dict:
        return {
            "run_id": run_id,
            "status": status,
            "requirement": requirement,
            "classification": self._classify(requirement),
            "normalized_requirement": template.normalized_requirement,
            "selected_template": template.feature_id,
            "title": template.title,
            "tasks": template.tasks,
            "impacted_files": template.impacted_files,
            "approval": approval,
            "policy_guardrails": [
                "Only approved change templates can execute code changes.",
                "Execution happens in an isolated generated workspace.",
                "Tests must pass before release evidence is marked successful.",
                "Human approval is required before applying code in governed mode.",
            ],
            "patch": {"applied": False, "files_changed": [], "diff": "", "workspace": ""},
            "validation": {"passed": False, "command": "not run", "stdout": "", "stderr": "", "returncode": None},
            "metrics": {
                "started_at": started,
                "completed_at": None,
                "success_rate": 0.0,
                "retry_count": 0,
                "rollback_count": 0,
                "fallback_count": 0,
                "mttr_seconds": 0.0,
                "end_to_end_latency_seconds": 0.0,
            },
        }

    def _select_template(self, requirement: str) -> ChangeTemplate:
        normalized = requirement.lower()
        for template in TEMPLATES:
            if any(term in normalized for term in template.trigger_terms):
                return template
        return LINK_EXPIRY_TEMPLATE

    def _classify(self, requirement: str) -> str:
        lowered = requirement.lower()
        if any(word in lowered for word in ("existing", "enhance", "bug", "fix", "refactor")):
            return "brownfield"
        if any(word in lowered for word in ("maybe", "something", "smart", "better", "unclear")):
            return "ambiguous"
        return "greenfield"

    def _run_tests(self, run_dir: Path) -> dict:
        command = [sys.executable, "-m", "pytest", "-q", str(run_dir)]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        return {
            "passed": completed.returncode == 0,
            "command": " ".join(command),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
        }

    def _write_evidence(self, run_dir: Path, result: dict) -> None:
        (run_dir / "evidence.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
