# Devpost submission copy

This document supplies factual copy backed by the live deployment and actual GitLab executions linked below. It does not assert that Devpost has received a submission. **Human voice recording, YouTube upload and final Devpost submission remain pending.** A Devpost draft attempt was blocked twice by reCAPTCHA service-connection errors; no challenge was solved or bypassed. See [evidence status](evidence-status.md) for the final handoff.

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

The reference application is deployed publicly on [Google Cloud Run](https://aftercare-359201230061.us-central1.run.app), with Firestore persistence. Its actual cloud smoke test passed health, registration/login/logout, guest isolation, artifact-digest checks and a recovered duplicate-charge scenario. The repository includes its non-root container build and Google Cloud deployment code. These results are captured in [cloud-smoke-results.json](cloud-smoke-results.json).

## Lifecycle stages

**Plan, create, verify, package, secure, release, configure, monitor and govern.**

The stage claims refer to concrete operations: reproduce and scope an incident; create source repair; execute contracts; package the tested source; enforce capability/path and dependency gates; canary and promote a sandbox revision; apply runtime intent and active-source configuration; independently monitor the promoted behavior; preserve the decision and compensation evidence. The README maps each stage to its evidence and distinguishes reference operations from the connected Duo workflow.

## What makes it different

Rollout verification, business metrics and synthetic monitoring already exist. Aftercare's proposed contribution is closing the loop around already-created business harm: a precise invariant, append-only synthetic compensation, an independent regression repair and a GitLab-bound proof of the decision.

Our initial buyer hypothesis is a small SaaS platform or engineering team already using GitLab, where transaction incidents span engineering and finance support. The proposed business offers open-source local contracts plus paid managed governance and evidence retention. Pricing and unit economics are explicit hypotheses in the product brief; we claim no customers, revenue or validated demand.

## Challenges

The hardest design choice was assigning authority honestly. A browser animation is not an agent run, a passing health check is not a customer guarantee, and a hash is not independent attestation.

We made each distinction observable: the browser uses a deterministic reference controller, real subprocess and HTTP results drive state, the separate Duo flow produced independently verified source edits, and unsafe candidates stop before execution. We also kept rollback and reconciliation distinct, because returning to a safe revision does not repair existing duplicate ledger entries.

## Accomplishments

We built an authenticated, usable product around a specific customer failure, rather than a collection of automation prompts. Its happy path produces verifiable artifacts, and its refusal path demonstrates that autonomy remains bounded. The implementation includes adversarial contracts, session isolation, tamper detection, source-bound packaging and repeatable incident reproduction.

The completed [Duo session](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions/9737653) generated [MR 1](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/merge_requests/1), modifying exactly the permitted service file and adding five regression tests. The existing acceptance contract was unchanged. The repair pipeline passed all ten business-contract tests. An independent counterfactual check found that four of the five new regressions fail against the original source. The full main pipeline passed its nine stages, including 38 application/CLI tests at that snapshot; a subsequent local test addition brings the latest local suite to 39.

## What we learned

The useful unit of automation is a customer promise with an explicit recovery boundary. Deterministic tools make that promise testable and keep the evidence precise; agents add value when they diagnose and repair source within those boundaries.

## What's next

Validate the buyer and pricing through customer interviews and a staged pilot. Build reviewed adapters for existing SaaS services, then add organization identity, durable distributed execution and separately authorized processor compensation. Measure actual connected-flow cost before setting paid incident allowances. None of those future integrations is claimed as complete in this submission.

## Built with

GitLab Duo Agent Platform, GitLab CI/CD, Python, FastAPI, React, TypeScript, Vite, SQLite, Google Cloud Run deployment code, Firestore cloud persistence, Docker, pytest, unittest, pip-audit, SHA-256, CycloneDX fixture manifest.

## Repository URL

[Aftercare public GitLab project](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare)

## Pipeline and agent evidence

- [Completed Duo session 9737653](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions/9737653)
- [Successful Duo workload pipeline 2966825574](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966825574)
- [AI-generated repair MR 1, left open for human review](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/merge_requests/1)
- [Successful repair pipeline 2966834617: ten contract tests](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966834617)
- [Successful full main pipeline 2966841144: nine stages](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966841144)

The single repair gate and the full main pipeline prove different scopes. The repair MR's source commit is `fadd583d8a27769bb82bbb318e4c33a309a133a5`; no merge or customer production deployment is claimed.

## Live project and video fields

**Live Google Cloud project:** [Aftercare public application](https://aftercare-359201230061.us-central1.run.app).

**YouTube video:** pending Shivam's voice recording and upload. The verbatim narration and exact shot list are in [video-script.md](video-script.md). Once uploaded, watch the full export signed out and copy its real YouTube URL into Devpost.

**Devpost submission:** pending. The draft workflow encountered reCAPTCHA service-connection errors on two attempts. A human must complete the remaining challenge/form and final submission; this document is not evidence of entry.

## Environmental Impact prize

**Do not opt in for this release.** The implementation avoids model calls for deterministic reference work, caches dependencies and bounds execution, but has no measured energy/SCI baseline. We do not claim quantified carbon savings.

## Team and attribution

**Shivam Gupta — creator and project director; product direction, implementation oversight and final review, with AI-assisted engineering and testing.** Do not add nonexistent teammates or claim manual authorship of work that was AI assisted. Repository software and documentation are MIT licensed.

## Final submission check

Verify the public MIT repository, actual visible CI history, actual Duo execution, required live URL for the cloud bonus, and a YouTube demo shorter than three minutes. Submit before **27 October 2026, 13:00 UTC / 18:30 India time**. Preserve the submitted repository and materials unchanged after the deadline through the required judging period; continue future work in a separate copy or fork.
