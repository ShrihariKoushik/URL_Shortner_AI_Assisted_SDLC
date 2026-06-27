# Agentic URL Shortener

Production-grade take-home prototype for a Charles Schwab agentic software engineering assessment. The project combines a runnable FastAPI URL shortener with an agentic SDLC orchestration layer that demonstrates DAG-based execution, gates, human approvals, audit logging, retry/fallback, rollback hooks, and reliability metrics.

## Features

- Create short URLs with optional custom slugs.
- Redirect short URLs and track click analytics.
- SQLite persistence for local durability.
- OpenAI-backed requirement analysis when `OPENAI_API_KEY` is configured.
- Deterministic fallback when no API key is present, so the demo remains runnable.
- Agentic SDLC workflow endpoints for greenfield, brownfield, and ambiguous scenarios.
- Append-only audit log at `./data/audit.log`.

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open API docs at `http://localhost:8000/docs`.

## URL Shortener API

Create a URL:

```bash
curl -X POST http://localhost:8000/shorten ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://example.com\",\"custom_slug\":\"demo\"}"
```

Use the short URL:

```bash
curl -i http://localhost:8000/demo
```

View analytics:

```bash
curl http://localhost:8000/stats/demo
```

## Agentic SDLC API

Run a greenfield workflow and pause at the human release checkpoint:

```bash
curl -X POST http://localhost:8000/agent/scenarios/greenfield/run ^
  -H "Content-Type: application/json" ^
  -d "{\"auto_approve\":false}"
```

Approve the release node:

```bash
curl -X POST http://localhost:8000/agent/runs/{run_id}/approve/release ^
  -H "Content-Type: application/json" ^
  -d "{\"approved\":true,\"approver\":\"reviewer\",\"comment\":\"approved for demo\"}"
```

Run all gates without pausing:

```bash
curl -X POST http://localhost:8000/agent/scenarios/brownfield/run ^
  -H "Content-Type: application/json" ^
  -d "{\"auto_approve\":true}"
```

## Testing

```bash
pytest
ruff check .
```

## Deliverables Map

- Working prototype: `app/main.py`, `app/url_service.py`, `app/database.py`
- Orchestration model: `app/orchestrator.py`
- Architecture overview: `docs/ARCHITECTURE.md`
- Greenfield, brownfield, ambiguous scenarios: `docs/SCENARIOS.md`
- Tests: `tests/`

## Assumptions and Trade-offs

- SQLite is used for the take-home prototype because it is portable and reviewable. Redis can be added behind the service boundary for high-volume redirect counters or cache-backed slug lookups.
- The orchestrator executes synchronous Python callables for determinism in tests. In production, the same DAG contract can dispatch work to queues or separate agent workers.
- Human approval is modeled as an API checkpoint. A production deployment would integrate identity, RBAC, signed approvals, and ticketing.
- The OpenAI API is optional to avoid making local evaluation dependent on secrets or network availability.

