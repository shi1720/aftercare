# Devpost submission copy

This document supplies factual copy. It does not assert that Devpost has received a submission. Before submitting, complete the actual live URL, Duo session, repair MR, passed pipeline and YouTube fields in [evidence status](evidence-status.md), then verify every link signed out.

## Project name

Aftercare

## Elevator pitch

Your health check is green. Your customer was charged twice. Aftercare restores safety, reconciles synthetic harm, verifies a bounded repair, and brings proof to a supervised GitLab decision.

## Track and autonomy

**Path A: Start Fresh. Supervised.**

Created from scratch during the hackathon submission period. No existing project was imported. The connected GitLab Duo workflow investigates, repairs, tests and opens a merge request; Shivam reviews the outcome. The public reference sandbox runs its fixed-fixture recovery hands-off, with deterministic repairs and zero model calls. These scopes are explicitly distinguished in the interface and documentation.

## Inspiration

The customer does not care that our uptime is green if their card was charged twice.

Retries, idempotency mistakes and tenant-boundary regressions can violate a customer promise while a service still responds successfully. Restoring an older revision stops additional harm. It leaves the team with the work already created: reconcile the ledger, fix the source, add the regression and assemble the evidence.

Aftercare starts at that overlooked boundary: recovery is not complete when the server is healthy. It is complete when the customer promise is restored and the decision can be inspected.

## What it does

Aftercare is a working recovery laboratory for transaction-heavy SaaS teams. Judges can enter an isolated sandbox without a payment account or API key, or create an account with their own persisted run history.

The main scenario demonstrates a checkout retry regression. A real loopback health probe returns 200 while an executable idempotency contract fails. The controller restores a known safe revision, independently validates it and appends compensating entries to a synthetic ledger. It preserves original history and verifies reconciliation is idempotent.

A reviewed reference repair then passes contract tests, an AST capability gate, digest-bound packaging, loopback canary requests and an independent post-promotion check. Each decision carries a source diff, measured results, ledger entries, artifact hashes and an event hash chain.

A second scenario verifies tenant isolation. A third deliberately proposes an unsafe repair and proves it is rejected before execution while the safe revision remains active.

All credits are synthetic. No payment processor is called, and no real refund or production customer deployment is implied. Hash chains establish integrity relative to a trusted head, not an external signature or compliance certification.

## How we built it

Shivam Gupta created and directed Aftercare, using AI-assisted implementation and review. The application uses React, TypeScript and Vite for the interface, FastAPI and Python for the API and controller, SQLite locally, and a dedicated Firestore database in cloud mode. Session-owner checks isolate run history and artifact downloads. Passwords use salted scrypt; session secrets are stored as hashes.

The GitLab Duo configuration defines two AgentComponents. The investigation agent runs a reproducible incident CLI and reads actual failing tests and source-bound evidence. The repair agent independently edits the intentionally defective checkout source and adds a new regression test. Executable changed-path rules protect the existing acceptance contract, CI and verifier. The repair is verified before a merge request is opened for review.

CI builds the interface, tests the API/controller and CLI, audits Python dependencies, checks restricted AST capabilities, packages source, executes actual sandbox recovery scenarios and retains evidence. Main's intentionally defective fixture is an expected-failure demonstration: the reproduce command succeeds only when it observes real duplicate captures and failing contracts. Repair branches must instead pass the business contract and added regression.

The repository also includes a non-root container build and Google Cloud deployment code. Actual deployment and connected-flow execution status are recorded in the linked evidence document; configuration alone is not presented as execution.

## Lifecycle stages

**Plan, create, verify, package, secure, release, configure, monitor and govern.**

The stage claims refer to concrete operations: reproduce and scope an incident; create source repair; execute contracts; package the tested source; enforce capability/path and dependency gates; canary and promote a sandbox revision; apply runtime intent and active-source configuration; independently monitor the promoted behavior; preserve the decision and compensation evidence. The README maps each stage to its evidence and distinguishes reference operations from the connected Duo workflow.

## What makes it different

Rollout verification, business metrics and synthetic monitoring already exist. Aftercare's proposed contribution is closing the loop around already-created business harm: a precise invariant, append-only synthetic compensation, an independent regression repair and a GitLab-bound proof of the decision.

Our initial buyer hypothesis is a small SaaS platform or engineering team already using GitLab, where transaction incidents span engineering and finance support. The proposed business offers open-source local contracts plus paid managed governance and evidence retention. Pricing and unit economics are explicit hypotheses in the product brief; we claim no customers, revenue or validated demand.

## Challenges

The hardest design choice was assigning authority honestly. A browser animation is not an agent run, a passing health check is not a customer guarantee, and a hash is not independent attestation.

We made each distinction observable: the browser uses a deterministic reference controller, real subprocess and HTTP results drive state, the separate Duo flow must produce actual source edits, and unsafe candidates stop before execution. We also kept rollback and reconciliation distinct, because returning to a safe revision does not repair existing duplicate ledger entries.

## Accomplishments

We built an authenticated, usable product around a specific customer failure, rather than a collection of automation prompts. Its happy path produces verifiable artifacts, and its refusal path demonstrates that autonomy remains bounded. The implementation includes adversarial contracts, session isolation, tamper detection, source-bound packaging and repeatable incident reproduction.

## What we learned

The useful unit of automation is a customer promise with an explicit recovery boundary. Deterministic tools make that promise testable and keep the evidence precise; agents add value when they diagnose and repair source within those boundaries.

## What's next

Validate the buyer and pricing through customer interviews and a staged pilot. Build reviewed adapters for existing SaaS services, then add organization identity, durable distributed execution and separately authorized processor compensation. Measure actual connected-flow cost before setting paid incident allowances. None of those future integrations is claimed as complete in this submission.

## Built with

GitLab Duo Agent Platform, GitLab CI/CD, Python, FastAPI, React, TypeScript, Vite, SQLite, Google Cloud Run deployment code, Firestore cloud persistence, Docker, pytest, unittest, pip-audit, SHA-256, CycloneDX fixture manifest.

## Repository URL

[Aftercare public GitLab project](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare)

## Pipeline and agent evidence

[CI/CD history](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines) · [Duo sessions](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions)

These are project index pages. Use the specific successful execution URLs recorded in [evidence status](evidence-status.md) when completing the final form and recording the video. Do not claim an index page proves a particular run succeeded.

## Live project and video fields

Copy the verified public application URL from [deployment evidence](deployment.md) after a signed-out smoke test. Copy the completed YouTube URL from [evidence status](evidence-status.md) after watching the full export signed out. Do not submit this document's internal links as substitutes for those fields.

## Environmental Impact prize

**Do not opt in for this release.** The implementation avoids model calls for deterministic reference work, caches dependencies and bounds execution, but has no measured energy/SCI baseline. We do not claim quantified carbon savings.

## Team and attribution

**Shivam Gupta — creator and project director; product direction, implementation oversight and final review, with AI-assisted engineering and testing.** Do not add nonexistent teammates or claim manual authorship of work that was AI assisted. Repository software and documentation are MIT licensed.

## Final submission check

Verify the public MIT repository, actual visible CI history, actual Duo execution, required live URL for the cloud bonus, and a YouTube demo shorter than three minutes. Submit before **27 October 2026, 13:00 UTC / 18:30 India time**. Preserve the submitted repository and materials unchanged after the deadline through the required judging period; continue future work in a separate copy or fork.
