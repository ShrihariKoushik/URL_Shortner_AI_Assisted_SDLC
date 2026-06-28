# AI-Assisted URL Shortener

A working prototype for an engineer-led AI-assisted software engineering assessment.

This project demonstrates how a requirement becomes a reviewable engineering outcome while keeping the engineer responsible for correctness, maintainability, validation, and final approval. AI is modeled as an accelerator inside tasks, not as an autonomous SDLC owner.

## What It Includes

- FastAPI URL shortener service
- SQLite persistence
- Create, redirect, analytics, disable, expiry, and max-click controls
- Static reviewer UI
- AI-assisted engineering evidence for greenfield, brownfield, and ambiguous requirements
- Task decomposition with dependencies
- Codebase reasoning for brownfield changes
- Prompt/AI suggestion/engineer action traceability
- Quality gates, risks, assumptions, limitations, and sign-off
- Unit and integration tests

## Run

```powershell
cd ai_assisted_shortener
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Open:

http://127.0.0.1:8010/

API docs:

http://127.0.0.1:8010/docs

## Test

```powershell
cd ai_assisted_shortener
python -m pytest -q
python -m ruff check .
```

## Demo Flow

1. Create a short link in the Shortener section.
2. Open the generated short URL to trigger redirect analytics.
3. Refresh stats to show clicks and last outcome.
4. In Engineering, choose Greenfield, Brownfield, or Ambiguous.
5. Toggle Engineer sign-off.
6. Click Generate engineering outcome.
7. Show requirement understanding, task decomposition, AI traceability, quality gates, and summary download.

## Important Framing

This is not autonomous orchestration. It demonstrates AI-assisted engineering execution:

- Engineer defines task intent, constraints, context, and acceptance criteria.
- AI suggestions are recorded as generated, edited, accepted, or rejected.
- Engineer owns correctness and final sign-off.
- Quality gates include analysis, linting, tests, security review, and trade-off review.
