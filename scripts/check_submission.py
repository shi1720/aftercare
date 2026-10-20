#!/usr/bin/env python3
"""Check concrete packaging prerequisites; external submission claims stay pending."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def check():
    required = ["LICENSE", "README.md", "AGENTS.md", "requirements.txt", ".gitlab-ci.yml",
                ".gitlab/duo/agent-config.yml", "gitlab/flows/aftercare.yml",
                "scripts/incident.py", "examples/checkout/service.py", "examples/checkout/test_contract.py"]
    checks = [{"name": name, "passed": (ROOT / name).is_file()} for name in required]
    license_text = (ROOT / "LICENSE").read_text() if (ROOT / "LICENSE").exists() else ""
    checks.append({"name": "MIT license detectable", "passed": "MIT License" in license_text and "Permission is hereby granted" in license_text})
    pins = (ROOT / "requirements.txt").read_text().splitlines() if (ROOT / "requirements.txt").exists() else []
    checks.append({"name": "dependency versions pinned", "passed": bool(pins) and all("==" in x for x in pins if x.strip() and not x.startswith("#"))})
    report = {"schema": "aftercare.submission-check/v1", "checks": checks,
              "passed": all(x["passed"] for x in checks),
              "externalEvidenceRequired": ["public GitLab URL and license detection", "visible passed CI pipeline",
                                           "registered and executed Duo flow session", "public YouTube video under three minutes",
                                           "Devpost submission completed before 2026-10-27T13:00:00Z"],
              "externalEvidenceVerifiedByThisScript": False}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = check()
    body = json.dumps(report, indent=2) + "\n"
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    print(body)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
