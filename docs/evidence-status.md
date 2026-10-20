# Verified execution evidence

Verified October 20, 2026. The reference sandbox and GitLab AI source-repair workflow have distinct execution scopes.

| Requirement | Actual evidence |
| --- | --- |
| Public application | https://aftercare-release.web.app, Firebase Hosting with same-origin Cloud Run API and dedicated Firestore database |
| Public MIT source | https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare |
| Registered Duo flow | Flow 1018811, two agents with bounded repair instructions |
| Actual completed Duo session | [Session 9737653](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions/9737653) |
| Actual source repair | [MR 1, merged](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/merge_requests/1). Exactly service.py and a new regression file changed in the original agent proposal. The original contract was preserved. |
| Regression sensitivity | Four of five added regressions fail against the original source; repaired current source passes all ten business tests |
| Passed merged-main CI | [Pipeline 2967016054](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2967016054), source 879576e71576d4bf85bfba1892429419ddc28d32, 11 jobs across all nine stages, 66 application/integration tests |
| Passed full repair-branch CI | [Pipeline 2966905048](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines/2966905048), prior to merge. The merged source branch was deleted after checks passed. |
| Firebase end-to-end checks | [Measured results](firebase-smoke-results.json): both recovery cases, blocked unsafe candidate, login/logout, cookie round trip, ownership isolation, event chains, artifact digests, CSRF and missing-path behavior |
| Browser checks | Registration, private empty account workspace, session persistence, search, filter clearing, mobile navigation, run reloads, JSON previews and downloaded evidence; responsive layout at 390, 768 and 1440 pixels with no document overflow |
| API explorer | /api/docs loads its own assets and the live schema under self-only script CSP; a real hosted health request returned HTTP 200 |
| Product demo | [Public YouTube demo](https://www.youtube.com/watch?v=ZqhwnJsPLQs), 129.74 seconds, clear neutral US English narration, English captions, genuine recovery/refusal recordings and real GitLab evidence. YouTube checks found no issues. |
| Devpost draft | Existing entry 1247898, titled Aftercare. Project fields, public video URL, country and confirmed eligibility are saved. The draft shows 4/5 steps complete; final prize-entry submission requires the owner. |

## Boundaries

The browser sandbox performs real subprocess tests and loopback requests against fixed first-party fixtures. Its known repairs are deterministic and make zero model calls. GitLab Duo independently diagnosed and repaired checked-in source. Merging that source does not imply a production payment deployment.

Credits are synthetic. No processor or customer payment is contacted. Completed event chains and manifest seals detect mutation relative to a trusted head; they are not independent signatures or compliance certifications.

The original defective source is preserved as a hash-bound explicit baseline. Main now verifies the repaired current source as well as reproduction of that baseline. Historical session and original commit evidence remain available after the branch is removed.
