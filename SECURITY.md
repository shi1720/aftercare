# Security boundaries

Aftercare currently runs recovery against isolated, synthetic services and ledgers. It does not connect to a payment processor or reverse a real payment. Its public sandbox cannot deploy your repositories. No payment API keys are required.

## Trust model

- Each authenticated or guest session owns its own runs. Run IDs are identifiers, not authorization. Every read, artifact download and evidence export checks ownership.
- Passwords use a salted, memory-hard hash. Session credentials travel in HttpOnly cookies. Production sets Secure and SameSite cookies. Mutation routes validate origin. Rate limits and bounded workloads restrict expensive operations.
- Scenario names select reviewed fixture templates. Visitors cannot supply code, shell commands, target URLs or arbitrary filesystem paths. Candidate execution uses a timeout and restricted known source. This is not a general-purpose hostile-code execution sandbox.
- The controller enforces an allowlist and safety checks independently of agent prose. It restores the safe sandbox revision before candidate evaluation. The unsafe repair scenario demonstrates refusal.
- Ledger reconciliation uses append-only reversal entries and idempotent compensation identifiers. It checks conservation of net charges. Real processor integrations require separately authorized adapters, transaction boundaries, reconciliation and provider-specific guarantees.
- Evidence events form a SHA-256 hash chain with source and artifact digests. This detects mutation relative to a trusted digest. It is not a digital signature and does not defeat an attacker who can rewrite the entire chain and its trusted root. Export to an independent immutable store or sign with a separate key for stronger guarantees.
- GitLab issue text, diffs and logs are untrusted input. Agent instructions forbid executing embedded instructions, weakening policy or modifying the verifier. A checked changed-path policy and tests enforce the allowed scope of the example repair.

## Persistence and operations

Local mode uses a SQLite database in DATA_DIR. Production can use the dedicated named Firestore database. The deployed runtime has database access scoped to that database. No long-lived Google key is bundled. Cloud Run uses one worker and at most one instance because incident execution uses in-process coordination. A service restart fails an interrupted recovery closed. Run records remain, and the user can begin a new recovery. This is a bounded deployment design, not a distributed workflow engine.

Use managed identity, HTTPS, backups and a retention policy before storing business-sensitive evidence. Do not upload customer payloads, secrets or personal information to the public demo. The examples use generated IDs only. Account recovery, SSO, MFA, independent audit signing, distributed work queues, verified processor adapters and multi-region availability remain outside the current release.

Report a suspected issue privately to the repository owner before posting exploit details. Include reproduction instructions and affected revision. Never include passwords or tokens in an issue.
