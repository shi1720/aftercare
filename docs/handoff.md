# Aftercare — final handoff

Created and directed by **Shivam Gupta**, with AI-assisted engineering and review. Verified October 20, 2026.

## Open the product

- [Live Google Cloud application](https://aftercare-359201230061.us-central1.run.app): choose the guest sandbox or register/login. Run duplicate charge, tenant leak or unsafe repair; download the evidence and release artifacts.
- [Public GitLab source](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare): MIT license, setup, CI, custom Duo configuration and Google Cloud deployment code.
- [Finished Duo session](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions/9737653), [actual repair MR !1](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/merge_requests/1), [pipeline history](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines).

Path A, **Supervised**. The AI repair MR stays open for review. All nine lifecycle stages have concrete reference/application CI evidence; the MR acceptance job independently verifies the source repair. See [evidence-status.md](evidence-status.md) for immutable execution links and exact scopes.

## Finish the submission

1. Open the supplied `Aftercare-demo-silent.mp4` (155 seconds, 1080p). Read the [verbatim narration](video-script.md), following `Aftercare-narration.srt` timing. Record your own voice in a quiet room. The footage and captions are already edited; no new screen recording is required.
2. Place the recording beside the video and run `python3 Aftercare-finalize-video.py voice.wav` with ffmpeg installed, or add the narration in your video editor. Watch the entire final export and confirm that narration matches the scene timing. The script preserves the 155-second picture and pads short audio with silence; narration exceeding 155 seconds must be rerecorded or edited first.
3. Upload the finished video to YouTube, choose **Public**, and verify signed-out playback. No music or third-party artwork has been added. The recording shows necessary GitLab interface footage; inspect the current rules' treatment of platform marks before upload.
4. Open [Devpost submission management](https://devpost.com/submit-to/31503-life-after-code/manage/submissions). Draft creation failed twice because Devpost could not connect to reCAPTCHA. Complete that step in your browser, paste [the prepared submission fields](devpost-submission.md), attach the video URL and submit. **No Devpost entry has been submitted.**
5. Use October 27, 2026, **13:00 UTC / 18:30 India time** as the deadline stated in the supplied guidelines; check the event page before final submission. Keep submitted source and materials unchanged from the deadline through the winners announcement. Continue later work in a separate fork.

## Scope and operations

The live service is a bounded reference sandbox. It performs real subprocess tests and loopback requests, but accepts only first-party scenarios and reviewed repair templates. It makes no payment-provider calls. GitLab Duo is the separate genuine AI workflow; its repair is not automatically deployed to the public reference service.

The deployment uses one Cloud Run instance with one worker, a dedicated Firestore database and a database-scoped runtime identity. In-flight tasks are not distributed durable jobs: deployment/restart can interrupt them, and stale runs fail closed. Do not redeploy during a judged run. Enterprise SSO, production payment adapters, independent signatures and an external queue remain product development work, not shipped capabilities.

Cloud hosting may incur charges, especially the named Firestore database and non-throttled CPU while requests execute. No always-on minimum instance is configured. See [deployment.md](deployment.md) for operating limits and controls. Keep the service live through judging, then decide whether to retain it.

The first-buyer and pricing proposal is a commercial hypothesis, not customer validation. The environmental prize is not claimed because no defensible SCI measurement has been made.
