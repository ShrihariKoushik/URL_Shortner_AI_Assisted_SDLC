# Agentic URL Shortener UI Demo

This folder is an isolated copy of the original take-home project with a reviewer-friendly web console added. The original project in the parent folder is unchanged.

## Run

```bash
cd ui
uvicorn app.main:app --reload --port 8001
```

Open:

- Product UI: http://127.0.0.1:8001/
- API docs: http://127.0.0.1:8001/docs

## Demo Flow

1. Create a short link from the first panel.
2. Open the short URL to prove redirect behavior.
3. Refresh analytics to show click tracking.
4. Run greenfield, brownfield, and ambiguous workflows.
5. Run without auto approval to show human checkpoints.
6. Approve the waiting node from the UI and show reliability metrics.

The copied docs and scenarios remain under `docs/`.
