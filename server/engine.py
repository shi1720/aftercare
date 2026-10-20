"""Bounded deterministic reference controller with executable release contracts.

The local controller repairs three known fixtures. AI diagnosis and GitLab
mutations belong to the separate Duo integration; this module never fakes them.
"""
import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .evidence import canonical, event_hash, verify_chain
from .sandbox import CANARY_RUNNER, DUPLICATE_SOURCE, SAFE_SOURCE, TENANT_SOURCE, TEST_RUNNER, UNSAFE_SOURCE

STAGES = ["plan", "create", "verify", "package", "secure", "release", "configure", "monitor", "govern"]
SCENARIOS = {
    "duplicate-charge": "A retry must never charge twice",
    "tenant-leak": "One tenant must never see another tenant’s order",
    "unsafe-repair": "Unsafe candidate blocked before execution",
}
POLICY = {
    "autonomy": "hands-off", "maxAttempts": 2, "allowedPaths": ["service/payments.py"],
    "requiredContracts": ["idempotency", "tenant-isolation", "input-validation"],
    "network": "loopback-only", "externalPayments": False, "failClosed": True,
    "execution": "Fixed first-party fixtures; no user-supplied executable code", "maxConcurrentRunsPerUser": 1, "maxConcurrentRunsSystem": 4,
}


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def security_gate(source):
    """Fail closed on any syntax outside the fixture's deliberately small subset."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"passed": False, "findings": ["Invalid Python syntax"]}
    findings = []
    allowed_builtins = {"ValueError", "isinstance", "int", "bool", "str", "len"}
    allowed_methods = {"append", "get"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.With, ast.AsyncWith, ast.Lambda, ast.Global, ast.Nonlocal, ast.Try, ast.Delete)):
            findings.append("Forbidden syntax: " + type(node).__name__)
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            findings.append("Dunder attribute access forbidden")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in allowed_builtins:
                findings.append("Unapproved call: " + node.func.id)
            elif isinstance(node.func, ast.Attribute) and node.func.attr not in allowed_methods:
                findings.append("Unapproved method: " + node.func.attr)
            elif not isinstance(node.func, (ast.Name, ast.Attribute)):
                findings.append("Indirect call forbidden")
    return {"passed": not findings, "findings": sorted(set(findings)), "scope": "Restricted AST allowlist for first-party Python fixture; not a general purpose security scanner"}


def reconcile(ledger, existing=None):
    """Append one compensating credit per extra synthetic debit; never delete history."""
    entries = copy.deepcopy(existing if existing is not None else ledger)
    seen_keys = set()
    reversed_ids = {entry["reverses"] for entry in entries if entry.get("kind") == "reversal"}
    for debit in ledger:
        identity = (debit["tenant"], debit["key"])
        if identity in seen_keys and debit["id"] not in reversed_ids:
            entries.append({"id": "reversal-" + debit["id"], "kind": "reversal", "reverses": debit["id"], "tenant": debit["tenant"], "key": debit["key"], "amount": -debit["amount"]})
            reversed_ids.add(debit["id"])
        seen_keys.add(identity)
    validate_reconciliation(ledger, entries)
    return entries


def validate_reconciliation(ledger, entries):
    if entries[:len(ledger)] != ledger:
        raise ValueError("Original debit history was altered")
    expected, actual = {}, {}
    ids = {entry["id"]: entry for entry in ledger}
    reversed_ids = set()
    for entry in ledger:
        expected.setdefault((entry["tenant"], entry["key"]), entry["amount"])
    for entry in entries:
        identity = (entry["tenant"], entry["key"])
        actual[identity] = actual.get(identity, 0) + entry["amount"]
        if entry.get("kind") == "reversal":
            original = ids.get(entry.get("reverses"))
            if not original or entry["reverses"] in reversed_ids or (original["tenant"], original["key"], -original["amount"]) != (entry["tenant"], entry["key"], entry["amount"]):
                raise ValueError("Invalid or duplicate compensating reversal")
            reversed_ids.add(entry["reverses"])
    if actual != expected:
        raise ValueError("Per-tenant checkout conservation failed")
    return True


def new_run(scenario):
    return {
        "id": str(uuid.uuid4()), "scenario": scenario, "title": SCENARIOS[scenario], "status": "running",
        "createdAt": now(), "stage": "plan", "events": [],
        "metrics": {"durationMs": 0, "testsPassed": 0, "testsTotal": 0, "requestsReplayed": 0, "duplicateCharges": 0, "modelCalls": 0, "artifactsReused": 0, "totalRequests": 0, "healthProbes": 0, "canaryRequests": 0, "stabilityRequests": 0},
        "before": {"revision": "fault-injected", "healthStatus": "unverified", "contractStatus": "unverified"},
        "after": {"revision": "last-known-good", "healthStatus": "unverified", "contractStatus": "pending-verification"},
        "artifacts": [], "diff": {"path": "service/payments.py", "before": "", "after": ""},
        "stages": [{"id": stage, "status": "pending", "detail": "Awaiting evidence"} for stage in STAGES],
        "decision": {"outcome": "investigating", "reason": "Running bounded recovery in an isolated synthetic payment sandbox"},
        "executionMode": "reference", "policy": copy.deepcopy(POLICY),
    }


class Controller:
    def __init__(self, store):
        self.store = store
        self.locks = {}
        self.lock = threading.Lock()

    def user_lock(self, user_id):
        with self.lock:
            return self.locks.setdefault(user_id, threading.Lock())

    def execute(self, user_id, run):
        try:
            self._execute(user_id, run)
        except Exception as exc:
            run["status"] = "failed"
            run["completedAt"] = now()
            run["decision"] = {"outcome": "stopped", "reason": "Controller storage or startup failure: " + type(exc).__name__}
            event = {"id": str(uuid.uuid4()), "at": run["completedAt"], "stage": "govern", "title": "Controller persistence failure", "detail": run["decision"]["reason"], "kind": "error", "previousHash": run["events"][-1]["hash"] if run["events"] else "0"*64}
            event["hash"] = event_hash(event)
            run["events"].append(event)
            self.store.seal_run(user_id, run)
        finally:
            lock = self.user_lock(user_id)
            if lock.locked():
                lock.release()

    def _execute(self, user_id, run):
        started = time.monotonic()
        folder = self.store.root / "runs" / run["id"]
        folder.mkdir(parents=True, exist_ok=True)
        source = folder / "payments.py"
        safe = folder / "safe.py"
        safe.write_text(SAFE_SOURCE)
        state_path = folder / "active-revision.json"
        atomic_json(state_path, {"revision": digest(SAFE_SOURCE.encode()), "source": "safe.py"})

        def persist(seal=False):
            if not seal:
                run["metrics"]["durationMs"] = round((time.monotonic()-started)*1000)
            snapshot = run
            if run["status"] != "running" and "completedAt" not in run:
                snapshot = copy.deepcopy(run)
                snapshot["status"] = "running"
            if seal:
                self.store.seal_run(user_id, snapshot)
            else:
                self.store.save_run(user_id, snapshot)

        def event(stage, title, detail, kind="info", evidence=None):
            run["stage"] = stage
            item = {"id": str(uuid.uuid4()), "at": now(), "stage": stage, "title": title, "detail": detail, "kind": kind,
                    "previousHash": run["events"][-1]["hash"] if run["events"] else "0"*64}
            if evidence is not None:
                item["evidence"] = evidence
            item["hash"] = event_hash(item)
            run["events"].append(item)
            persist()

        def stage(stage_id, status, detail):
            next(s for s in run["stages"] if s["id"] == stage_id).update(status=status, detail=detail)
            persist()

        def execute_fixture(mode, fixture):
            runner = folder / (mode + "_runner.py")
            runner.write_text(TEST_RUNNER if mode == "contracts" else CANARY_RUNNER)
            before = time.monotonic()
            command = [sys.executable, "-I", str(runner), str(fixture)]
            if mode == "monitor":
                command.append("5")
            result = subprocess.run(command, cwd=str(folder), capture_output=True, text=True, timeout=20,
                                    env={"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0", "LANG": "C.UTF-8"})
            parsed = json.loads(result.stdout.strip().splitlines()[-1])
            parsed["durationMs"] = round((time.monotonic()-before)*1000)
            parsed["exitCode"] = result.returncode
            parsed["runnerSha256"] = digest(runner.read_bytes())
            parsed["sourceSha256"] = digest(fixture.read_bytes())
            if mode != "contracts":
                run["metrics"]["totalRequests"] += parsed["requests"] + parsed["healthProbeRequests"]
                run["metrics"]["healthProbes"] += parsed["healthProbeRequests"]
                run["metrics"]["stabilityRequests"] += parsed.get("stabilityRequests", 0)
            (folder / (mode + "-" + fixture.stem + ".json")).write_bytes(canonical(parsed))
            return parsed

        try:
            stage("plan", "running", "Capturing failing revision and recovery intent")
            broken = TENANT_SOURCE if run["scenario"] == "tenant-leak" else DUPLICATE_SOURCE
            source.write_text(broken)
            atomic_json(state_path, {"revision": digest(broken.encode()), "source": "payments.py"})
            run["before"]["revision"] = digest(broken.encode())[:12]
            baseline = execute_fixture("contracts", source)
            if baseline["exitCode"] == 0 or not baseline["failures"]:
                raise RuntimeError("Fault fixture did not reproduce. Recovery cannot proceed.")
            run["before"]["contractStatus"] = "failed"
            event("plan", "Incident reproduced", "Real subprocess contract tests reproduced the seeded regression in the active fault-injected sandbox revision.", "warning", baseline)
            stage("plan", "running", "Fault reproduced; measuring impact before containment")

            baseline_traffic = execute_fixture("canary", source)
            run["metrics"]["duplicateCharges"] = baseline_traffic["duplicateCharges"]
            run["before"]["healthStatus"] = baseline_traffic["health"]["body"]["status"]
            event("plan", "Green health, broken business promise", "The fault-injected service returned HTTP 200 healthy while behavioral replay exposed the incident.", "warning", {"health": baseline_traffic["health"], "traffic": baseline_traffic})
            previous_active = json.loads(state_path.read_text())
            atomic_json(state_path, {"revision": digest(SAFE_SOURCE.encode()), "source": "safe.py"})
            rollback_tests = execute_fixture("contracts", safe)
            rollback_traffic = execute_fixture("canary", safe)
            if rollback_tests["exitCode"] != 0 or not rollback_traffic["passed"]:
                raise RuntimeError("Containment revision failed validation")
            run["after"] = {"revision": digest(SAFE_SOURCE.encode())[:12], "healthStatus": rollback_traffic["health"]["body"]["status"], "contractStatus": "passed"}
            event("plan", "Incident contained by verified rollback", "Active revision pointer changed from fault-injected source to the known safe source. Independent contract tests and loopback HTTP requests validate the selected revision.", "success", {"fromRevision": previous_active["revision"], "toRevision": digest(SAFE_SOURCE.encode()), "contracts": rollback_tests, "traffic": rollback_traffic})
            stage("plan", "passed", "Fault measured; safe rollback independently verified")
            ledger = baseline_traffic["ledger"]
            compensated = reconcile(ledger)
            if reconcile(ledger, compensated) != compensated:
                raise RuntimeError("Reconciliation is not idempotent")
            ledger_path = folder / "synthetic-ledger.json"
            ledger_path.write_bytes(canonical({"unit": "synthetic test credits", "entries": compensated, "noExternalPayments": True}))
            event("plan", "Customer-impact ledger reconciled", "Append-only reversals balance duplicate synthetic debits; replaying reconciliation adds no second reversal. No external payment system was contacted.", "success", {"syntheticDebits": len(ledger), "reversals": len(compensated)-len(ledger), "netTestCredits": sum(row["amount"] for row in compensated), "tenantLeaksObserved": baseline_traffic["tenantLeaks"], "ledgerSha256": digest(ledger_path.read_bytes())})

            stage("create", "running", "Building a bounded repair for service/payments.py")
            candidate = UNSAFE_SOURCE if run["scenario"] == "unsafe-repair" else SAFE_SOURCE
            candidate_path = folder / "candidate.py"
            candidate_path.write_text(candidate)
            run["diff"].update(before=broken, after=candidate)
            event("create", "Repair candidate created", "Reference controller selected one known repair template. Attempts: 1 of 2; allowed path: service/payments.py. Local model calls: 0.", evidence={"attempt": 1, "allowedPath": "service/payments.py", "candidateSha256": digest(candidate.encode()), "controller": "deterministic reference"})
            stage("create", "passed", "One repair within the path and attempt budget")

            stage("secure", "running", "Inspecting candidate before any execution")
            security = security_gate(candidate)
            event("secure", "AST policy evaluated", "Candidate is checked before executing tests or packaging it.", "success" if security["passed"] else "error", security)
            if not security["passed"]:
                stage("secure", "blocked", "Unapproved import or executable capability detected")
                # Verify the kept revision instead of ever executing rejected source.
                safe_tests = execute_fixture("contracts", safe)
                safe_traffic = execute_fixture("monitor", safe)
                if safe_tests["exitCode"] != 0 or not safe_traffic["passed"]:
                    raise RuntimeError("Last known good revision failed validation")
                run["metrics"].update(testsPassed=safe_tests["passed"], testsTotal=safe_tests["total"], requestsReplayed=safe_traffic["requests"], canaryRequests=safe_traffic["canaryRequests"])
                run["after"] = {"revision": digest(SAFE_SOURCE.encode())[:12], "healthStatus": "healthy", "contractStatus": "passed"}
                run["status"] = "blocked"
                run["decision"] = {"outcome": "repair-blocked", "reason": "Candidate requests forbidden capabilities. It was never executed or promoted; verified safe revision remains active."}
                for s in run["stages"]:
                    if s["status"] == "pending":
                        s.update(status="blocked", detail="Candidate rejected by security policy")
                stage("monitor", "passed", "Kept revision passed contracts and a five-second HTTP stability gate")
                event("monitor", "Safe revision confirmed", "Rejected source was never loaded. Contracts, 32 initial behavioral requests, and sampled health/idempotency/tenant checks over five seconds validate the kept safe revision.", "success", {"contracts": safe_tests, "traffic": safe_traffic})
            else:
                stage("secure", "passed", "Restricted AST allowlist passed")
                stage("verify", "running", "Executing regression and adversarial contracts")
                verified = execute_fixture("contracts", candidate_path)
                run["metrics"].update(testsPassed=verified["passed"], testsTotal=verified["total"])
                event("verify", "Regression contracts executed", "Retry identity, cross-tenant access, ownership, key scoping, conflicting amounts, and input validation run in a separate Python process.", "success" if verified["exitCode"] == 0 else "error", verified)
                if verified["exitCode"] != 0:
                    raise RuntimeError("Candidate failed required contracts")
                stage("verify", "passed", str(verified["passed"]) + " / " + str(verified["total"]) + " executable contracts passed")

                stage("package", "running", "Creating immutable release bundle and component manifest")
                sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
                        "metadata": {"component": {"type": "application", "name": "aftercare-synthetic-payment-fixture", "version": digest(candidate.encode())[:12]}},
                        "components": [], "properties": [{"name": "aftercare:scope", "value": "First-party fixture has no third-party runtime dependencies; control-plane dependencies listed in requirements.txt"}]}
                (folder / "sbom.cdx.json").write_bytes(canonical(sbom))
                bundle = folder / "release.zip"
                with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
                    for name, data in [("service/payments.py", candidate.encode()), ("sbom.cdx.json", canonical(sbom))]:
                        info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                        archive.writestr(info, data)
                for path, kind in [(bundle, "release-bundle"), (folder / "sbom.cdx.json", "sbom")]:
                    run["artifacts"].append({"name": path.name, "type": kind, "sha256": digest(path.read_bytes()), "url": "/api/runs/" + run["id"] + "/artifacts/" + path.name})
                event("package", "Release bundle sealed", "The exact tested source is packaged with a scoped CycloneDX SBOM. Package digest is verified again at promotion.", "success", {"sha256": digest(bundle.read_bytes()), "sourceSha256": digest(candidate.encode())})
                stage("package", "passed", "SHA-256 release bundle + scoped SBOM")

                stage("configure", "running", "Applying immutable sandbox runtime configuration")
                config = {"payments": "synthetic-only", "network": "127.0.0.1", "candidateDigest": digest(candidate.encode()), "trafficRequests": 32, "contractsRequired": True}
                atomic_json(folder / "runtime-config.json", config)
                event("configure", "Runtime intent applied", "Isolated fixture accepts loopback synthetic traffic only. No arbitrary URL, executable source, or shell input is accepted by the API.", "success", config)
                stage("configure", "passed", "Configuration digest recorded")

                stage("release", "running", "Replaying HTTP traffic before promotion")
                canary = execute_fixture("canary", candidate_path)
                run["metrics"]["requestsReplayed"] = canary["requests"]
                run["metrics"]["canaryRequests"] = canary["canaryRequests"]
                event("release", "Loopback canary completed", "32 real HTTP requests: 24 duplicate checkout retries and 8 cross-tenant reads. These are synthetic sandbox requests.", "success" if canary["passed"] else "error", canary)
                if not canary["passed"]:
                    raise RuntimeError("Canary contract failed; safe revision retained")
                if digest(bundle.read_bytes()) != run["artifacts"][0]["sha256"]:
                    raise RuntimeError("Artifact changed before promotion")
                with zipfile.ZipFile(bundle) as archive:
                    if digest(archive.read("service/payments.py")) != digest(candidate.encode()):
                        raise RuntimeError("Bundle source differs from tested source")
                atomic_json(state_path, {"revision": digest(candidate.encode()), "source": "candidate.py", "bundleSha256": digest(bundle.read_bytes())})
                stage("release", "passed", "Verified candidate promoted in sandbox")

                stage("monitor", "running", "Checking promoted revision independently")
                active = json.loads(state_path.read_text())
                active_source = folder / active["source"]
                postcheck = execute_fixture("contracts", active_source)
                if postcheck["exitCode"] != 0 or digest(active_source.read_bytes()) != active["revision"]:
                    atomic_json(state_path, {"revision": digest(SAFE_SOURCE.encode()), "source": "safe.py"})
                    raise RuntimeError("Post-promotion verification failed; safe revision restored")
                observed = execute_fixture("monitor", active_source)
                run["metrics"]["requestsReplayed"] += observed["requests"]
                if not observed["passed"] or observed["observationMs"] < 5000:
                    atomic_json(state_path, {"revision": digest(SAFE_SOURCE.encode()), "source": "safe.py"})
                    raise RuntimeError("Post-promotion stability gate failed; safe revision restored")
                event("monitor", "Five-second stability gate passed", "Active source served real HTTP traffic over a five-second observation window. Every sample checked health, retry identity, and tenant boundaries.", "success", observed)
                event("monitor", "Post-promotion contracts passed", "The active revision was loaded from its on-disk pointer and independently retested. Sandbox service health and behavioral contracts agree.", "success", postcheck)
                stage("monitor", "passed", "Active revision independently tested and stable for five seconds")
                run["status"] = "recovered"
                run["after"] = {"revision": digest(candidate.encode())[:12], "healthStatus": "healthy", "contractStatus": "passed"}
                run["decision"] = {"outcome": "recovered", "reason": "Reproduced regression, reconciled synthetic impact, repaired within policy, passed contracts and loopback canary, then promoted the verified bundle in the isolated sandbox."}

            stage("govern", "running", "Sealing the evidence chain and decision")
            run["artifacts"].append({"name": ledger_path.name, "type": "synthetic-ledger", "sha256": digest(ledger_path.read_bytes()), "url": "/api/runs/" + run["id"] + "/artifacts/" + ledger_path.name})
            event("govern", "Recovery decision recorded", run["decision"]["reason"], "success" if run["status"] == "recovered" else "warning", {"outcome": run["status"], "chainType": "SHA-256 hash chain; no external signature or timestamp authority", "safeRevisionActive": run["after"]["healthStatus"] == "healthy", "measurement": "Wall-clock duration and observed test/HTTP counts; no estimated financial or energy savings"})
            if not verify_chain(run["events"]):
                raise RuntimeError("Evidence integrity verification failed")
            stage("govern", "passed", "Event chain verified; decision sealed")
        except Exception as exc:
            atomic_json(state_path, {"revision": digest(SAFE_SOURCE.encode()), "source": "safe.py"})
            run["status"] = "failed"
            run["after"] = {"revision": digest(SAFE_SOURCE.encode())[:12], "healthStatus": "safe-revision-retained", "contractStatus": "unverified"}
            run["decision"] = {"outcome": "stopped", "reason": "Recovery stopped safely: " + str(exc)[:350]}
            stage(run["stage"], "failed", run["decision"]["reason"])
            event("govern", "Fail-closed recovery stop", run["decision"]["reason"], "error")
        finally:
            for artifact in run["artifacts"]:
                artifact_path = folder / artifact["name"]
                self.store.put_artifact(run["id"], artifact["name"], artifact_path.read_bytes())
            run["completedAt"] = now()
            run["metrics"]["durationMs"] = round((time.monotonic()-started)*1000)
            atomic_json(folder / "run-evidence.json", self.envelope(run))
            persist(seal=True)

    @staticmethod
    def envelope(run):
        return {"format": "aftercare.evidence.v1", "project": "Aftercare", "author": "Shivam Gupta", "executionMode": "deterministic-reference", "sandbox": True,
                "run": run, "integrity": {"algorithm": "SHA-256", "sealed": run["status"] != "running" and bool(run.get("completedAt")), "verified": verify_chain(run["events"]), "manifestSha256": digest(canonical(run)), "head": run["events"][-1]["hash"] if run["events"] else "0"*64,
                "limitations": "Hash chain detects modification relative to a trusted head. It is not an external signature, timestamp, or independent proof of execution."}}


def atomic_json(path, body):
    temp = Path(str(path) + ".tmp")
    temp.write_bytes(canonical(body))
    os.replace(str(temp), str(path))
