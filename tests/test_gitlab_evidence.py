import json
import urllib.error

from fastapi.testclient import TestClient

from server.gitlab_evidence import API_ROOT, PROJECT_URL, GitLabEvidence
from server.main import create_app

SHA = "a" * 40


class Reply:
    def __init__(self, payload):
        self.payload = payload

    def read(self, limit):
        return json.dumps(self.payload).encode()[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def mock_upstream(monkeypatch, fail=False):
    calls = []
    def urlopen(request, timeout):
        calls.append(request.full_url)
        assert request.full_url.startswith(API_ROOT)
        assert timeout == 4
        assert "Authorization" not in request.headers
        if fail:
            raise urllib.error.URLError("private diagnostic should not leak")
        if "/pipelines?" in request.full_url:
            return Reply([{"id": 44, "status": "success", "sha": SHA, "ref": "aftercare/repair-test", "source": "push", "web_url": "https://untrusted.example"}])
        if "/merge_requests?" in request.full_url:
            return Reply([{"iid": 2, "title": "Repair retry identity", "source_branch": "aftercare/repair-test", "state": "opened", "sha": SHA}, {"iid": 3, "title": "Unrelated change", "source_branch": "unrelated", "state": "opened", "sha": SHA}])
        return Reply({"iid": 1, "title": "Recovery request", "state": "opened"})
    monkeypatch.setattr("server.gitlab_evidence.urllib.request.urlopen", urlopen)
    return calls


def test_public_evidence_parsing_fixed_links_and_cache(monkeypatch):
    calls = mock_upstream(monkeypatch)
    clock = [100]
    reader = GitLabEvidence(clock=lambda: clock[0])
    result = reader.get()
    assert result["available"] is True and result["stale"] is False
    assert len(result["mergeRequests"]) == 1
    assert result["mergeRequests"][0]["pipeline"]["status"] == "success"
    assert result["pipelines"][0]["source"] == "push"
    assert result["pipelines"][0]["url"] == PROJECT_URL + "/-/pipelines/44"
    assert "sessionStatus" not in result
    assert reader.get() == result and len(calls) == 3
    clock[0] += 31
    reader.get()
    assert len(calls) == 6


def test_failure_returns_unavailable_or_explicitly_stale(monkeypatch):
    clock = [100]
    calls = mock_upstream(monkeypatch, fail=True)
    empty = GitLabEvidence(clock=lambda: clock[0]).get()
    assert empty["available"] is False and empty["pipelines"] == []
    assert "private diagnostic" not in empty["detail"]
    mock_upstream(monkeypatch)
    reader = GitLabEvidence(clock=lambda: clock[0])
    good = reader.get()
    clock[0] += 31
    mock_upstream(monkeypatch, fail=True)
    stale = reader.get()
    assert stale["available"] and stale["stale"]
    assert stale["checkedAt"] == good["checkedAt"]
    assert stale["pipelines"] == good["pipelines"]
    assert "statuses may have changed" in stale["detail"]


def test_evidence_route_requires_session_guest_allowed(tmp_path, monkeypatch):
    mock_upstream(monkeypatch)
    app = create_app(tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/gitlab/evidence").status_code == 401
        client.post("/api/demo/session", json={})
        response = client.get("/api/gitlab/evidence")
        assert response.status_code == 200 and response.json()["available"]
        assert response.headers["cache-control"] == "no-store"


def test_config_cannot_inject_url_or_project(monkeypatch):
    monkeypatch.setenv("AFTERCARE_GITLAB_SESSION_ID", "../../other?token=secret")
    monkeypatch.setenv("AFTERCARE_GITLAB_FLOW_ID", "https://attacker.example")
    mock_upstream(monkeypatch)
    result = GitLabEvidence().get()
    assert result["sessionUrl"] == PROJECT_URL + "/-/automate/agent-sessions/9737653"
    assert result["flowUrl"] == PROJECT_URL + "/-/automate/flows/1018811"
