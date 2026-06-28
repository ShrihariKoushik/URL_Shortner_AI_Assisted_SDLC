# Architecture Overview

## Purpose

The project is a working prototype that turns a software requirement into a
**reviewable engineering outcome** using engineer-led, AI-assisted execution. It
pairs a production-style FastAPI URL shortener with an engineering-evidence
engine that, for any submitted requirement, derives the understanding, task
plan, codebase impact, AI-assisted execution record, quality gates, risks, and a
downloadable final summary. The engineer leads and approves; AI accelerates work
inside tasks but is never an autonomous owner.

## Components

- `app/main.py` — FastAPI application and HTTP boundary (shortener, engineering, implementation routes).
- `app/schemas.py` — Pydantic request/response contracts, including per-step engineer actions.
- `app/config.py` — settings (DB path, sign-off policy, AI provider/base URL/model/key).
- `app/database.py` — SQLite setup and connection management.
- `app/url_service.py` — core shortener business logic (create, resolve, expiry, max-click, disable, stats).
- `app/engineering.py` — requirement-driven evidence engine: understanding, task decomposition, codebase reasoning, AI-assisted execution phases, quality gates, risk register, assumptions/limitations, and the markdown summary.
- `app/ai_assist.py` — minimal helper that calls any OpenAI-compatible Chat Completions endpoint and returns JSON.
- `app/quality.py` — **executable** quality gates: a real `ruff` subprocess and an in-process runtime smoke test of the service.
- `app/implementation.py` — generates an isolated implementation package, validates it, and retries once with feedback on the AI path.
- `app/codegen.py` — generates real code/schema modules, runnable pytest files, and docs for the requirement, then executes the generated tests.
- `app/static/` — reviewer UI.
- `tests/` — unit and integration tests.

## Tools

- **FastAPI / Uvicorn** for the service and API.
- **Pydantic / pydantic-settings** for validation and configuration.
- **SQLite** for durable, reviewable local persistence.
- **pytest** for unit and integration tests; **ruff** for static analysis.
- **Any OpenAI-compatible LLM** (OpenAI, DeepSeek, Meta Llama hosts, Claude via gateway) selected through `.env`. See `.env.example`.

## Execution Approach

Every evidence dimension is **derived from the actual requirement text**, not
fixed per scenario:

1. If an API key is configured, the relevant step calls the LLM for a JSON result.
2. If no key is set, or the call fails, a **deterministic capability-based engine**
   produces the same structured output. This keeps the system fully runnable
   offline and makes tests deterministic.

"Capabilities" (link creation, redirect, expiry, max-click limit, analytics,
custom endpoint, disable) are detected from the requirement and drive
decomposition, codebase impact, risks, assumptions/limitations, and the
per-phase AI execution record. The engineer's notes are folded into this
detection, so engineer guidance changes what the AI works on.

## Control Flow

### URL shortener

1. `POST /api/links` validates the URL, custom endpoint, expiry, and max-click fields, then writes a link row.
2. `GET /r/{code}` resolves the code, checks disabled/expired/click-limit state, records the outcome, and 307-redirects on success.
3. `GET /api/links/{code}/stats` returns analytics; `POST /api/links/{code}/disable` is a kill switch.

### Engineering evidence (`POST /engineering/execute`)

Requirement → scope assessment → requirement understanding (intent, ambiguity,
normalized problem) → task decomposition (with dependencies) → codebase reasoning
(impacted files/APIs/data flow/regression risk) → AI-assisted execution across
six SDLC phases → **executed** quality gates → risk register and trade-offs →
assumptions/limitations → final summary. The run is persisted and downloadable
as JSON or `summary.md`. Sign-off and approval role gate the final status.

### Implementation package (`POST /implementation/execute`)

Security review (blocks secret/destructive terms) → sign-off gate → AI or local
generation of UI changes → **validation** of the generated package (files exist,
the requested change applied, generated tests run) → corrective retry on the AI
path → code/test/doc artifacts generated and their tests executed → zipped,
isolated package with a report and `VALIDATION.json`. The live application is
never modified.

## Quality Gates and Validation

Gates are executed at request time, not asserted:

- `static_analysis` runs `ruff` as a subprocess (reports `skipped` honestly if ruff is absent).
- `runtime_tests` exercises create → redirect → stats → expiry → max-click in-process and reports a measured duration.
- `security_review` is computed from the requirement and blocks sensitive terms.
- `engineer_ownership` passes only when sign-off is recorded.

## Security and Control

- Custom-endpoint allowlist blocks unsafe characters; reserved route names cannot be used as short codes.
- The security gate and the implementation security review block secret/credential/destructive terms before any AI call.
- No secrets or personal data are placed in prompts; the provider key lives only in `.env` (gitignored).
- Out-of-scope requests (e.g. "build Facebook clone", QR codes) are routed to scope review, not silently implemented.
- Engineer sign-off is required for high-impact code generation; without it, no implementation files are produced.

## Key Decisions

- **SQLite over Redis** for a durable, simple, reviewable prototype; the service layer keeps a clean seam for swapping later.
- **`/r/{code}` prefix** avoids collisions with `/api`, `/docs`, `/static`, engineering, and implementation routes.
- **Failed redirects are not counted as successful clicks**, but every outcome is recorded in `click_events` for audit.
- **AI is represented through traceable, task-level assistance** with explicit engineer accept/edit/reject — not hidden autonomy.
- **Deterministic fallback** mirrors the AI output shape so the system is reviewable and testable without network access.
- **OpenAI-compatible base URL** makes the model provider a configuration choice rather than a code change.
