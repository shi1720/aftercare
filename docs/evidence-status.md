# Verified execution evidence

Verified on October 20, 2026. This file separates observed platform execution from the deterministic reference product. All links refer to actual resources.

| Requirement | Evidence |
| --- | --- |
| Public original Path A project | [Aftercare on GitLab](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare), created October 20, root MIT LICENSE |
| Registered and enabled custom Duo flow | [Aftercare flow 1018811](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/flows/1018811), service account `ai-aftercare-gitlab-ai-hackathon`, mention and assignment triggers |
| Actual Duo execution | [Finished session 9737653](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions/9737653), [successful workload pipeline 2966825574](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966825574) |
| Actual independently generated repair | [Merge request !1](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/merge_requests/1), source commit `fadd583d8a27769bb82bbb318e4c33a309a133a5`, exactly two permitted files changed |
| Repair acceptance | [Passed MR pipeline 2966834617](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966834617), 10 passing fixture/regression tests, protected original acceptance tests unchanged |
| Regression sensitivity | Independent replay of the five added regressions on the original source caused four failures; repaired source passes all ten tests |
| Full reference/application CI | [Passed full pipeline 2966841144](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966841144), all nine stages complete, source commit `b00c4663cbd6353d7755018cee9fc0e2dfaa68c6` |
| Local application validation | 39 tests pass, TypeScript/Vite production build passes, npm audit and Python advisory audit found no known vulnerabilities at verification time |
| Live Google Cloud product | [Public Aftercare app](https://aftercare-359201230061.us-central1.run.app); Cloud Run with dedicated named Firestore database and dedicated runtime identity |
| Cloud smoke test | [Measured result JSON](cloud-smoke-results.json): recovery, real healthy HTTP versus failed contract, 23 duplicate synthetic debits, artifact digest verification, guest ownership isolation, registration/login/logout |
| Reference recovery | Duplicate charge and tenant leak recover; unsafe executable capabilities blocked before candidate execution. Each run executes real subprocess tests, loopback HTTP checks, five-second observation and downloadable evidence. |
| Video | Verbatim narration and shot list ready in [video-script.md](video-script.md). A 155-second 1080p silent edit with captions and original-speed recovery/refusal recordings is prepared. Human voice recording and public YouTube upload remain pending. |
| Devpost | Copy ready in [devpost-submission.md](devpost-submission.md). Draft creation was blocked twice by a reCAPTCHA connection error. The user must complete Devpost entry and final submission. |

## What the evidence proves

The repair pipeline verifies source repair and its regression tests. The broader nine-stage recovery, packaging and synthetic compensation use the reference controller and full application pipeline. These are separate scopes and are labeled accordingly. Neither loop makes real payment refunds.

The public app's GitLab workflow page retrieves actual public pipeline and MR metadata. It links the real session without inventing a session status. The reference dashboard reports zero model calls because it uses deterministic known templates.

Hashes detect mutation relative to a trusted chain head. They do not provide an external signature or independently prove authorship. The completed run manifest separately seals metadata, the source diff and artifact list.

After rebasing MR !1, its current source is `815eed8a6f5f5a73453b71da5c9ebeb6e20491b5`; [acceptance pipeline 2966905098](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966905098) passes. The original AI-generated commit above remains the historical session evidence.

The rebased repair branch also passes [full pipeline 2966905048](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966905048): all 11 jobs across nine stages, including `ai_repair_contract` instead of the expected-fault job. This is distinct from the one-job MR acceptance pipeline.
