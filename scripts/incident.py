#!/usr/bin/env python3
"""Reproducible checkout contract evidence. All effects remain in a subprocess.

This CLI does not call an LLM, deploy, refund real money or claim a Duo run.
The Duo flow uses it to gather evidence before independently editing source.
"""
import argparse
import ast
import hashlib
import io
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "checkout"
REPAIR_PATHS = {"examples/checkout/service.py", "examples/checkout/test_regression.py"}
GENESIS = "0" * 64


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def append_event(events, kind, payload):
    event = {"sequence": len(events) + 1, "kind": kind, "payload": payload,
             "previousHash": events[-1]["hash"] if events else GENESIS}
    event["hash"] = hashlib.sha256(canonical(event)).hexdigest()
    events.append(event)


def validate_chain(events):
    if not isinstance(events, list) or not events:
        return False
    previous = GENESIS
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or event.get("sequence") != index or event.get("previousHash") != previous:
            return False
        calculated = hashlib.sha256(canonical({k: v for k, v in event.items() if k != "hash"})).hexdigest()
        if event.get("hash") != calculated:
            return False
        previous = calculated
    return True


def run_contract(fixture=FIXTURE):
    candidate_findings = fixture_safety(fixture)
    if candidate_findings:
        raise ValueError("Fixture rejected before execution: " + "; ".join(candidate_findings))
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(fixture),
                             "-p", "test_*.py", "-v"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    count = re.search(r"Ran (\d+) tests?", result.stderr)
    return {"command": "python -m unittest discover -s examples/checkout -p 'test_*.py' -v",
            "exitCode": result.returncode, "testsRun": int(count.group(1)) if count else 0,
            "stdout": result.stdout, "stderr": result.stderr}


def fixture_safety(fixture):
    """Small domain allowlist before source or regression code can be loaded."""
    findings = []
    names = {"Checkout", "ValueError", "type", "len", "str", "int", "bool", "range", "set"}
    methods = {"append", "get", "charge", "health", "main", "assertEqual", "assertNotEqual",
               "assertRaises", "assertTrue", "assertFalse", "assertIs", "assertIsNot",
               "assertIsNone", "assertIsNotNone", "assertIn", "assertNotIn", "assertLessEqual"}
    for path in sorted(Path(fixture).glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(alias.name != "unittest" for alias in node.names):
                findings.append(path.name + ": forbidden import")
            if isinstance(node, ast.ImportFrom) and (node.module != "service" or node.level != 0 or any(alias.name != "Checkout" for alias in node.names)):
                findings.append(path.name + ": forbidden import")
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                findings.append(path.name + ": forbidden dunder access")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id not in names:
                    findings.append(path.name + ": unapproved call " + node.func.id)
                elif isinstance(node.func, ast.Attribute) and node.func.attr not in methods:
                    findings.append(path.name + ": unapproved method " + node.func.attr)
                elif not isinstance(node.func, (ast.Name, ast.Attribute)):
                    findings.append(path.name + ": indirect call")
    return sorted(set(findings))


def observe(fixture=FIXTURE):
    if fixture_safety(fixture):
        raise ValueError("Unsafe fixture cannot be observed")
    program = '''import json,sys
sys.path.insert(0,sys.argv[1])
from service import Checkout
checkout=Checkout()
for _ in range(24):
    checkout.charge("alice","checkout-canary",4200)
print(json.dumps({"health":checkout.health(),"requests":24,"uniqueOrders":1,
"captures":len(checkout.ledger),"duplicateCaptures":max(0,len(checkout.ledger)-1),
"creditsAtRisk":max(0,len(checkout.ledger)-1)*4200,"ledger":checkout.ledger}))
'''
    result = subprocess.run([sys.executable, "-c", program, str(fixture)], cwd=ROOT,
                            capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError("Fixture execution failed: " + result.stderr[-2000:])
    return json.loads(result.stdout)


def record(mode, output, fixture=FIXTURE):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    tests, observation = run_contract(fixture), observe(fixture)
    reproduced = (tests["exitCode"] == 1 and observation["health"]["status"] == "healthy"
                  and observation["duplicateCaptures"] > 0)
    verified = (tests["exitCode"] == 0 and observation["duplicateCaptures"] == 0
                and (fixture / "test_regression.py").is_file() and tests["testsRun"] >= 6)
    source = {"serviceSha256": digest(fixture / "service.py"),
              "contractSha256": digest(fixture / "test_contract.py")}
    events = []
    append_event(events, "source-bound", source)
    append_event(events, "contract-executed", {"exitCode": tests["exitCode"]})
    append_event(events, "canary-observed", observation)
    append_event(events, "decision", {"defectReproduced": reproduced, "repairVerified": verified})
    write_json(output / "tests.json", tests)
    write_json(output / "observation.json", observation)
    write_json(output / "events.json", events)
    manifest = {"schema": "aftercare.fixture-evidence/v1", "mode": mode,
                "createdAt": datetime.now(timezone.utc).isoformat(), "syntheticCreditsOnly": True,
                "source": source, "defectReproduced": reproduced, "repairVerified": verified,
                "chainHead": events[-1]["hash"],
                "files": {name: digest(output / name) for name in ["tests.json", "observation.json", "events.json"]}}
    write_json(output / "manifest.json", manifest)
    print(json.dumps({"output": str(output), "defectReproduced": reproduced,
                      "repairVerified": verified, "chainHead": events[-1]["hash"]}))
    return 0 if (verified if mode == "verify" else reproduced) else 1


def check_evidence(output):
    output = Path(output)
    try:
        manifest = json.loads((output / "manifest.json").read_text())
        events = json.loads((output / "events.json").read_text())
        if set(manifest["files"]) != {"tests.json", "observation.json", "events.json"}:
            return False
        if not validate_chain(events) or events[-1]["hash"] != manifest["chainHead"]:
            return False
        return all(digest(output / name) == sha for name, sha in manifest["files"].items())
    except (OSError, ValueError, KeyError, TypeError):
        return False


def changed_paths(base):
    result = subprocess.run(["git", "diff", "--name-status", "--no-renames", base, "--"],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    changes = [line.split("\t") for line in result.stdout.splitlines()]
    if not changes or any(len(line) != 2 or line[0] not in {"A", "M"} for line in changes):
        raise ValueError("Repair must contain only additions or modifications")
    paths = {line[1] for line in changes}
    if not paths <= REPAIR_PATHS or "examples/checkout/service.py" not in paths:
        raise ValueError("Repair changed a protected path or omitted the service")
    if "examples/checkout/test_regression.py" not in paths:
        raise ValueError("Repair must include an independently added regression test")
    for name in paths:
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 20000:
            raise ValueError("Unsafe repair file")
        ast.parse(path.read_text())
    findings = fixture_safety(ROOT / "examples" / "checkout")
    if findings:
        raise ValueError("Unsafe candidate: " + "; ".join(findings))
    return sorted(paths)


def security_scan():
    findings = []
    files = sorted((ROOT / "server").rglob("*.py")) + sorted(FIXTURE.glob("*.py"))
    for path in files:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "compile", "__import__"}:
                findings.append({"path": str(path.relative_to(ROOT)), "line": node.lineno, "rule": "dynamic-code-execution"})
            if isinstance(node, ast.Call) and any(kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True for kw in node.keywords):
                findings.append({"path": str(path.relative_to(ROOT)), "line": node.lineno, "rule": "shell-true"})
    return {"scanner": "aftercare-ast/v1", "scope": "Python server and checkout fixture", "filesScanned": len(files),
            "limitations": "Narrow first-party checks, not a complete security audit or dependency CVE scan.", "findings": findings}


def package(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = [p for p in ROOT.rglob("*") if p.is_file() and not p.is_symlink()
             and output.resolve() not in p.resolve().parents
             and not any(part in {".git", ".venv", "__pycache__", ".pytest_cache", "artifacts", "node_modules", ".env", "data", ".data", ".cache"} for part in p.relative_to(ROOT).parts)
             and not (p.name.startswith(".env") and p.name != ".env.example")
             and p.suffix not in {".pyc", ".db", ".sqlite", ".sqlite3"}]
    archive = output / "aftercare-source.tar"
    with tarfile.open(archive, "w") as tar:
        for path in sorted(paths):
            data = path.read_bytes()
            info = tarfile.TarInfo(str(path.relative_to(ROOT)))
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))
    write_json(output / "package.json", {"archive": archive.name, "sha256": digest(archive), "files": len(paths)})
    return archive


def reference_evidence(output):
    """Execute the actual server controller; never translate fixtures into AI claims."""
    sys.path.insert(0, str(ROOT))
    from server.engine import Controller, new_run, STAGES
    from server.evidence import verify_chain
    from server.store import Store
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    summaries = []
    with tempfile.TemporaryDirectory(prefix="aftercare-reference-") as directory:
        store = Store(directory)
        user_id = "ci-synthetic-user"
        with store.connection() as conn:
            conn.execute("INSERT INTO users(id,name,demo) VALUES(?,?,1)", (user_id, "CI sandbox"))
        controller = Controller(store)
        for scenario in ["duplicate-charge", "tenant-leak", "unsafe-repair"]:
            run = new_run(scenario)
            controller.execute(user_id, run)
            expected = "blocked" if scenario == "unsafe-repair" else "recovered"
            if run["status"] != expected or not verify_chain(run["events"]):
                raise RuntimeError("Reference controller failed: " + json.dumps(run["decision"]))
            if scenario != "unsafe-repair" and any(stage["status"] != "passed" for stage in run["stages"]):
                raise RuntimeError("Reference lifecycle stage did not pass")
            scenario_dir = output / scenario
            scenario_dir.mkdir(exist_ok=True)
            write_json(scenario_dir / "run-evidence.json", controller.envelope(run))
            for artifact in run["artifacts"]:
                shutil.copy2(store.root / "runs" / run["id"] / artifact["name"], scenario_dir / artifact["name"])
            summaries.append({"scenario": scenario, "status": run["status"], "metrics": run["metrics"],
                              "chainHead": run["events"][-1]["hash"]})
    report = {"executionMode": "deterministic-reference", "syntheticOnly": True,
              "lifecycleStages": STAGES, "scenarios": summaries,
              "duoExecutionClaimed": False}
    write_json(output / "reference-report.json", report)
    print(json.dumps(report))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["reproduce", "verify", "evidence", "validate", "policy", "secure", "package"])
    parser.add_argument("--output", default="artifacts/incident")
    parser.add_argument("--base")
    args = parser.parse_args(argv)
    try:
        if args.command in {"reproduce", "verify"}:
            return record(args.command, args.output)
        if args.command == "evidence":
            return reference_evidence(args.output)
        if args.command == "validate":
            valid = check_evidence(args.output)
            print(json.dumps({"integrityValid": valid, "identityAttestation": False}))
            return 0 if valid else 1
        if args.command == "policy":
            if not args.base:
                raise ValueError("--base is required; an absent comparison must fail closed")
            print(json.dumps({"allowed": True, "changedPaths": changed_paths(args.base)}))
            return 0
        if args.command == "secure":
            result = security_scan()
            write_json(Path(args.output) / "security.json", result)
            print(json.dumps(result))
            return 1 if result["findings"] else 0
        print(package(args.output))
        return 0
    except (OSError, ValueError, SyntaxError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
