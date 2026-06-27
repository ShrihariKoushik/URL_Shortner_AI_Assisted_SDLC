# Combined Agentic URL Shortener Demo

This folder combines the strongest parts of both efforts:

- Working FastAPI URL shortener and analytics product
- Reviewer-friendly UI for normal users
- Swagger API docs for technical reviewers
- CLI-style agentic SDLC trace with audit logs, summaries, retry, replan, and approval evidence
- Downloadable PDF analysis and SDLC reports from the UI

## Run The UI

```powershell
cd C:\Users\shrih\Downloads\dp\cs_codex\combined
uvicorn app.main:app --reload --port 8002
```

Open:

```text
http://127.0.0.1:8002/
```

Technical API docs:

```text
http://127.0.0.1:8002/docs
```

## Run The CLI SDLC Demo

Auto-approve all scenarios:

```powershell
cd C:\Users\shrih\Downloads\dp\cs_codex\combined
python -m run all --auto-approve
```

Interactive approval:

```powershell
python -m run greenfield --interactive
```

Generated run evidence is written to:

```text
combined/runs/{run_id}/audit.jsonl
combined/runs/{run_id}/summary.json
combined/runs/{run_id}/sdlc_report.md
```

## UI Report Downloads

From the UI Docs section:

- Download analysis report
- Download SDLC report after a workflow run
- Download JSON evidence after a workflow run

## Demo Recommendation

1. Show the UI shortener and analytics.
2. Run a UI workflow without auto approval and approve it.
3. Download the analysis and SDLC reports.
4. Show Swagger for API reviewers.
5. Run `python -m run all --auto-approve` to show the enterprise-style trace with retry and replan.

