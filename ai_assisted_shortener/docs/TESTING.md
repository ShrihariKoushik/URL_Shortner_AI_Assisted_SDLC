# Testing Approach, Limitations, and Trade-offs

## How to run

```bash
cd ai_assisted_shortener
python -m pytest -q        # 33 tests, expect: 33 passed
python -m ruff check .     # expect: All checks passed!
```

Tests run against the **deterministic (offline) engine** (`openai_enabled=False`
is set in the test setup), so they are reproducible and require no network or API
key. Requires Python 3.11+.

## Approach

- **Unit tests** (`tests/test_url_service.py`) cover the core service rules in
  isolation: create/resolve/stats, expiry blocking (and not counting expired
  hits), and the max-click limit.
- **Integration tests** (`tests/test_api.py`) drive the full FastAPI app through
  `TestClient`: the shortener API, reserved-endpoint validation, and every
  engineering/implementation evidence dimension.
- **Behavioural assertions over fixtures.** Tests assert that outputs are
  *derived from the input* — e.g. two different requirements produce different
  task graphs, risk registers, and impact analyses — rather than checking static
  strings. This is what guards against the evidence silently becoming canned.
- **Gates are tested as executed, not declared.** The quality-gate tests assert
  the runtime smoke test actually ran (it reports a measured `duration_ms`) and
  that the security gate blocks a sensitive requirement. The generated-package
  test asserts the generated unit tests were executed.

## Coverage mapped to the eight requirements

- **R1 Understanding** — understanding derived from input; vague input flags ambiguity; understanding feeds traceability.
- **R2 Decomposition** — requirement-specific task graph; valid dependencies/sequencing; vague input clarifies first.
- **R3 Codebase reasoning** — requirement-specific impact; reports API and regression risk.
- **R4 AI-assisted execution** — quality gates actually run; security gate blocks; six SDLC phases are requirement-specific.
- **R5 Output generation** — generated package is validated; package includes generated code, tests, and docs that execute.
- **R6 Validation & risk** — requirement-specific risks/trade-offs, each with a mitigation.
- **R7 Controlled oversight** — engineer notes steer execution; per-step overrides flow to traceability; sign-off gating for engineering and implementation.
- **R8 Final summary** — `summary.md` contains all required sections; assumptions/limitations follow the requirement.
- **Scope control** — QR, Facebook-clone, Spotify, and unknown-product requests are routed to scope review.

## Limitations

- **Offline path is rule-based.** Without an API key, the understanding,
  decomposition, codebase, risk, and summary content come from deterministic
  capability templates rather than open-ended LLM reasoning. Iterative refinement
  (the corrective retry in the implementation package) only engages on the AI
  path.
- **Prototype scope.** Single-node SQLite, no authentication model, and no
  production observability backend. The shortener is not built for horizontal
  scale.
- **Generated artifacts are intentionally small.** `codegen` emits focused,
  dependency-free rule modules and their tests to demonstrate verified output
  generation; it is not a full feature-implementation generator.
- **Maintainability.** `app/engineering.py` is large and would benefit from being
  split into focused modules (understanding, decomposition, codebase, phases,
  gates) as a follow-up.

## Trade-offs

- **SQLite over Redis/Postgres** — simplest durable setup for a reviewable
  prototype; the service seam allows swapping later.
- **Deterministic fallback that mirrors the AI output shape** — guarantees the
  system is runnable and testable offline, at the cost of the offline content
  being templated rather than generative.
- **Quality gates run real tools in-request** — gives honest pass/fail evidence,
  at the cost of a small per-request latency (a ruff subprocess and an in-process
  smoke test); the gate reports `skipped` rather than failing if a tool is absent.
- **Hard sign-off gate on code generation** — prioritises controlled oversight
  over convenience: no implementation files are produced without engineer
  approval.
- **OpenAI-compatible base URL** — one integration covers many providers
  (OpenAI, DeepSeek, Meta Llama hosts, Claude via gateway) at the cost of not
  using any provider's native, non-standard features.
