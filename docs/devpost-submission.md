# Devpost submission fields

Continue the existing submission **1247898**. The title and tagline have been saved. This document does not claim final publication or submission.

The canonical copy is in [submission-fields.json](submission-fields.json): project title, tagline, story, testing instructions, YouTube title and YouTube description. The story is also readable in [submission-story.md](submission-story.md). These fields replace the earlier long draft.

Primary product URL: https://aftercare-release.web.app. Verify the final deployment and sign-in flow before submitting. GitLab source and immutable execution evidence remain linked from the product.

## Project title

Aftercare

## Tagline

Your health check is green. Your customer was charged twice. Aftercare contains the harm, verifies the repair, and brings the proof to GitLab.

## Story

## Inspiration

A customer retries a checkout after a timeout. Every request succeeds. The dashboard stays green. The ledger now contains two charges for one purchase.

Rolling back can stop the next duplicate. It does not fix the duplicates already created. Someone still has to reconcile the damage, repair the source, add the regression and prove the release is safe.

We built Aftercare around that unfinished work. Recovery should end with a correct customer outcome, not just a healthy server.

## What it does

Aftercare gives a small engineering team an inspectable recovery loop built around customer promises: one purchase produces one net charge, one tenant cannot read another tenant's order, and a repair cannot bypass its safety boundary.

Open the public sandbox and introduce a checkout retry fault. A real HTTP health probe returns 200 while the business contract fails. Aftercare restores a known safe revision, validates it, and appends 23 compensating entries for 23 extra synthetic debits. It preserves the original ledger and verifies that repeating reconciliation adds no further reversal.

The reference controller then tests a reviewed repair, checks its executable capabilities, packages the tested source, replays HTTP traffic and verifies the promoted sandbox revision. Each run includes the diff, test results, ledger, artifact hashes and a downloadable decision record. An unsafe candidate is blocked before execution.

These are synthetic credits, not real customer payments. The public reference loop uses deterministic repairs. The separate GitLab Duo workflow performs genuine AI investigation and source repair under human outcome review.

## How we built it

Shivam Gupta created and directed Aftercare with AI-assisted engineering and testing. The product uses React and TypeScript, a FastAPI control plane, Python recovery checks and Firestore persistence on Google Cloud Run. Guest sessions and registered accounts have separate run histories and artifact access.

Our custom GitLab Duo flow contains an investigation agent and a repair agent. In its completed execution, Duo reproduced the checked-in fault, wrote the source fix and added five regression tests without changing the existing acceptance contract. An independent check ran those new tests against the original source: four failed. The repaired source passed all ten business tests.

GitLab CI covers plan, create, verify, package, secure, release, configure, monitor and govern through executable operations and retained artifacts. The tested repair passed a full pipeline of 11 jobs across nine stages. Dependency audits, changed-path checks and behavioral tests turn the agent's proposal into a reviewable engineering result.

## Challenges we ran into

The hardest part was keeping containment, compensation and source repair distinct. A rollback cannot erase an existing duplicate debit. A passing test cannot authorize a candidate with forbidden capabilities. A hash cannot prove that an external system executed a release.

We made those boundaries visible in the product and evidence instead of hiding them behind a success animation. The source-repair workflow and synthetic reference run each show what actually happened.

## Accomplishments that we're proud of

Aftercare is a usable product with a public deployment, sign-in, isolated guest workspaces and three executable scenarios. It combines a real Duo-generated source repair with meaningful regression tests, passing CI, synthetic reconciliation and a refusal path that can be inspected.

The commercial starting point is specific: SaaS engineering teams using GitLab whose transaction incidents spill into finance and support. The proposed business pairs open-source contracts with managed evidence and team governance. Customer demand and pricing remain hypotheses to validate.

## What we learned

The useful unit of automation is a customer promise. Deterministic tools make that promise testable. Agents help diagnose and repair the source. Evidence connects both to a decision someone can trust.

## What's next for Aftercare

Validate the first buyer through a staged pilot, add reviewed adapters for existing services, and measure the cost of real agent incidents. Extend the platform with durable workflow execution and organization identity. Real payment compensation would require its own reviewed integration and authorization model.

The goal stays simple: keep the customer promise, and bring the proof.

## Testing instructions

1. Open https://aftercare-release.web.app and choose Open sandbox. No account, API key or payment account is required.
2. Start the duplicate-charge scenario. Allow the run to finish, then compare the healthy service signal with the initially failed customer contract.
3. Inspect the reconciliation event: 24 original synthetic debits, 23 append-only reversals and one net debit. Replaying reconciliation must not add another reversal.
4. Open Repair diff and Evidence. Inspect the actual test results, candidate checks and source hashes, then export the complete evidence record.
5. Start Unsafe repair. Confirm the candidate is blocked before execution and the verified safe revision remains active.
6. Run the tenant-isolation scenario and inspect the corrected cross-tenant access results.
7. Open GitLab workflow. Follow the real Duo session, MR 1 source diff and passed CI links. These demonstrate the separate AI source-repair workflow.
8. Optionally create an account, sign out and sign back in to test your persisted workspace. Another guest session cannot read your runs.

All scenarios use synthetic data. The reference sandbox performs no payment-provider calls. Its deterministic recovery is separate from the supervised GitLab Duo source repair.

## YouTube title

Aftercare | Your health check is green. Your customer was charged twice.

## YouTube description

A healthy service can still break a customer promise. Aftercare restores a safe revision, reconciles duplicate synthetic debits, verifies a bounded repair and preserves the evidence.

Try the product: https://aftercare-release.web.app
Source and setup: https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare
Actual GitLab Duo session: https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions/9737653
AI-generated repair: https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/merge_requests/1
Passed full repair pipeline: https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966905048

The public reference sandbox uses synthetic credits, reviewed deterministic repairs and real tests and HTTP checks. GitLab Duo independently investigated and repaired the source, with a human reviewing the outcome. No real payments or refunds occur.

Created and directed by Shivam Gupta with AI-assisted engineering and review. MIT licensed.

## Submission choices and final checks

- Select Path A: Start Fresh and Supervised. The public reference sandbox is hands-off within its isolated fixtures; the GitLab source-repair workflow has human outcome review.
- Select the nine lifecycle stages supported by the actual operations and CI evidence: plan, create, verify, package, secure, release, configure, monitor and govern.
- Supply the public MIT GitLab repository, the final product URL and the publicly viewable YouTube URL. Deployment code is included for the Google Cloud bonus.
- Do not opt into the Environmental Impact prize without a measured SCI baseline. No carbon reduction or validated customer demand is claimed.
- Review all saved fields in the existing draft, watch the full final video signed out, and complete the actual final submission before the event deadline. Retain its confirmation.
