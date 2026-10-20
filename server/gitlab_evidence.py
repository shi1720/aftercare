"""Read-only public execution evidence for the one Aftercare GitLab project.

No personal token, private API, configurable host, or caller-supplied URL is used.
A session link is a navigation reference; this reader makes no session-status claim.
"""
import copy
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

PROJECT_ID = 87855246
PROJECT_URL = "https://gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43209963/aftercare"
API_ROOT = "https://gitlab.com/api/v4/projects/87855246/"
FIXED_PATHS = {
    "pipelines": "pipelines?per_page=20&order_by=id&sort=desc",
    "mergeRequests": "merge_requests?state=all&per_page=50&order_by=updated_at&sort=desc",
    "issue": "issues/1",
}
SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
REPAIR_BRANCH = re.compile(r"aftercare/repair-[A-Za-z0-9._-]{1,160}\Z")


class GitLabEvidence:
    def __init__(self, clock=None):
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._cached = None
        self._last_good = None
        self._expires = 0
        self._flow_id = self._numeric_config("AFTERCARE_GITLAB_FLOW_ID", "1018811")
        self._session_id = self._numeric_config("AFTERCARE_GITLAB_SESSION_ID", "9737653")

    @staticmethod
    def _numeric_config(name, default):
        configured = os.environ.get(name, default)
        return configured if re.fullmatch(r"[1-9][0-9]{0,15}", configured) else default

    @staticmethod
    def _read_json(key):
        # Enumerated keys prevent both URL injection and requests to other projects.
        request = urllib.request.Request(API_ROOT + FIXED_PATHS[key], headers={"Accept": "application/json", "User-Agent": "Aftercare-public-evidence/1.0"})
        with urllib.request.urlopen(request, timeout=4) as response:
            data = response.read(1_000_001)
        if len(data) > 1_000_000:
            raise ValueError("Public response exceeds evidence size limit")
        value = json.loads(data)
        if not isinstance(value, dict if key == "issue" else list):
            raise ValueError("Unexpected public API response")
        return value

    @staticmethod
    def _pipeline(row):
        if not isinstance(row, dict) or not isinstance(row.get("id"), int) or row["id"] < 1:
            return None
        if not isinstance(row.get("sha"), str) or not SHA.fullmatch(row["sha"]):
            return None
        if not isinstance(row.get("status"), str) or not isinstance(row.get("ref"), str):
            return None
        result = {"id": row["id"], "status": row["status"][:50], "sha": row["sha"], "url": PROJECT_URL + "/-/pipelines/" + str(row["id"]), "ref": row["ref"][:200]}
        if isinstance(row.get("source"), str):
            result["source"] = row["source"][:80]
        return result

    def _result(self, values, failures):
        pipelines = [parsed for row in values.get("pipelines", []) if (parsed := self._pipeline(row)) is not None]
        merge_requests = []
        for row in values.get("mergeRequests", []):
            if not isinstance(row, dict) or not isinstance(row.get("source_branch"), str) or not REPAIR_BRANCH.fullmatch(row["source_branch"]):
                continue
            if not isinstance(row.get("iid"), int) or row["iid"] < 1 or not isinstance(row.get("sha"), str) or not SHA.fullmatch(row["sha"]):
                continue
            if row.get("state") not in {"opened", "closed", "merged", "locked"}:
                continue
            mr = {"iid": row["iid"], "title": str(row.get("title", "Untitled repair"))[:300], "state": row["state"], "url": PROJECT_URL + "/-/merge_requests/" + str(row["iid"]), "sourceBranch": row["source_branch"], "sha": row["sha"]}
            # Link a pipeline only when the public API identifies the same commit
            # and branch, or explicitly provides this MR's head pipeline.
            matched = next((pipeline for pipeline in pipelines if pipeline["sha"] == mr["sha"] and pipeline["ref"] == mr["sourceBranch"]), None)
            if not matched:
                matched = self._pipeline(row.get("head_pipeline"))
                if matched and matched["sha"] != mr["sha"]:
                    matched = None
            if matched:
                mr["pipeline"] = matched
            merge_requests.append(mr)
        available = bool(values)
        detail = "Live public GitLab API evidence. Repair MRs are filtered to aftercare/repair- branches. The linked Duo session status is not queried or inferred."
        if failures:
            detail = "Public GitLab evidence is partial; unavailable sources: " + ", ".join(sorted(failures)) + ". No missing status is inferred."
        return {"projectUrl": PROJECT_URL, "flowUrl": PROJECT_URL + "/-/automate/flows/" + self._flow_id,
                "issueUrl": PROJECT_URL + "/-/issues/1", "sessionUrl": PROJECT_URL + "/-/automate/agent-sessions/" + self._session_id,
                "checkedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "pipelines": pipelines,
                "mergeRequests": merge_requests, "available": available, "stale": False, "detail": detail}

    def get(self):
        # This method is called from a synchronous FastAPI route, so neither the
        # outbound reads nor cache contention block the event loop.
        with self._lock:
            current = self._clock()
            if self._cached is not None and current < self._expires:
                return copy.deepcopy(self._cached)
            values, failures = {}, []
            with ThreadPoolExecutor(max_workers=3, thread_name_prefix="gitlab-proof") as pool:
                futures = {key: pool.submit(self._read_json, key) for key in FIXED_PATHS}
                for key, future in futures.items():
                    try:
                        values[key] = future.result()
                    except (OSError, ValueError, urllib.error.URLError, TimeoutError):
                        failures.append(key)
            if not values and self._last_good:
                result = copy.deepcopy(self._last_good)
                result.update(stale=True, detail="Public GitLab is temporarily unavailable. Showing the last successful evidence snapshot at checkedAt; statuses may have changed. Duo session status is not inferred.")
            else:
                result = self._result(values, failures)
                if not failures:
                    self._last_good = copy.deepcopy(result)
            self._cached = result
            self._expires = self._clock() + 30
            return copy.deepcopy(result)
