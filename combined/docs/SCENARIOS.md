# Scenario Playbooks

## Greenfield

Requirement: build a URL shortener from scratch with create, redirect, analytics, and reliability controls.

Workflow: requirements -> architecture -> implementation/tests/security in parallel -> documentation -> release approval.

Validation: API tests cover creation, duplicate slug protection, redirect behavior, analytics increments, and health checks.

## Brownfield

Requirement: enhance an existing shortener while preserving behavior.

Workflow difference: inserts impact analysis before architecture. The run records impacted modules and data flow before downstream work starts.

Validation: regression tests preserve existing API behavior while analytics and orchestration tests confirm the enhancement.

## Ambiguous

Requirement: "Make links smarter and safer, but keep the product simple."

Workflow difference: inserts a clarification node after requirements. This node requires product-owner approval before architecture starts.

Validation: the workflow demonstrates safe controlled autonomy by pausing until ambiguity is resolved and stopping safely if rejected.

