# Verified Google Cloud deployment

**Public URL:** https://aftercare-359201230061.us-central1.run.app

The live application runs on Google Cloud Run in `us-central1`, with a dedicated named Firestore database (`aftercare`) and a dedicated runtime service account. Its `roles/datastore.user` grant has an IAM condition limiting access to that named database. No personal GitLab token is stored in the service. Public GitLab evidence uses fixed read-only public API endpoints.

The Dockerfile, provisioning, identity condition and deployment scripts are included under `deploy/`. The existing hosting project is shared infrastructure; the Aftercare service, database and identity are new and isolated from its other services.

## Verified behavior

The public health endpoint reached Firestore successfully. A cloud smoke test completed duplicate-charge recovery, distinguished real HTTP 200 health from the failed business invariant, verified all downloadable artifact hashes, denied cross-guest run access, and exercised registration, login and logout. Exact observed counters are in [cloud-smoke-results.json](cloud-smoke-results.json), including wall-clock duration. Counters refer to synthetic requests, not real protected customers.

## Runtime and cost limits

Cloud Run uses minimum zero and maximum one instance, one Python worker, 512 MiB memory and bounded sandbox workloads. CPU throttling is disabled so a background recovery can finish after its HTTP 202 response. Scale-to-zero remains enabled. The named Firestore database persists accounts, hashed sessions, runs, seals and bounded artifact bytes across container replacements.

The named Firestore database is not covered by a default-database free tier. Cloud Run, builds, artifact storage and Firestore operations can incur usage charges. No zero-cost hosting or measured carbon reduction is claimed. Local use needs no cloud or model service. Keep a billing budget and review usage if the public demo receives substantial traffic.

Execution coordination remains single-process. Do not increase instance/worker count without a distributed lease and task design. Stale interrupted work fails closed. General payment-processor adapters, organization SSO, account recovery, independent audit signing, validated backups and an incident-response operating service remain outside this release.

No real customer payments, refunds or tenant records are used. The GitLab source-repair workflow is supervised and leaves the MR open for review.
