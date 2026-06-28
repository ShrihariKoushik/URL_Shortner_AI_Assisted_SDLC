# URL Shortener AI-Assisted SDLC

Production-grade prototype for engineer-led, AI-assisted software delivery: a URL shortener that turns a requirement into a reviewable engineering outcome.

The runnable project is in [`ai_assisted_shortener`](./ai_assisted_shortener).

Live app: https://cs-url.onrender.com

Live API docs: https://cs-url.onrender.com/docs

## Deliverables

- Working FastAPI + SQLite URL shortener, runnable end to end.
- Architecture overview covering components, tools, execution approach, control flow, and key decisions.
- Three review scenarios: greenfield, brownfield, and ambiguous.
- AI-assisted execution evidence with requirement understanding, decomposition, codebase reasoning, traceability, quality gates, risk controls, and sign-off.
- Generated implementation package flow with preview/download, isolated workspace, validation, and rollback safety.
- Setup instructions, testing approach, limitations, and trade-offs.
- GitHub Pages reviewer guide with screenshots in [`docs/index.html`](./docs/index.html).

## Quick Start

```powershell
cd ai_assisted_shortener
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Open:

- UI: http://127.0.0.1:8010/
- API docs: http://127.0.0.1:8010/docs
- Health: http://127.0.0.1:8010/health

## Optional AI Configuration

The system runs without an API key using deterministic fallback logic. To use a real OpenAI-compatible model:

```powershell
cd ai_assisted_shortener
copy .env.example .env
# edit .env and set AI_SHORTENER_OPENAI_API_KEY
```

Default model: `gpt-4.1`.

## Validation

```powershell
cd ai_assisted_shortener
python -m pytest -q
python -m ruff check .
```

## Review Flow

1. Create a short link in the UI.
2. Open `/docs` to show API/schema definitions.
3. Run Greenfield, Brownfield, and Ambiguous scenarios in the Engineering section.
4. Approve as Engineer or Business to show controlled oversight.
5. Build a real implementation package and open the generated UI preview.
6. Download summary/evidence artifacts for review.

## Live Deployment

- Reviewer site: GitHub Pages from `/docs` on the `main` branch.
- Live FastAPI app: Render at `https://cs-url.onrender.com`.
- API docs: `https://cs-url.onrender.com/docs`.

## GitHub Pages

The static reviewer page lives in [`docs/index.html`](./docs/index.html). In GitHub, enable Pages from the `main` branch and `/docs` folder.

