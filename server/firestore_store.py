"""Durable optional Google Cloud store, isolated to a named Firestore database.

Only fixed Aftercare collections are used. Artifact documents are bounded well
below Firestore's 1 MiB document limit. Cloud Run must use a single instance and
single worker because execution locks are process-local.
"""
import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import firestore

from .evidence import canonical, event_hash


class FirestoreStore:
    def __init__(self, root, project, database="aftercare"):
        if database == "(default)":
            raise ValueError("Use a dedicated named Firestore database for Aftercare")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.client = firestore.Client(project=project, database=database)
        self.prefix = "aftercare_v1_"

    def collection(self, name):
        return self.client.collection(self.prefix + name)

    def health(self):
        # Read-only connectivity check. It does not create an infrastructure doc.
        self.collection("metadata").document("health").get(timeout=5)

    def create_user(self, user_id, name, email, password=None, demo=False):
        user_ref = self.collection("users").document(user_id)
        email_ref = self.collection("emails").document(hashlib.sha256(email.encode()).hexdigest())

        @firestore.transactional
        def create(transaction):
            if email_ref.get(transaction=transaction).exists:
                raise sqlite3.IntegrityError("Email already registered")
            transaction.create(user_ref, {"id": user_id, "name": name, "email": email, "password": password, "demo": int(demo)})
            transaction.create(email_ref, {"user_id": user_id})
        create(self.client.transaction())

    def user_by_email(self, email):
        lookup = self.collection("emails").document(hashlib.sha256(email.encode()).hexdigest()).get().to_dict()
        return self.collection("users").document(lookup["user_id"]).get().to_dict() if lookup else None

    def session_user(self, hashed_token, current):
        session = self.collection("sessions").document(hashed_token).get().to_dict()
        if not session or session["expires"] <= current:
            return None
        return self.collection("users").document(session["user_id"]).get().to_dict()

    def put_session(self, hashed_token, user_id, expires, previous=None):
        batch = self.client.batch()
        if previous:
            batch.delete(self.collection("sessions").document(previous))
        batch.set(self.collection("sessions").document(hashed_token), {"user_id": user_id, "expires": expires, "expiresAt": datetime.fromtimestamp(expires, timezone.utc)})
        batch.commit()

    def delete_session(self, hashed_token):
        self.collection("sessions").document(hashed_token).delete()

    def check_rate_limit(self, key, limit, seconds, current):
        ref = self.collection("rate_limits").document(hashlib.sha256(key.encode()).hexdigest())

        @firestore.transactional
        def consume(transaction):
            row = ref.get(transaction=transaction).to_dict()
            if row and current-row["window"] < seconds:
                if row["count"] >= limit:
                    return False
                transaction.update(ref, {"count": row["count"]+1})
            else:
                transaction.set(ref, {"count": 1, "window": current, "expiresAt": datetime.fromtimestamp(current+86400, timezone.utc)})
            return True
        return consume(self.client.transaction())

    def run_count(self, user_id=None):
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.collection("runs")
        if user_id:
            query = query.where(filter=FieldFilter("user_id", "==", user_id))
        result = query.count().get()
        return int(result[0][0].value)

    def save_run(self, user_id, run):
        self.collection("runs").document(run["id"]).set({"user_id": user_id, "body": json.dumps(run), "updatedAt": time.time()}, merge=True)

    def seal_run(self, user_id, run):
        if run["status"] == "running" or not run.get("completedAt"):
            raise ValueError("Only completed runs can be sealed")
        ref = self.collection("runs").document(run["id"])
        seal = hashlib.sha256(canonical(run)).hexdigest()

        @firestore.transactional
        def seal_final(transaction):
            current = ref.get(transaction=transaction).to_dict()
            if not current or current["user_id"] != user_id:
                raise ValueError("Run owner mismatch")
            if current.get("sealedSha256") and current["sealedSha256"] != seal:
                raise ValueError("Completed run seal is immutable")
            transaction.update(ref, {"body": json.dumps(run), "sealedSha256": seal, "updatedAt": time.time()})
        seal_final(self.client.transaction())

    def seal_matches(self, user_id, run):
        row = self.collection("runs").document(run["id"]).get().to_dict()
        return bool(row and row["user_id"] == user_id and row.get("sealedSha256") == hashlib.sha256(canonical(run)).hexdigest())

    def _run_body(self, row):
        if not row:
            return None
        run = json.loads(row["body"])
        if run["status"] != "running" or time.time()-row["updatedAt"] <= 180:
            return run
        ref = self.collection("runs").document(run["id"])

        @firestore.transactional
        def expire_stale(transaction):
            # Re-read inside the transaction: a stale list snapshot must never
            # overwrite an execution that has since completed or renewed its lease.
            fresh = ref.get(transaction=transaction).to_dict()
            if not fresh or fresh["user_id"] != row["user_id"]:
                raise ValueError("Run owner mismatch")
            current = json.loads(fresh["body"])
            if current["status"] != "running" or time.time()-fresh["updatedAt"] <= 180:
                return current
            current["status"] = "failed"
            current["after"]["healthStatus"] = "unverified"
            current["after"]["contractStatus"] = "unverified"
            current["completedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            current["decision"] = {"outcome": "stopped", "reason": "Controller lease expired. No unverified candidate can be promoted. Start a new isolated run."}
            event = {"id": "lease-expired", "at": current["completedAt"], "stage": "govern", "title": "Controller lease expired", "detail": current["decision"]["reason"], "kind": "error", "previousHash": current["events"][-1]["hash"] if current["events"] else "0"*64}
            event["hash"] = event_hash(event)
            current["events"].append(event)
            for stage in current["stages"]:
                if stage["status"] in ("pending", "running"):
                    stage.update(status="blocked", detail="Controller lease expired before completion")
            transaction.update(ref, {"body": json.dumps(current), "updatedAt": time.time(), "sealedSha256": hashlib.sha256(canonical(current)).hexdigest()})
            return current
        return expire_stale(self.client.transaction())

    def run(self, user_id, run_id):
        row = self.collection("runs").document(run_id).get().to_dict()
        return self._run_body(row) if row and row["user_id"] == user_id else None

    def runs(self, user_id):
        from google.cloud.firestore_v1.base_query import FieldFilter
        rows = self.collection("runs").where(filter=FieldFilter("user_id", "==", user_id)).limit(100).stream()
        runs = [self._run_body(row.to_dict()) for row in rows]
        return sorted(runs, key=lambda run: run["createdAt"], reverse=True)

    def put_artifact(self, run_id, name, data):
        if len(data) > 500_000:
            raise ValueError("Artifact exceeds bounded document storage limit")
        self.collection("artifacts").document(run_id + "--" + name).set({"data": data, "run_id": run_id, "name": name})

    def get_artifact(self, run_id, name):
        row = self.collection("artifacts").document(run_id + "--" + name).get().to_dict()
        return row["data"] if row else None
