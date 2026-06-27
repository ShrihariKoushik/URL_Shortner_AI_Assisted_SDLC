# Complete Beginner Explanation: Agentic URL Shortener

This document explains the whole project in simple language. Use it to understand the project, prepare for the demo, and answer interview questions.

## 1. What Did We Build?

We built two things:

1. A URL Shortener
2. An Agentic Software Engineering System around it

The URL shortener is the actual product.

The agentic system is the main assessment idea. It shows how an AI-assisted engineering workflow can take a requirement, break it into tasks, run software delivery stages, pause for human approval, track risks, and report audit logs and reliability metrics.

Simple comparison:

```text
Normal project:
Developer reads requirement -> writes code -> tests -> documents -> releases

This project:
Agentic workflow reads requirement -> decomposes tasks -> runs stages -> checks gates
-> asks human approval -> logs everything -> reports metrics -> releases safely
```

## 2. What Is A URL Shortener?

A URL shortener converts a long URL into a short link.

Example:

```text
Long URL:
https://www.schwab.com/client-home/accounts/summary/details

Short URL:
http://127.0.0.1:8001/schwab-demo
```

When someone opens the short URL, the app redirects them to the original long URL.

Our app supports:

```text
Create short URL
Redirect short URL
Track clicks
Show analytics
```

Example in the UI:

```text
Target URL: https://www.schwab.com
Custom slug: schwab-demo
```

Result:

```text
http://127.0.0.1:8001/schwab-demo
```

If someone opens that link, the click count increases.

## 3. What Is A Slug?

A slug is the short code at the end of the URL.

Example:

```text
http://127.0.0.1:8001/schwab-demo
```

Here, the slug is:

```text
schwab-demo
```

A custom slug means the user chooses the code.

An auto-generated slug means the system creates it randomly, for example:

```text
aB91xZk
```

Important note: the assignment did not specifically require custom slug. We added it as a useful extra. In a normal-user UI, custom slug should be optional.

## 4. What Is FastAPI?

FastAPI is the Python framework used to build the backend API.

Simple meaning:

```text
FastAPI lets us create web endpoints.
```

An endpoint is a URL that performs a backend action.

Example endpoint:

```text
POST /shorten
```

Meaning:

```text
Send a long URL to the backend and get a short URL back.
```

Another endpoint:

```text
GET /stats/{slug}
```

Meaning:

```text
Show click analytics for this short link.
```

FastAPI automatically creates technical API documentation here:

```text
http://127.0.0.1:8001/docs
```

That page is mainly for technical reviewers.

## 5. What Is SQLite?

SQLite is a small local database.

It stores the app data locally without needing a separate database server.

The database stores:

```text
slug
target URL
created time
click count
last accessed time
```

Example database row:

```text
slug: schwab-demo
target_url: https://www.schwab.com
clicks: 3
last_accessed_at: 2026-06-27...
```

We used SQLite because it is easy to run locally for a take-home assessment. No external database setup is needed.

## 6. What Is The OpenAI API Doing?

The OpenAI API is optional in this project.

Its role is requirement analysis.

Example requirement:

```text
Build a URL shortener with analytics and reliability features.
```

The agent or LLM can summarize it like this:

```text
Requirement: Create short links, redirect users, track click analytics.
Assumptions: Must run locally. Must have approval gates.
Risks: Ambiguous requirements, duplicate slugs, unsafe redirects.
```

If no OpenAI API key is provided, the app still works using a deterministic fallback.

That is useful because reviewers can run the project without secrets or network access.

## 7. What Does Agentic Mean?

Agentic means the system can perform multi-step work with some autonomy.

But it is not uncontrolled.

In this project:

```text
Agents execute.
Humans approve.
The system logs everything.
```

Simple analogy:

```text
An assistant can prepare the work, but a senior person approves important decisions.
```

That is exactly what the assessment wants: controlled autonomy.

## 8. What Is SDLC?

SDLC means Software Development Life Cycle.

It is the full process of building software:

```text
Requirement
Design
Implementation
Testing
Security review
Documentation
Release
```

Our agentic workflow models these stages.

## 9. What Is A DAG-Based Workflow?

DAG means Directed Acyclic Graph.

Simple meaning:

```text
A set of steps with dependencies, where work moves forward and does not loop forever.
```

Example:

```text
Requirements must happen before Architecture.
Architecture must happen before Implementation.
Implementation, Tests, and Security can happen in parallel.
Release happens only after everything passes.
```

Our workflow looks like this:

```text
Requirements
   ↓
Architecture
   ↓
Implementation + Tests + Security
   ↓
Documentation
   ↓
Release Gate
   ↓
Human Approval
```

For brownfield work, the workflow adds:

```text
Impact Analysis
```

For ambiguous work, the workflow adds:

```text
Clarification
```

## 10. What Are Entry Gates And Exit Gates?

A gate is a checkpoint.

An entry gate asks:

```text
Can this step start?
```

An exit gate asks:

```text
Did this step finish correctly?
```

Example:

Architecture should not start unless requirements are complete.

```text
Entry gate:
Do we have a normalized requirement?
```

Release should not happen unless validation passed.

```text
Exit gate:
Are implementation, tests, security, and docs complete?
```

This is important because it proves the system has governance and does not blindly run steps out of order.

## 11. What Is A Human Approval Checkpoint?

A human approval checkpoint pauses the workflow until a person approves.

Example:

You run the workflow with auto approve turned off.

The UI shows:

```text
Waiting for approval: release
```

Then you click:

```text
Approve checkpoint
```

After approval, the UI shows:

```text
Status: completed
```

This proves the system does not blindly release important changes.

## 12. What Is Audit Logging?

Audit logging means recording what happened.

Example events:

```text
workflow_started
node_started
node_passed
approval_required
approval_recorded
workflow_completed
```

Audit logs help answer:

```text
Who approved?
What ran?
When did it run?
What failed?
What passed?
```

This matters especially in financial and regulated environments.

## 13. What Are Reliability Metrics?

Reliability metrics measure how dependable the workflow is.

The UI shows:

```text
Success rate
Retries
Fallbacks
Rollbacks
Latency
```

Simple definitions:

```text
Success rate:
How many workflow steps passed successfully.

Retries:
How many times the system tried again after a failure.

Fallbacks:
Backup behavior used when the primary behavior fails.

Rollbacks:
Undo or safe reversal when release fails.

Latency:
How long the workflow took.
```

Example output:

```text
Success rate: 100%
Retries: 0
Fallbacks: 0
Rollbacks: 0
Latency: 0.01s
```

## 14. What Are The Three Scenarios?

The assessment asks for three scenarios.

### Greenfield

Greenfield means building something new from scratch.

Example:

```text
Build a new URL shortener.
```

Workflow:

```text
Requirements -> Architecture -> Build/Test/Security -> Docs -> Release
```

### Brownfield

Brownfield means changing an existing system.

Example:

```text
Add analytics to an existing URL shortener.
```

Extra concern:

```text
What existing files, APIs, and data flows will this change affect?
```

That is why the workflow adds:

```text
Impact Analysis
```

### Ambiguous

Ambiguous means the requirement is unclear.

Example:

```text
Make links smarter and safer.
```

That is vague. What does smarter mean? What does safer mean?

So the workflow pauses for:

```text
Clarification
```

This proves the system does not make risky assumptions silently.

## 15. What Is The Difference Between The UI And Swagger Docs?

The UI is for normal users and business reviewers.

Open it here:

```text
http://127.0.0.1:8001/
```

It shows:

```text
Create short link
View analytics
Run workflow
Approve checkpoint
See metrics
Understand scenarios
```

Swagger docs are for technical reviewers.

Open them here:

```text
http://127.0.0.1:8001/docs
```

Swagger shows all backend API endpoints and lets engineers test raw API calls.

## 16. How To Run The UI Version

Open PowerShell and run:

```powershell
cd C:\Users\shrih\Downloads\dp\cs_codex\ui
uvicorn app.main:app --reload --port 8001
```

Then open:

```text
http://127.0.0.1:8001/
```

To stop the app later, go to the PowerShell window running uvicorn and press:

```text
Ctrl + C
```

## 17. How To Demo The Project

Use this order.

### Step 1: Show The Normal User UI

Open:

```text
http://127.0.0.1:8001/
```

Say:

```text
This is the product-facing view. A normal user can create a short link and see analytics.
```

Create a short link.

Example:

```text
Target URL: https://www.schwab.com
Custom slug: schwab-demo
```

Then show the generated short URL and analytics.

### Step 2: Show The Workflow Section

Scroll to the DAG workflow section.

Say:

```text
This is the agentic engineering workflow behind the project. It models how software changes move through SDLC stages.
```

Run Greenfield with auto approve off.

Show:

```text
Waiting for approval: release
```

Say:

```text
The agent can execute work, but release requires human approval.
```

Click approve.

Show:

```text
Status: completed
Success rate: 100%
```

### Step 3: Show Brownfield

Run Brownfield.

Say:

```text
Brownfield includes impact analysis because changing existing systems needs extra care.
```

### Step 4: Show Ambiguous

Run Ambiguous.

Say:

```text
Ambiguous requirements trigger clarification before architecture starts.
```

### Step 5: Show Technical API Docs

Open:

```text
http://127.0.0.1:8001/docs
```

Say:

```text
This is the technical API view for engineering reviewers.
```

## 18. Interview Explanation Script

You can say this:

```text
I built a runnable URL shortener using Python, FastAPI, and SQLite.
But the main focus is the agentic SDLC orchestration layer.

The system takes requirements, decomposes them into workflow stages,
executes them through a DAG, enforces entry and exit gates, pauses for
human approval on high-impact actions, logs all events for auditability,
and tracks reliability metrics like success rate, retries, rollbacks,
fallbacks, MTTR, and latency.

I included greenfield, brownfield, and ambiguous scenarios to show how
the orchestration adapts based on the type of engineering request.
```

## 19. Important Files

Main backend API:

```text
app/main.py
```

URL shortener logic:

```text
app/url_service.py
```

Database setup:

```text
app/database.py
```

Agentic DAG orchestration:

```text
app/orchestrator.py
```

Audit logging:

```text
app/audit.py
```

UI files:

```text
ui/app/static/index.html
ui/app/static/styles.css
ui/app/static/app.js
```

Architecture docs:

```text
docs/ARCHITECTURE.md
ui/docs/ARCHITECTURE.md
```

Scenario docs:

```text
docs/SCENARIOS.md
ui/docs/SCENARIOS.md
```

## 20. One-Line Summary

The project is:

```text
A Python FastAPI URL shortener wrapped in a governed agentic SDLC orchestration system with DAG workflow, gates, approvals, audit logs, retries, rollback hooks, and reliability metrics.
```
