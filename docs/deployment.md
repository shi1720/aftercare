# Deployment and operating limits

Google Cloud deployment is in progress. The final public service URL and verified revision will be recorded here after a successful health and browser check.

The deployment uses a new Cloud Run service named aftercare and a dedicated named Firestore database, with a runtime service account limited to that database. Other existing services in the hosting project are outside the scope of this application.

Local mode remains fully usable without Google Cloud or model credentials. Cloud Run uses minimum zero and maximum one instance, one Python worker, 512 MiB memory and bounded sandbox workloads. Firestore stores account/session/run/evidence records and bounded artifact bytes. Raw credentials are not stored in the container image or source.

The named Firestore database is not covered by a default-database free tier. Cloud Run, builds, artifact storage and Firestore operations can incur usage charges. No claim of zero hosting cost is made. Production volumes require a cost budget, data retention plan, backup validation and a distributed task design before increasing instance count.

No real customer payments, refunds or tenant records are used. This deployment is the publicly testable reference product; the separate GitLab Duo flow produces a repair merge request for review.
