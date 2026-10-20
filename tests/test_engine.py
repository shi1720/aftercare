import copy
import json
import threading

import pytest

from server.engine import Controller, digest, new_run, reconcile, security_gate
from server.evidence import verify_chain
from server.sandbox import SAFE_SOURCE, UNSAFE_SOURCE
from server.store import Store


@pytest.mark.parametrize("scenario,status", [("duplicate-charge", "recovered"), ("tenant-leak", "recovered"), ("unsafe-repair", "blocked")])
def test_real_release_recovery(tmp_path, scenario, status):
    store = Store(tmp_path)
    with store.connection() as conn:
        conn.execute("INSERT INTO users(id,name,email) VALUES('owner','Owner','owner@example.com')")
    controller = Controller(store)
    run = new_run(scenario)
    controller.user_lock("owner").acquire()
    controller.execute("owner", run)
    assert run["status"] == status, run["decision"]
    assert run["metrics"]["modelCalls"] == 0
    assert run["metrics"]["testsPassed"] == run["metrics"]["testsTotal"] == 7
    assert run["metrics"]["requestsReplayed"] >= 52
    assert run["metrics"]["canaryRequests"] == 32
    assert run["metrics"]["stabilityRequests"] >= 20
    assert run["metrics"]["totalRequests"] > run["metrics"]["requestsReplayed"]
    assert run["before"]["healthStatus"] == "healthy"
    assert run["after"]["healthStatus"] == "healthy"
    assert verify_chain(run["events"])
    assert not controller.user_lock("owner").locked()
    persisted = store.run("owner", run["id"])
    assert persisted["status"] == status
    folder = tmp_path / "runs" / run["id"]
    active = json.loads((folder / "active-revision.json").read_text())
    assert active["revision"] == digest(SAFE_SOURCE.encode())
    ledger = json.loads((folder / "synthetic-ledger.json").read_text())
    assert sum(x["amount"] for x in ledger["entries"]) == 4200
    if scenario == "duplicate-charge":
        assert run["metrics"]["duplicateCharges"] == 23
        assert sum(x.get("kind") == "reversal" for x in ledger["entries"]) == 23
    if scenario == "unsafe-repair":
        assert active["source"] == "safe.py"
        assert not (folder / "release.zip").exists()
        assert not (folder / "contracts-candidate.json").exists()
    else:
        assert active["source"] == "candidate.py"
        assert all(stage["status"] == "passed" for stage in run["stages"])
        assert (folder / "release.zip").is_file()


def test_reconciliation_is_append_only_and_exactly_once():
    debits = [{"id": str(i), "tenant": "alice", "key": "k", "amount": 500} for i in range(4)]
    reconciled = reconcile(debits)
    assert reconciled[:4] == debits
    assert len(reconciled) == 7
    assert sum(e["amount"] for e in reconciled) == 500
    assert reconcile(debits, reconciled) == reconciled


def test_reconciliation_tenant_scoped():
    entries = [{"id": "a", "tenant": "alice", "key": "same", "amount": 5}, {"id": "b", "tenant": "bob", "key": "same", "amount": 5}]
    assert reconcile(entries) == entries


def test_ast_gate_blocks_execution_capabilities():
    assert security_gate(SAFE_SOURCE)["passed"]
    for source in [UNSAFE_SOURCE, "x = __import__('os')", "print('no')", "x = object.__subclasses__()", "exec('x')", "def x(:"]:
        assert not security_gate(source)["passed"]


def test_evidence_tamper_detection(tmp_path):
    from server.evidence import event_hash
    event = {"id": "1", "previousHash": "0" * 64, "detail": "original"}
    event["hash"] = event_hash(event)
    assert verify_chain([event])
    tampered = copy.deepcopy(event)
    tampered["detail"] = "changed"
    assert not verify_chain([tampered])
    assert not verify_chain([event, event])


def test_failure_retains_safe_revision(tmp_path, monkeypatch):
    store = Store(tmp_path)
    with store.connection() as conn:
        conn.execute("INSERT INTO users(id,name,email) VALUES('owner','Owner','owner@example.com')")
    import server.engine as engine
    monkeypatch.setattr(engine.subprocess, "run", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("sandbox timed out")))
    run = new_run("duplicate-charge")
    Controller(store).execute("owner", run)
    assert run["status"] == "failed"
    assert "timed out" in run["decision"]["reason"]
    active = json.loads((tmp_path / "runs" / run["id"] / "active-revision.json").read_text())
    assert active["source"] == "safe.py"
    assert verify_chain(run["events"])


def test_reconciliation_rejects_tampered_or_foreign_reversals():
    from server.engine import validate_reconciliation
    ledger = [{"id": "a", "tenant": "alice", "key": "k", "amount": 5}, {"id": "b", "tenant": "alice", "key": "k", "amount": 5}]
    valid = reconcile(ledger)
    for mutation in [lambda entries: entries[0].update(amount=99), lambda entries: entries[-1].update(tenant="bob"), lambda entries: entries.append(copy.deepcopy(entries[-1])), lambda entries: entries[-1].update(reverses="unknown")]:
        invalid = copy.deepcopy(valid)
        mutation(invalid)
        with pytest.raises(ValueError):
            validate_reconciliation(ledger, invalid)


def test_artifact_persistence_failure_revokes_promotion(tmp_path, monkeypatch):
    store = Store(tmp_path)
    store.create_user("owner", "Owner", "owner@example.com")
    controller = Controller(store)
    run = new_run("duplicate-charge")
    store.save_run("owner", run)
    calls = []
    def storage_failure(run_id, name, data):
        calls.append(name)
        if len(calls) == 2:
            raise OSError("Storage failed after one successful upload")
    monkeypatch.setattr(store, "put_artifact", storage_failure)
    controller.user_lock("owner").acquire()
    controller.execute("owner", run)
    assert run["status"] == "failed"
    assert not controller.user_lock("owner").locked()
    active = json.loads((tmp_path / "runs" / run["id"] / "active-revision.json").read_text())
    assert active["source"] == "safe.py"
    assert run["after"]["contractStatus"] == "unverified"
    assert [artifact["name"] for artifact in run["artifacts"]] == ["release.zip"]
    assert store.seal_matches("owner", run)
    assert verify_chain(run["events"])
    assert next(stage for stage in run["stages"] if stage["id"] == "govern")["status"] == "failed"


def test_malformed_evidence_is_rejected_without_crashing():
    assert not verify_chain(None)
    assert not verify_chain({"events": []})
    assert not verify_chain(["not an event"])
    assert not verify_chain([{"previousHash": "0" * 64, "hash": "invalid", "value": float("nan")}])
