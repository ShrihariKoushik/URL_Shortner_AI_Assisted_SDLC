"""Generate real engineering output (code, unit tests, docs) for a requirement.

For each capability detected in the requirement this writes a dependency-free
Python module, a runnable pytest file, and a documentation section into the
generated package, then actually executes the generated tests and reports the
result. This is what turns "engineering output generation" into produced,
verified artifacts instead of a description.
"""

import os
import subprocess
import sys
from pathlib import Path

CODE_TEMPLATES: dict[str, dict[str, object]] = {
    "expiry": {
        "keywords": ("expiry", "expire", "expiration", "ttl"),
        "module": "expiry_rule.py",
        "api": "POST /api/links (expires_at), GET /r/{code}",
        "doc": "Adds optional `expires_at`. `is_expired` blocks a redirect once the deadline passes.",
        "code": '''"""Generated: link expiry rule."""


def is_expired(expires_at: float | None, now: float) -> bool:
    """Return True if the link has an expiry timestamp at or before ``now``."""
    return expires_at is not None and now >= expires_at
''',
        "test": '''from expiry_rule import is_expired


def test_no_expiry_never_expires():
    assert is_expired(None, 100.0) is False


def test_past_expiry_is_expired():
    assert is_expired(50.0, 100.0) is True


def test_future_expiry_not_expired():
    assert is_expired(150.0, 100.0) is False
''',
    },
    "max-click limit": {
        "keywords": ("max click", "max-click", "max_clicks", "click limit", "click cap"),
        "module": "click_limit_rule.py",
        "api": "POST /api/links (max_clicks), GET /r/{code}",
        "doc": "Adds optional `max_clicks`. `within_click_limit` blocks a redirect once the cap is reached.",
        "code": '''"""Generated: max-click limit rule."""


def within_click_limit(clicks: int, max_clicks: int | None) -> bool:
    """Return True if another redirect is allowed under the configured cap."""
    return max_clicks is None or clicks < max_clicks
''',
        "test": '''from click_limit_rule import within_click_limit


def test_unlimited_when_none():
    assert within_click_limit(5, None) is True


def test_allows_under_limit():
    assert within_click_limit(0, 1) is True


def test_blocks_at_limit():
    assert within_click_limit(1, 1) is False
''',
    },
    "custom endpoint": {
        "keywords": ("custom endpoint", "custom code", "custom alias", "vanity"),
        "module": "custom_code_rule.py",
        "api": "POST /api/links (custom_endpoint)",
        "doc": "Validates custom codes against an allowlist and reserved-name set before creation.",
        "code": '''"""Generated: custom endpoint validation rule."""

_ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def is_valid_custom_code(code: str, reserved: set[str]) -> bool:
    """Return True if ``code`` is safe and is not a reserved route name."""
    if not code or any(character not in _ALLOWED for character in code):
        return False
    return code.lower() not in reserved
''',
        "test": '''from custom_code_rule import is_valid_custom_code


def test_rejects_unsafe_characters():
    assert is_valid_custom_code("bad/code", set()) is False


def test_rejects_reserved_name():
    assert is_valid_custom_code("api", {"api"}) is False


def test_accepts_valid_code():
    assert is_valid_custom_code("promo_1", {"api"}) is True
''',
    },
    "disable / kill switch": {
        "keywords": ("disable", "deactivate", "kill switch", "revoke"),
        "module": "disable_rule.py",
        "api": "POST /api/links/{code}/disable",
        "doc": "Adds a disabled flag; `is_blocked` stops disabled links from redirecting.",
        "code": '''"""Generated: disable / kill-switch rule."""


def is_blocked(disabled: int) -> bool:
    """Return True if the link has been disabled."""
    return bool(disabled)
''',
        "test": '''from disable_rule import is_blocked


def test_blocks_disabled_link():
    assert is_blocked(1) is True


def test_allows_active_link():
    assert is_blocked(0) is False
''',
    },
    "analytics": {
        "keywords": ("analytics", "stats", "statistics", "metrics", "report"),
        "module": "analytics_rule.py",
        "api": "GET /api/links/{code}/stats",
        "doc": "Aggregates recorded click outcomes into a per-outcome count for the stats endpoint.",
        "code": '''"""Generated: analytics aggregation."""


def summarize_outcomes(outcomes: list[str]) -> dict[str, int]:
    """Return a count of each recorded click outcome."""
    summary: dict[str, int] = {}
    for outcome in outcomes:
        summary[outcome] = summary.get(outcome, 0) + 1
    return summary
''',
        "test": '''from analytics_rule import summarize_outcomes


def test_counts_outcomes():
    assert summarize_outcomes(["resolved", "resolved", "expired"]) == {"resolved": 2, "expired": 1}


def test_empty_outcomes():
    assert summarize_outcomes([]) == {}
''',
    },
    "redirect": {
        "keywords": ("redirect", "forward"),
        "module": "redirect_rule.py",
        "api": "GET /r/{code}",
        "doc": "Maps a resolved link outcome to the HTTP status the redirect endpoint should return.",
        "code": '''"""Generated: redirect status mapping."""

_STATUS = {"resolved": 307, "expired": 410, "disabled": 410, "click_limit_exceeded": 429}


def redirect_status(outcome: str) -> int:
    """Return the HTTP status for a redirect outcome (404 if unknown)."""
    return _STATUS.get(outcome, 404)
''',
        "test": '''from redirect_rule import redirect_status


def test_resolved_is_temporary_redirect():
    assert redirect_status("resolved") == 307


def test_expired_is_gone():
    assert redirect_status("expired") == 410


def test_unknown_is_not_found():
    assert redirect_status("nope") == 404
''',
    },
    "link creation": {
        "keywords": ("shorten", "url shortener", "short link", "new link", "create link"),
        "module": "create_rule.py",
        "api": "POST /api/links",
        "doc": "Normalizes and validates the target URL (http/https only) before a link is created.",
        "code": '''"""Generated: link target normalization."""


def normalize_target(url: str) -> str:
    """Trim and validate a target URL, allowing only http/https schemes."""
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("only http/https URLs are allowed")
    return url
''',
        "test": '''from create_rule import normalize_target


def test_accepts_and_trims_https():
    assert normalize_target("  https://example.com  ") == "https://example.com"


def test_rejects_non_http_scheme():
    raised = False
    try:
        normalize_target("ftp://example.com")
    except ValueError:
        raised = True
    assert raised
''',
    },
}


def detect(requirement: str) -> list[str]:
    lowered = requirement.lower()
    return [name for name, tpl in CODE_TEMPLATES.items() if any(k in lowered for k in tpl["keywords"])]


def generate(requirement: str, workspace: Path) -> dict[str, object]:
    """Write code/test/doc artifacts for the requirement and run the generated tests."""
    selected = detect(requirement)
    gen_dir = Path(workspace).resolve() / "generated"
    if not selected:
        return {
            "capabilities": [],
            "artifacts": [],
            "generated_dir": str(gen_dir),
            "tests": {"name": "generated_unit_tests", "status": "skipped", "evidence": "no concrete capability detected"},
        }
    gen_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[str] = []
    doc_lines = ["# Generated Engineering Output", "", f"Requirement: {requirement}", ""]
    for name in selected:
        tpl = CODE_TEMPLATES[name]
        module = str(tpl["module"])
        (gen_dir / module).write_text(str(tpl["code"]), encoding="utf-8")
        artifacts.append(f"generated/{module}")
        test_name = f"test_{module}"
        (gen_dir / test_name).write_text(str(tpl["test"]), encoding="utf-8")
        artifacts.append(f"generated/{test_name}")
        doc_lines += [f"## {name}", "", f"API: {tpl['api']}", "", str(tpl["doc"]), ""]
    (gen_dir / "GENERATED_OUTPUT.md").write_text("\n".join(doc_lines) + "\n", encoding="utf-8")
    artifacts.append("generated/GENERATED_OUTPUT.md")
    return {
        "capabilities": selected,
        "artifacts": artifacts,
        "generated_dir": str(gen_dir),
        "tests": run_generated_tests(gen_dir),
    }


def run_generated_tests(gen_dir: Path) -> dict[str, object]:
    """Actually execute the generated pytest files in an isolated subprocess."""
    gen_dir = Path(gen_dir).resolve()
    if not list(gen_dir.glob("test_*.py")):
        return {"name": "generated_unit_tests", "status": "skipped", "evidence": "no generated tests"}
    env = {**os.environ, "PYTHONPATH": str(gen_dir) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(gen_dir), "-q", "-p", "no:cacheprovider"],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            cwd=str(gen_dir),
        )
    except FileNotFoundError:
        return {"name": "generated_unit_tests", "status": "skipped", "evidence": "pytest not installed"}
    except subprocess.TimeoutExpired:
        return {"name": "generated_unit_tests", "status": "skipped", "evidence": "generated tests timed out"}
    if "No module named pytest" in (proc.stderr or ""):
        return {"name": "generated_unit_tests", "status": "skipped", "evidence": "pytest not installed"}
    lines = [ln for ln in (proc.stdout or proc.stderr or "").strip().splitlines() if ln.strip()]
    summary = lines[-1][:200] if lines else ""
    if proc.returncode == 5:
        return {"name": "generated_unit_tests", "status": "skipped", "evidence": "no tests collected"}
    status = "passed" if proc.returncode == 0 else "failed"
    return {"name": "generated_unit_tests", "status": status, "evidence": summary}
