# Scenarios

## Greenfield

Requirement:

Build a URL shortener service from scratch with create, redirect, analytics, expiry, max-click limits, tests, and documentation.

Demonstrates:

- Requirement normalization
- New API/schema/service/data design
- Task decomposition from blank slate
- AI suggestions for API shape and tests
- Engineer edits and ownership
- Quality gates and final summary

## Brownfield

Requirement:

Enhance the existing shortener with expiry and max-click controls while preserving create, redirect, and analytics behavior.

Demonstrates:

- Impacted modules and data flow
- Regression-risk reasoning
- Backward-compatible optional fields
- AI-generated test ideas reviewed by engineer
- Explicit decisions around analytics semantics

## Ambiguous

Requirement:

Make links safer and smarter for advisors without making the product complicated.

Demonstrates:

- Ambiguity identification
- Clarifying questions and assumptions
- Scope control before implementation
- Rejection of unbounded AI suggestions
- Engineer sign-off as a gate before coding

## What To Show Evaluators

1. Run Greenfield with sign-off on.
2. Run Brownfield with sign-off on and point to impacted components.
3. Run Ambiguous with sign-off off and show waiting status.
4. Turn sign-off on and regenerate to show the outcome becomes reviewable.
5. Download `summary.md` for the run.
