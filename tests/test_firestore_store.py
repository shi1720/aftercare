"""Transaction regression tests; live IAM/connectivity is validated separately."""
import copy
import json
import time
from types import SimpleNamespace

import pytest

from server.engine import new_run
from server.evidence import verify_chain
from server.firestore_store import FirestoreStore


class Snapshot:
    def __init__(self, row):
        self.row = row

    def to_dict(self):
        return copy.deepcopy(self.row)


def transaction_store(monkeypatch, fresh):
    import server.firestore_store as module
    monkeypatch.setattr(module.firestore, "transactional", lambda callback: callback)
    transaction = SimpleNamespace(writes=[], update=lambda ref, body: transaction.writes.append(body))
    ref = SimpleNamespace(get=lambda **kwargs: Snapshot(fresh))
    store = object.__new__(FirestoreStore)
    store.collection = lambda name: SimpleNamespace(document=lambda name: ref)
    store.client = SimpleNamespace(transaction=lambda: transaction)
    return store, transaction


def test_stale_snapshot_cannot_overwrite_completed_run(monkeypatch):
    old = new_run("duplicate-charge")
    stale = {"user_id": "alice", "body": json.dumps(old), "updatedAt": time.time()-200}
    completed = copy.deepcopy(old)
    completed["status"] = "recovered"
    fresh = {"user_id": "alice", "body": json.dumps(completed), "updatedAt": time.time()}
    store, transaction = transaction_store(monkeypatch, fresh)
    assert store._run_body(stale)["status"] == "recovered"
    assert transaction.writes == []


def test_lease_expiry_is_sealed_and_chain_valid(monkeypatch):
    run = new_run("duplicate-charge")
    stale = {"user_id": "alice", "body": json.dumps(run), "updatedAt": time.time()-200}
    store, transaction = transaction_store(monkeypatch, stale)
    result = store._run_body(stale)
    assert result["status"] == "failed"
    assert result["after"]["healthStatus"] == "unverified"
    assert verify_chain(result["events"])
    assert len(transaction.writes) == 1
    assert len(transaction.writes[0]["sealedSha256"]) == 64


def test_renewed_lease_cannot_be_expired(monkeypatch):
    run = new_run("duplicate-charge")
    stale = {"user_id": "alice", "body": json.dumps(run), "updatedAt": time.time()-200}
    fresh = dict(stale, updatedAt=time.time())
    store, transaction = transaction_store(monkeypatch, fresh)
    assert store._run_body(stale)["status"] == "running"
    assert transaction.writes == []


def test_firestore_default_database_rejected(tmp_path):
    with pytest.raises(ValueError, match="dedicated named"):
        FirestoreStore(tmp_path, "project", "(default)")


def test_firestore_save_cannot_change_owner_or_completed_seal(monkeypatch):
    import hashlib
    from server.evidence import canonical
    run = new_run("duplicate-charge")
    fresh = {"user_id": "alice", "body": json.dumps(run), "updatedAt": time.time()}
    store, transaction = transaction_store(monkeypatch, fresh)
    with pytest.raises(ValueError, match="owner mismatch"):
        store.save_run("bob", run)
    assert transaction.writes == []
    fresh["sealedSha256"] = hashlib.sha256(canonical(run)).hexdigest()
    modified = copy.deepcopy(run)
    modified["title"] = "tampered"
    with pytest.raises(ValueError, match="immutable"):
        store.save_run("alice", modified)
    assert transaction.writes == []


def test_firestore_health_has_a_short_non_retrying_deadline():
    captured = []
    reference = SimpleNamespace(get=lambda **kwargs: captured.append(kwargs))
    store = object.__new__(FirestoreStore)
    store.collection = lambda name: SimpleNamespace(document=lambda name: reference)
    store.health()
    assert captured == [{"timeout": 3, "retry": None}]
