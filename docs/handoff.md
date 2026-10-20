# Aftercare launch handoff

Created and directed by **Shivam Gupta**, with AI-assisted engineering and review. Verified October 20, 2026.

## Open the product

- [Live application](https://aftercare-release.web.app): use the guest sandbox or create an account. Choose a scenario, launch it, inspect its gates and download its evidence.
- [Public MIT source](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare): application, tests, CI, custom Duo configuration and Google Cloud/Firebase deployment scripts.
- [Finished Duo session](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions/9737653), [merged repair MR !1](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/merge_requests/1), [main pipeline history](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines?ref=main).

Path A, **Supervised**. The actual AI repair was reviewed, rebased, tested and merged into main. Its source branch was deleted after the passing merge pipeline. The merged pipeline ran 11 jobs across nine lifecycle stages and passed all 66 tests. Subsequent maintenance checks appear in the linked main history. See [evidence-status.md](evidence-status.md) for exact scopes.

## Video and submission

[Watch the public YouTube demo](https://www.youtube.com/watch?v=ZqhwnJsPLQs). The video is 129.74 seconds at 1080p with a standard Google Cloud synthetic voice, burned-in English captions and a separate uploaded English caption track. YouTube copyright and Community Guidelines checks found no issues. Public playback was checked at 1920x1080 and anonymous oEmbed metadata was available.

The complete mastered voiceover received an automated listening review for pronunciation, accent consistency and pacing. It was identified as neutral US English with no flagged pronunciation issues or awkward pauses. A brief audio peak was corrected; the final AAC master measures -17.83 LUFS and -1.15 dBTP. The picture, timing and captions were preserved. There is no music, fictional customer claim or payment-provider activity.

The [Devpost entry](https://devpost.com/submit-to/31503-life-after-code/manage/submissions/1247898-aftercare/finalization) shows **4/5 steps complete**. The project name, tagline, story, technology list, application/source links, public video URL, testing instructions, nine stages, branded cover and captioned gallery are saved. The owner supplied India as country of residence and confirmed the three eligibility statements; those fields are saved.

**The owner must complete the final step:** open the finalization page, review and accept its Official Rules and Terms of Service, then click **Submit project**. This final prize-entry action is reserved for the owner by the browser-control policy. No final entry has been submitted by the agent.

The supplied deadline is October 27, 2026, **13:00 UTC / 18:30 India time**. Check the event page before final submission. Keep the submitted source and materials unchanged from the deadline through the winners announcement. Continue later development in a separate fork.

## Scope and operations

The live service is a bounded reference sandbox. It runs real subprocess tests and loopback requests using first-party scenarios and reviewed deterministic repair templates. Credits are synthetic. It makes no payment-provider calls or model calls. GitLab Duo is the separate genuine AI workflow, with a completed session and merged source repair. The UI identifies this distinction.

The canonical deployment serves static assets from Firebase Hosting and forwards API requests to Cloud Run. Exact allowed origins include both Firebase aliases and both Cloud Run service aliases. Browser sessions, account ownership, CSRF checks, evidence hashes, unsafe repair refusal, responsive navigation and the first-party API explorer were exercised against the hosted service.

The deployment uses one Cloud Run instance with one worker, a dedicated Firestore database and a database-scoped runtime identity. In-flight tasks are not distributed durable jobs: deployment/restart can interrupt them, and stale runs fail closed. Do not redeploy during an active demonstration. Enterprise SSO, production payment adapters, independent signatures and an external queue remain future product work.

Cloud hosting may incur charges, especially the named Firestore database and non-throttled CPU while requests execute. No always-on minimum instance is configured. See [deployment.md](deployment.md) and [../deploy/firebase.sh](../deploy/firebase.sh) for operating controls. Keep the service live through judging, then decide whether to retain it.

The first-buyer and pricing proposal is a commercial hypothesis, not customer validation. The environmental prize is not claimed because no defensible SCI measurement has been made.
