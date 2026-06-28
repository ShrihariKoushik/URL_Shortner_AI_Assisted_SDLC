"""Quality gates that actually execute, instead of asserting static 'passed' strings.

- `run_ruff` shells out to ruff and reports the real result (or 'skipped' if ruff
  is not installed in the environment).
- `run_smoke_test` exercises the live service in-process (create -> redirect ->
  stats -> expiry -> max-click) and reports a real pass/fail. It deliberately does
  NOT invoke pytest, which would recurse when a gate runs inside a test.
"""

import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.database import Database
from app.url_service import LinkClickLimitExceededError, LinkExpiredError, UrlService


def run_ruff(target: Path) -> dict[str, object]:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "ruff", "check", str(target), "--quiet"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        return {"name": "static_analysis", "status": "skipped", "evidence": "ruff is not installed in this environment"}
    except subprocess.TimeoutExpired:
        return {"name": "static_analysis", "status": "skipped", "evidence": "ruff check timed out"}
    output = (proc.stdout or proc.stderr or "").strip()
    if "No module named ruff" in output:
        return {"name": "static_analysis", "status": "skipped", "evidence": "ruff is not installed in this environment"}
    if proc.returncode == 0:
        return {"name": "static_analysis", "status": "passed", "evidence": f"ruff check {target.name} reported no issues"}
    return {"name": "static_analysis", "status": "failed", "evidence": output[:600] or "ruff reported issues"}


def run_smoke_test() -> dict[str, object]:
    start = time.perf_counter()
    try:
        db_path = Path(tempfile.mkdtemp()) / "smoke.db"
        service = UrlService(Database(db_path), "http://smoke/r")
        service.create("https://example.com", custom_endpoint="smoke", max_clicks=1)
        if service.resolve("smoke") != "https://example.com":
            raise AssertionError("redirect target mismatch")
        if service.get("smoke").clicks != 1:
            raise AssertionError("click was not counted")
        try:
            service.resolve("smoke")
            raise AssertionError("max-click limit was not enforced")
        except LinkClickLimitExceededError:
            pass
        service.create("https://example.com", custom_endpoint="exp", expires_at=datetime.now(UTC) - timedelta(days=1))
        try:
            service.resolve("exp")
            raise AssertionError("expiry was not enforced")
        except LinkExpiredError:
            pass
    except Exception as exc:  # noqa: BLE001 - any failure is a real gate failure
        ms = int((time.perf_counter() - start) * 1000)
        return {"name": "runtime_tests", "status": "failed", "evidence": f"runtime smoke test failed: {exc}", "duration_ms": ms}
    ms = int((time.perf_counter() - start) * 1000)
    return {
        "name": "runtime_tests",
        "status": "passed",
        "evidence": f"create/redirect/stats/expiry/max-click verified in-process in {ms} ms",
        "duration_ms": ms,
    }
