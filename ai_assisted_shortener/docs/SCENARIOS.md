# Scenarios

Each scenario is run from the **Engineering** section of the UI (or
`POST /engineering/execute`). Pick the scenario, enter the requirement and
optional engineer notes, generate without approval to see the gated state, then
approve as Engineer or Business to produce the reviewable outcome. Every run
returns decomposition, execution, and validation, and can be downloaded as
`summary.md` or JSON.

The outputs below are from the deterministic (offline) engine so they are
reproducible without an API key; with a key configured, the same fields are
produced by the LLM and edited by the engineer.

## Greenfield

**Requirement:** "Build a URL shortener service from scratch with create,
redirect, analytics, expiry, max-click limits, tests, and documentation."

- **Decomposition:** capabilities detected (link creation, redirect, analytics,
  expiry, max-click limit) produce a sequenced task graph — `T-REQ` →
  `T-DATA` → `T-CREATE` / `T-REDIRECT` / `T-EXPIRY` / `T-MAXCLICK` / `T-STATS`
  → `T-TEST` → `T-DOC`, each with `depends_on` and acceptance criteria.
- **Execution:** the six AI phases (requirement analysis, implementation,
  debugging, refactoring, test generation, documentation/review) are populated
  from those capabilities and recorded with engineer accept/edit/reject.
- **Validation:** quality gates run — `static_analysis` (ruff), `runtime_tests`
  (in-process create/redirect/stats/expiry/max-click with a measured duration),
  `security_review`, and `engineer_ownership` (passes only after sign-off).

## Brownfield

**Requirement:** "Add expiry and max-click controls to existing links."

- **Decomposition:** a focused graph for the two changed capabilities
  (`T-REQ` → `T-DATA` → `T-EXPIRY` / `T-MAXCLICK` → `T-TEST` → `T-DOC`) — not a
  full rebuild. (Capabilities are detected from the words in the requirement, so
  naming only the changed controls keeps the plan scoped.)
- **Execution:** codebase reasoning lists the **impacted modules, the API, the
  data-flow step, and the regression risk** per capability (e.g. expiry →
  `app/url_service._resolve_outcome`, `GET /r/{code}`, timezone risk; max-click
  → over-counting risk). Backward-compatible optional fields are the stated
  trade-off.
- **Validation:** the same executed gates run, and the risk register flags the
  change-specific failure scenarios (timezone/clock-skew, click over-counting)
  each with a mitigation; assumptions/limitations note that existing links keep
  working and there is no background cleanup of expired rows.

## Ambiguous

**Requirement:** "Make links safer and smarter for advisors."

- **Decomposition:** no concrete capability is detected, so the plan is
  `T-REQ` → `T-SCOPE` (define concrete capabilities with the stakeholder before
  coding) → `T-TEST` → `T-DOC`, rather than inventing scope.
- **Execution:** requirement understanding surfaces ambiguity derived from the
  text ("safer"/"smarter" are subjective and need measurable acceptance
  criteria). Without sign-off the status is held at
  `waiting_for_engineer_signoff` / `clarification_required`.
- **Validation:** the `engineer_ownership` gate stays `waiting` until sign-off,
  and the engineer leads by adding notes (which steer capability detection) or
  by approving once the scope is agreed.

## Out-of-scope handling

Requests outside the approved prototype (e.g. "build a Facebook clone",
"generate QR codes", "build Spotify") are routed to **scope review**: the intent
is captured, implementation is blocked, the task list becomes `SCOPE-1..3`, and
the AI suggestion is recorded as `rejected_for_now`. The system does not silently
reinterpret them as URL-shortener work.

## What to show evaluators

1. Run **Greenfield** with sign-off on — point to the sequenced decomposition and the executed quality gates.
2. Run **Brownfield** with sign-off on — point to the per-capability impact analysis and change-specific risks.
3. Run **Ambiguous** with sign-off off — show the waiting status and clarify-first plan; then add a note or approve to show it becoming reviewable.
4. Submit an out-of-scope requirement — show it routed to scope review, not implemented.
5. Download `summary.md` for any run — it contains plan, trade-offs, artifacts, validation, risks, assumptions, and limitations.
