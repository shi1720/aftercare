# Aftercare

**Your health check is green. Your customer was charged twice.**

Aftercare turns a broken customer promise into a bounded recovery workflow. It restores a safe revision, reconciles existing harm in a synthetic ledger, verifies a repair, and carries the proof to the release decision.

Created and directed by **Shivam Gupta**, with AI-assisted engineering and review. Built from scratch for GitLab Transcend 2026. **Path A · Supervised.**

## The problem worth solving

Consider a subscription SaaS team receiving retried checkout requests after a network timeout. The service stays online and returns successful HTTP responses, yet each retry creates another capture. A rollback stops additional duplicates. It does not reverse duplicates already created.

The engineering lead must now coordinate incident containment, transaction reconciliation, a source repair, a regression test and evidence for the final decision. The customer experiences one failure; the team inherits work across several systems.

Aftercare begins with a precise invariant: **one tenant, one idempotency key and one amount produce one net debit**. An amount change under an existing key must fail closed. Tenant isolation is a second executable promise, with a third adversarial scenario proving an unsafe repair is rejected.

## A complete recovery, with clear authority

| Step | Concrete outcome |
| --- | --- |
| Detect | A real subprocess test reproduces the business failure; loopback HTTP probes separately measure service health. |
| Contain | The isolated active-revision pointer returns to a known safe source, which is independently tested. |
| Reconcile | Append-only reversals balance duplicate synthetic debits. Repeating reconciliation produces no extra reversal. |
| Repair | The reference controller selects a reviewed repair; the separate Duo flow independently edits checked-in source and adds a regression test. |
| Verify and release | Contract tests, restricted AST policy, source-bound packaging and HTTP replay gate sandbox promotion. |
| Prove | The decision includes a source diff, artifact hashes, ledger entries and an event hash chain. |

The public reference app runs hands-off inside fixed first-party fixtures and makes **zero model calls**. The GitLab integration uses two Duo AgentComponents for investigation and repair, then leaves a tested merge request for review. It does not automatically merge, deploy a customer's service, or contact a payment processor. Registration and actual execution of that flow are tracked in [evidence status](evidence-status.md).

**Actual execution, 20 October 2026:** [Duo session 9737653](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions/9737653) finished and produced [repair MR 1](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/merge_requests/1). Its [repair pipeline](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966834617) passed ten contracts. An independent review ran the five added regressions against the original source: four failed, confirming the tests detect the defect. The separate [full main pipeline](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966841144) passed all nine configured stages and 38 application/CLI tests at that snapshot; the latest local suite has 39 tests. The [public Cloud Run application](https://aftercare-359201230061.us-central1.run.app) passed health, sign-in, guest-isolation, recovery and artifact-digest smoke checks with Firestore persistence; the captured results are in [cloud-smoke-results.json](cloud-smoke-results.json).

All credit amounts are synthetic. A ledger reversal is not a real refund. An isolation incident cannot undo data already disclosed; its demonstration establishes containment and corrected access behavior.

## First customer and practical adoption

The initial buyer hypothesis is a head of engineering or platform lead at a transaction-heavy SaaS company using GitLab, with a small on-call team and repeated payment or entitlement incidents. The first use case is checkout retry integrity in an isolated staging environment.

An initial deployment would install one invariant pack, connect a reviewed application adapter, reproduce a known incident, and require a human to approve the first repair outcome. Real processor compensation would need a separately reviewed adapter, authorization boundaries, replay protection and reconciliation rules. Those integrations are future work, not functionality hidden behind the demo.

Success would mean fewer manual handoffs and a shorter, independently verifiable path from incident to a correct customer outcome. This release has no claimed customers, revenue or validated willingness to pay. Customer interviews and a staged pilot are the next commercial tests.

## Why it can stand apart

This is a competitive market. [LaunchDarkly guarded rollouts](https://launchdarkly.com/docs/fed-docs/home/releases/releasing) already monitor selected metrics and can automatically revert a release. [Harness deployment verification](https://www.harness.io/products/continuous-delivery/ai-assisted-deployment-verification) compares deployment health signals and supports rollback. [Checkly synthetic monitoring](https://www.checklyhq.com/product/synthetic-monitoring/) tests checkout and other important customer journeys.

Aftercare's proposed wedge is the incident closure after containment: **prove a business invariant, reconcile already-created synthetic harm, create the regression repair, and bind the evidence to the GitLab decision**. The novelty claim concerns that integrated workflow, not business metrics, synthetic monitoring or automatic rollback by themselves.

The defensibility hypothesis is a growing library of reviewed domain contracts and compensation adapters, plus source-bound regression evidence. This is a product direction to validate, not an established moat.

## Business and unit economics: explicit hypotheses

The proposed business is open-source contracts and a local controller, with a paid managed service for team governance, longer evidence retention and reviewed integrations. A testable opening price is **US$99 per environment per month**, including up to 20 agent-assisted incidents. This is a pricing hypothesis; no billing or paid plan is implemented.

An illustrative monthly direct-cost model is:

`cost = fixed hosting allocation + incidents × (model allocation + execution + retained evidence)`

| Assumption | Illustrative value |
| --- | --- |
| Fixed hosting/storage allocation | US$10/month |
| Agent/model allocation | US$0.50 per incident |
| Execution allocation | US$0.02 per incident |
| Retained evidence allocation | US$0.01 per incident |
| Twenty incidents | US$20.60 total direct cost |
| US$99 revenue less that direct cost | US$78.40, or about 79% before support, payment fees, tax, development and sales |

These values are planning assumptions, not provider quotes or measured spend. GitLab Credits and model consumption must be measured in actual sessions before setting incident allowances. One hundred incidents under the same assumptions would cost US$63; quotas, a measured usage price and bounded inference would be necessary to protect margins. The current sandbox does not enforce dollar-denominated spending limits.

The reference controller needs no paid model API. Local use needs no paid service. A cloud deployment can incur hosting and database charges; see [deployment details](deployment.md).

## Sustainability without invented savings

Deterministic checks handle policy, hashing, packaging and known fixture recovery. The reference run reports zero model calls; expensive reasoning belongs in the connected diagnosis and source-repair steps. Pinned dependencies, CI caching, bounded workloads and scale-to-zero cloud configuration avoid unnecessary work.

We are **not opting into the Environmental Impact prize** for this release. No energy consumption, hardware allocation or regional carbon intensity has been measured, and no SCI baseline has been established. Model-call and request counters are operational evidence, not carbon measurements. A future study would define the functional unit, compare equal workloads and apply the [Software Carbon Intensity specification](https://sci.greensoftware.foundation/).

## The scope judges can verify

The repository contains a functioning authenticated reference app, isolated guest sessions, real tests and HTTP traffic, an unsafe-repair refusal, a source-repair fixture, Duo flow configuration, CI and cloud deployment code. Each of the nine lifecycle stages maps to a concrete operation in [the README](../README.md#lifecycle-coverage).

Repository: [public GitLab project](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare). External execution and deployment claims should be checked against [evidence status](evidence-status.md), not inferred from configuration files.
