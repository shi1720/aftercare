# Aftercare

**Your health check is green. Your customer was charged twice.**

Aftercare closes the gap between a healthy deployment and a correct customer outcome. It detects a broken customer promise, restores a safe revision, reconciles damage in a synthetic ledger, tests a bounded repair, and preserves the evidence of recovery.

Built by **Shivam Gupta** for GitLab Transcend 2026. **Path A · Supervised GitLab repair workflow.** The public reference sandbox runs its bounded loop hands-off. This distinction is visible in the product.

- [Live Google Cloud app](https://aftercare-release.web.app)
- [Watch the 2:10 product demo](https://www.youtube.com/watch?v=ZqhwnJsPLQs)
- [Public GitLab project](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare)
- [CI/CD history](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/pipelines)
- [Executed Duo session](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/automate/agent-sessions/9737653)
- [AI-generated repair MR](https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare/-/merge_requests/1)
- [MIT license](LICENSE) · [Security boundaries](SECURITY.md)

## The customer problem

A retry can create two charges while every request returns HTTP 200. A rollback prevents more duplicates but leaves existing duplicates in the ledger. Platform engineers then coordinate application repair, finance reconciliation, regression tests and incident evidence by hand.

Aftercare starts with one precise promise: **one tenant + one idempotency key + one amount produces one net debit**. It also tests tenant isolation and conflicting retries. Its intended buyer is an engineering team running transaction-heavy SaaS on GitLab. Commercial assumptions and competitive positioning are documented in [the product brief](docs/product-brief.md).

## Try it

Open the deployed URL in [deployment evidence](docs/deployment.md), then choose **Open sandbox**. No API key or payment account is needed. You may also register an account to retain your own history. The demo processes synthetic credits only.

1. Run **Duplicate charge**. Watch actual subprocess tests reproduce the fault while a real loopback HTTP health probe returns 200.
2. Inspect the safe revision switch and append-only reversal entries. Replaying reconciliation must add no further reversal.
3. Watch the repaired source pass contract tests and 32 synthetic HTTP requests before promotion. Open the source diff and download the evidence and ledger.
4. Run **Unsafe repair**. The AST policy blocks the candidate before execution and verifies that the safe revision remains active.

**Two execution modes, clearly separated:**

| Mode | What actually executes | Authority |
| --- | --- | --- |
| Public reference sandbox | Reviewed deterministic templates, real Python subprocess tests, loopback HTTP traffic, synthetic ledger reconciliation, artifact sealing, pointer promotion and postcheck | Hands-off inside an isolated fixture only. Zero model calls. |
| GitLab Duo flow | AI triage of a checked-in fault, source repair, added regression test, verification and repair MR using GitLab tools | Supervised. MR 1 was reviewed, tested and merged into main. No live processor or automatic real deployment. |

The **GitLab workflow** page retrieves real public pipeline and repair-MR metadata from the fixed public project, with explicit stale/error states and direct links to the registered flow and actual Duo session. It uses no private token. The interface does not impersonate a GitLab session. A repository YAML file alone does not mean a flow ran. Actual external execution evidence belongs in [the evidence status](docs/evidence-status.md).

## Run locally

Requires Python 3.12+, Node 22+, and npm. No model API keys are needed for the reference sandbox.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd web
npm ci
npm run build
cd ..
DATA_DIR=./var APP_ORIGIN=http://localhost:8080 uvicorn server.main:app --host 127.0.0.1 --port 8080
```

Open http://localhost:8080. The production server serves both the built UI and `/api/` routes. Local users, sessions and runs persist in `var/aftercare.sqlite3`. Do not commit that directory. For frontend development, run `npm run dev` inside `web/`; Vite proxies API requests to port 8080.

```bash
python -m pytest tests -q
python scripts/check_submission.py
python scripts/incident.py evidence --output artifacts/reference
python scripts/incident.py reproduce --fixture seeded --output artifacts/seeded-fault
python scripts/incident.py verify --fixture current --output artifacts/repair
```

The current checkout contains the reviewed Duo repair and its regression tests, so `verify --fixture current` must pass on main. The original incident is preserved at `examples/checkout/baselines/duplicate-charge.py`; `reproduce --fixture seeded` checksum-checks that source, copies it into an isolated temporary directory with the unchanged acceptance tests and current regressions, and exits zero only when the fault produces actual failing tests and duplicate captures. It never overwrites current source. `verify --fixture seeded` must fail. Reproduction defaults to `seeded`; verification defaults to `current`.

## GitLab Duo Agent Platform setup

The project must have Duo access and a supported runner. Read [GitLab's custom flow documentation](https://docs.gitlab.com/user/duo_agent_platform/flows/custom/). The `.gitlab/duo/agent-config.yml` uses the managed execution environment and installs pinned Python dependencies. Configuration is read from the default branch.

1. In the project, go to **AI > Flows > New flow**.
2. Name it **Aftercare** and paste `gitlab/flows/aftercare.yml`. The flow uses two `AgentComponent`s: incident triage and source repair. It explicitly passes the trigger context and project ID.
3. Create and enable it for this project, then add a **mention** or **assignment** trigger. Use the service-account handle GitLab actually displays.
4. For a new incident, create an issue describing an actual current-source regression and invoke the flow. Do not include secrets or customer records. The original checkout incident has already been repaired; an agent must report that no new repair is needed if current verification passes. The historical source-repair execution remains inspectable through its immutable session and MR links.
5. Inspect the real session, resulting repair MR and branch pipeline. A new repair branch is `aftercare/repair-*`. CI enforces a path allowlist, regression coverage and unchanged verifier/policy. The seeded incident baseline remains protected evidence, not the current service implementation.

Prompt instructions are supported by executable gates. They are not a substitute for GitLab permissions. Custom CI variables are not automatically available to Duo execution. Do not put cloud or payment secrets in the flow YAML.

## Lifecycle coverage

| Stage | Concrete operation and evidence |
| --- | --- |
| Plan | Reproduce incident, identify failing invariant, record customer-impact scope and permitted recovery intent |
| Create | Duo writes a source repair and regression test; reference mode selects a reviewed template and says so |
| Verify | Execute business and adversarial contracts against the candidate in a separate Python process |
| Package | Build the tested fixture into a digest-bound release archive with a scoped CycloneDX manifest |
| Secure | Restrict AST capabilities before execution; enforce repair changed-path policy; audit Python dependencies in CI |
| Release | Replay real loopback HTTP canary requests, verify bundle/source identity, promote only a verified sandbox revision |
| Configure | Apply bounded runtime configuration and record the active revision pointer |
| Monitor | Independently retest the promoted revision; distinguish HTTP health from customer promises |
| Govern | Record the decision, compensation ledger, source/artifact hashes and a verifiable event hash chain |

CI has jobs for these operations, frontend build, application tests and evidence retention. Stage labels alone are not presented as proof of coverage.

## Architecture and persistence

React + TypeScript + Vite UI; FastAPI API; bounded Python reference controller; SQLite for local use; a dedicated named Firestore database in cloud mode. All run reads and downloads check the session owner. The UI polls real backend state and starts without fabricated history.

The candidate sources are fixed first-party fixtures, not arbitrary visitor-supplied code. The API accepts a scenario enum, not shell commands or URLs. See [SECURITY.md](SECURITY.md) for the exact boundary and outstanding production work.

Cloud mode stores users, hashed sessions, run evidence and bounded artifacts in Firestore. Use one Cloud Run instance and one worker because execution locks are process-local. A stale interrupted workflow fails closed. This release does not provide a distributed durable workflow engine or real payment compensation adapter.

## Google Cloud deployment

The included multistage Dockerfile builds the UI and runs the backend as a non-root user. Deployment scripts create a dedicated identity and database, scope database access with an IAM condition, and configure scale-to-zero with one maximum instance.

```bash
export GOOGLE_CLOUD_PROJECT=your-billing-enabled-project
./deploy/setup-google-cloud.sh
./deploy/google-cloud.sh
```

Google Cloud must have billing enabled. Cloud Run and the named Firestore database can incur charges, even though local use needs no paid service. No model or processor credential is included. See [deployment evidence and operating limits](docs/deployment.md).

## Evidence and claims

Evidence is a SHA-256 chain, **not a cryptographic signature**. It detects changes relative to a trusted chain head. Do not treat it as a compliance certification. Ledger amounts are synthetic test credits. Duration and test/request counts are measured. No customer, revenue, avoided-loss or carbon reduction is invented.

The commercial model is a hypothesis to validate: open-source contracts and controller, paid managed evidence retention and team governance. Existing rollout and synthetic-monitoring products already address adjacent problems. Aftercare's proposed wedge is closing already-created business harm and linking the proof to a GitLab repair.

## Author and license

Created and directed by **Shivam Gupta**, with AI-assisted engineering and review. [MIT](LICENSE). Commit sign-offs follow the [Developer Certificate of Origin 1.1](https://developercertificate.org/). No prior project was imported into Path A.

## Firebase deployment

The canonical public application is https://aftercare-release.web.app. Firebase Hosting serves the frontend and proxies API requests to the Cloud Run control plane. Sessions use the Firebase-compatible HttpOnly `__session` cookie.

After setting up the named Firestore database and runtime identity as described in `docs/deployment.md`, deploy with:

```sh
GOOGLE_CLOUD_PROJECT=your-project bash deploy/firebase.sh
```

This builds the frontend, deploys the Cloud Run backend with exact allowed origins, and publishes a digest-bound Firebase Hosting version. It uses your signed-in gcloud identity and stores no deployment token in source. For a different site name, set `FIREBASE_SITE`; site names must be globally unique. Runtime API documentation is available at `/api/docs` with a self-hosted explorer under the same security policy.
