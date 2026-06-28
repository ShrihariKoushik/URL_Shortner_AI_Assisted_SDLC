# Architecture Overview

## Components

- `app/main.py`: FastAPI application and HTTP API boundary.
- `app/schemas.py`: Pydantic request and response schemas.
- `app/database.py`: SQLite setup and connection management.
- `app/url_service.py`: Core shortener business logic.
- `app/engineering.py`: AI-assisted engineering evidence generation.
- `app/static/`: Reviewer UI.
- `tests/`: Unit and API tests.

## Control Flow

### URL Shortener

1. `POST /api/links` receives target URL and optional controls.
2. Pydantic validates URL, endpoint, expiry, and max-click fields.
3. `UrlService.create()` writes a link row to SQLite.
4. `GET /r/{code}` resolves the short code.
5. Service checks disabled, expired, and click-limit states before redirecting.
6. Click events are recorded for both successful and blocked outcomes.
7. `GET /api/links/{code}/stats` returns analytics.

## AI-Assisted Execution Model

The system stores review evidence for each engineering scenario:

- Requirement understanding
- Ambiguity analysis
- Task decomposition with dependencies
- Brownfield impact analysis
- AI prompt intent and constraints
- AI suggestion
- Engineer action: accepted, edited, or rejected
- Engineer rationale
- Quality gates
- Risks and mitigations
- Final summary

## Key Decisions

- SQLite keeps setup simple and reviewable.
- `/r/{code}` avoids collisions with `/api`, `/docs`, `/static`, and engineering routes.
- Failed redirects do not increment successful click count, but click events record blocked outcomes.
- AI is represented through traceable task-level assistance records, not hidden autonomy.
- Engineer sign-off is required to mark outcomes review-ready.

## Security and Control

- Custom endpoint allowlist blocks unsafe characters.
- Reserved route names cannot be used as short codes.
- No secret or personal data is sent to AI in this prototype.
- Ambiguous requirements are stopped until assumptions/sign-off are recorded.
