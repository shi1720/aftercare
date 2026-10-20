# Backend implementation notes

Aftercare is authored by Shivam Gupta. This server is an executable **deterministic reference controller**, not a local LLM. The GitLab Duo integration lives separately in `gitlab/`. The public dashboard does not imply a connected integration has run.

## Launch

Python 3.12 is the supported runtime. From the repository root:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --host 0.0.0.0 --port 8080 --workers 1
```

Build `web/` first to serve the dashboard. `/healthz` and `/api/health` check datastore readiness. API schema is `/api/docs`. SQLite uses `DATA_DIR` (default `.data/`). Mount a persistent volume when using SQLite beyond a local session. Never run multiple server workers against the reference controller's process-local execution locks.

## Cloud durability

Set `AFTERCARE_STORE=firestore`, `GOOGLE_CLOUD_PROJECT`, and `FIRESTORE_DATABASE=aftercare` to use the dedicated **named** database. The default Firestore database is intentionally rejected. Collections use the `aftercare_v1_` prefix. Users, salted scrypt password hashes, hashed session tokens, run evidence, quotas, and small artifact bytes persist in Firestore. Source execution directories remain ephemeral per-run sandboxes. Artifact integrity is checked against its recorded digest on download.

Cloud Run must use **one instance, one worker**, request-based CPU throttling disabled for background jobs, and `COOKIE_SECURE=true`. Set `APP_ORIGIN` to the exact public HTTPS origin. The runtime service account needs datastore access restricted to the dedicated database. The SDK uses workload identity, not a committed service-account key. Configure a Firestore TTL policy on sessions/rate_limits `expiresAt` for optional storage cleanup; expiry is independently enforced in code.

This is a bounded hackathon deployment. To support multiple instances, move execution into a durable queue with transactional leases; add account verification/recovery, organization access control, retention controls, and an independent evidence witness before handling customer workloads. SQLite and Firestore store selection do not change the sandbox scope.

## What actually executes

Each run owns a UUID directory and first-party Python source revisions. The controller selects a fault-injected revision, executes seven behavioral unit contracts in a subprocess, sends real loopback HTTP traffic, measures a green health probe while business behavior fails, and switches the active sandbox revision pointer to known safe source. It independently verifies that rollback before building one bounded repair.

Security checks reject unapproved AST capabilities **before** loading the candidate. Passing candidates run the contracts, receive a SHA-256 bundle and scoped CycloneDX SBOM, serve 32 behavioral loopback requests plus a separately counted health probe, are promoted by atomic pointer update, then run an independent post-promotion test suite. Rejected candidates are never imported, tested, packaged, or promoted. The verified safe revision is retained.

The ledger contains **synthetic test credits**. Append-only reversals reconcile observed extra debits once per original debit. Invariants enforce tenant/key conservation, original history preservation, and unique referenced reversals. No payment processor or real customer account is contacted.

No user-provided source code, URL, shell command, or file path is executed. The AST checker is a narrow policy for these fixtures; it is not a general sandbox for arbitrary hostile Python. Runtime fixture manifests explicitly cover only the fixture's dependency-free source, rather than claiming to scan the entire control plane.

## Evidence and limitations

Every event includes its predecessor and SHA-256 hash. Downloads include the complete source diff, measured subprocess outcomes, loopback traffic ledger, decision, run manifest digest, and chain head. Download routes recheck ownership, chain validity, and artifact hashes. A hash chain establishes integrity **relative to a trusted head**; it does not establish external identity, trusted time, or an independently witnessed execution. Export the chain head to an external append-only witness for stronger audit guarantees.

All counts come from observed tests and requests. No financial savings, energy savings, emissions reduction, or external CI/deployment outcome is fabricated. `modelCalls=0` in reference mode. `requestsReplayed` counts final candidate or kept revision behavioral requests, including stability sampling. `canaryRequests=32` is the initial behavioral replay. `stabilityRequests` counts repeated checkout and tenant-boundary checks during a genuine five-second observation window. `healthProbes` and `totalRequests` count all run probes and all HTTP requests respectively; baseline and rollback requests are included in totalRequests. Additional baseline and rollback requests appear in event evidence.

## Safety bounds and checks

Only three known scenarios are accepted. Each user may have one active recovery, the process may run four recoveries concurrently, each run has a fixed 20-second subprocess timeout and a two-attempt policy ceiling (reference mode uses one), runs are rate-limited and quota-limited, mutations require same-origin JSON, cookies are HttpOnly/SameSite Strict, and sessions expire after seven days. Passwords use scrypt with random salts. Interrupted work fails closed rather than appearing complete. A stale Firestore run lease expires after 180 seconds.

```sh
python -m pytest tests -q
uvx pip-audit -r requirements.txt
```
