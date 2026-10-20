# Aftercare

Your health check is green. Your customer was charged twice. Aftercare contains the harm, verifies the repair, and brings the proof to GitLab.

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
