"""Exercise actual fault evidence, changed-path enforcement and repair contracts."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("incident_cli", ROOT / "scripts" / "incident.py")
incident = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(incident)


class IncidentEvidenceTests(unittest.TestCase):
    def test_chain_detects_tampering_missing_and_reordered_events(self):
        events = []
        incident.append_event(events, "source", {"sha": "abc"})
        incident.append_event(events, "tests", {"exit": 1})
        self.assertTrue(incident.validate_chain(events))
        changed = copy.deepcopy(events)
        changed[0]["payload"]["sha"] = "attacker"
        self.assertFalse(incident.validate_chain(changed))
        self.assertFalse(incident.validate_chain(events[::-1]))
        self.assertFalse(incident.validate_chain(events[1:]))
        self.assertFalse(incident.validate_chain([]))

    def test_current_fixture_observation_agrees_with_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "fixture"
            shutil.copytree(incident.FIXTURE, target, ignore=shutil.ignore_patterns("__pycache__", "test_regression.py"))
            # The monitor job separately requires repaired current source to pass.
            tests = incident.run_contract(target)
            observation = incident.observe(target)
            self.assertEqual(tests["exitCode"] == 0, observation["duplicateCaptures"] == 0)
            self.assertEqual(observation["health"]["status"], "healthy")

    def test_seeded_baseline_fails_without_rewriting_current_source(self):
        before = incident.digest(incident.FIXTURE / "service.py")
        with incident.selected_fixture("seeded") as fixture:
            self.assertNotEqual(fixture, incident.FIXTURE)
            tests = incident.run_contract(fixture)
            observation = incident.observe(fixture)
            self.assertEqual(tests["exitCode"], 1)
            self.assertGreaterEqual(tests["testsRun"], 5)
            self.assertEqual(observation["duplicateCaptures"], 23)
            self.assertEqual(incident.digest(fixture / "service.py"), incident.SEEDED_SOURCE_SHA256)
            self.assertEqual((fixture / "test_contract.py").read_bytes(),
                             (incident.FIXTURE / "test_contract.py").read_bytes())
        self.assertFalse(fixture.exists())
        self.assertEqual(incident.digest(incident.FIXTURE / "service.py"), before)

    def test_tampered_seeded_baseline_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "changed.py"
            changed.write_text("import os\n")
            with patch.object(incident, "SEEDED_SOURCE", changed):
                with self.assertRaises(ValueError):
                    with incident.selected_fixture("seeded"):
                        self.fail("Tampered baseline must not be yielded")

    def test_cli_labels_seeded_evidence_and_verify_remains_red(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(incident.main(["reproduce", "--fixture", "seeded", "--output", directory]), 0)
            manifest = json.loads((Path(directory) / "manifest.json").read_text())
            self.assertEqual(manifest["source"]["fixtureSelection"], "seeded")
            self.assertTrue(manifest["defectReproduced"])
            self.assertFalse(manifest["repairVerified"])
            self.assertTrue(incident.check_evidence(directory))
            self.assertEqual(incident.main(["verify", "--fixture", "seeded", "--output", directory]), 1)

    def test_real_repair_passes_contract_and_preserves_evidence_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "fixture"
            target.mkdir()
            shutil.copy2(incident.FIXTURE / "test_contract.py", target / "test_contract.py")
            # Independent correct implementation used solely to exercise the CLI.
            (target / "service.py").write_text('''class Checkout:
    def __init__(self):
        self.ledger=[]
        self.requests={}
    def charge(self, tenant, key, amount):
        if not tenant or not key or type(amount) is not int or not 0 < amount <= 100000:
            raise ValueError("invalid")
        identity=(tenant,key)
        if identity in self.requests:
            prior=self.requests[identity]
            if prior["amount"] != amount:
                raise ValueError("conflict")
            return prior
        record={"id":str(len(self.ledger)+1),"tenant":tenant,"key":key,"amount":amount}
        self.ledger.append(record)
        self.requests[identity]=record
        return record
    def health(self):
        return {"status":"healthy"}
''')
            (target / "test_regression.py").write_text('''import unittest
from service import Checkout
class Regression(unittest.TestCase):
    def test_many_retries_share_one_capture(self):
        checkout=Checkout()
        for _ in range(100):
            checkout.charge("alice","retry",42)
        self.assertEqual(len(checkout.ledger),1)
''')
            output = Path(directory) / "evidence"
            self.assertEqual(incident.record("verify", output, target), 0)
            self.assertTrue(incident.check_evidence(output))
            (output / "observation.json").write_text("{}")
            self.assertFalse(incident.check_evidence(output))

    def test_policy_fails_closed_without_base(self):
        self.assertEqual(incident.main(["policy"]), 2)

    def test_policy_accepts_only_service_and_added_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "examples" / "checkout"
            fixture.mkdir(parents=True)
            (fixture / "service.py").write_text("x = 1\n")
            (fixture / "test_contract.py").write_text("x = 1\n")
            def git(*args):
                return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            git("init", "-q")
            git("add", ".")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
            base = git("rev-parse", "HEAD")
            (fixture / "service.py").write_text("x = 2\n")
            with patch.object(incident, "ROOT", root):
                with self.assertRaises(ValueError):
                    incident.changed_paths(base)
                (fixture / "test_regression.py").write_text("def test_new():\n    assert 1 == 1\n")
                git("add", ".")
                self.assertEqual(len(incident.changed_paths(base)), 2)
                (fixture / "test_contract.py").write_text("x = 2\n")
                with self.assertRaises(ValueError):
                    incident.changed_paths(base)

    def test_malicious_fixture_is_rejected_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            (fixture / "service.py").write_text("import os\nos.remove('anything')\n")
            with self.assertRaises(ValueError):
                incident.run_contract(fixture)
            with self.assertRaises(ValueError):
                incident.observe(fixture)


if __name__ == "__main__":
    unittest.main()
