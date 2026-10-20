"""Hosting, auth, and failure-path regressions from the production audit."""
import asyncio
import threading
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from server.main import COOKIE, LEGACY_COOKIE, canonical_origin, create_app, token_hash


def make_user(client):
    return client.post("/api/auth/register", json={"name": "Shivam Gupta", "email": "account@example.test", "password": "a sufficiently long password"})


def test_firebase_cookie_survives_proxy_cookie_filter(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        response = client.post("/api/demo/session", json={})
        owner = response.json()["user"]["id"]
        assert COOKIE == "__session"
        token = client.cookies.get("__session")
        # Firebase Hosting forwards only this cookie to a Cloud Run rewrite.
        with TestClient(app) as proxy:
            proxy.cookies.set("__session", token)
            assert proxy.get("/api/session").json()["user"]["id"] == owner
            assert proxy.get("/api/overview").status_code == 200


def test_legacy_session_rotates_and_logout_revokes_both(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        make_user(client)
        old = client.cookies.get(COOKIE)
        client.cookies.clear()
        client.cookies.set(LEGACY_COOKIE, old, domain="testserver.local", path="/")
        migrated = client.get("/api/session")
        assert migrated.json()["user"]["email"] == "account@example.test"
        new = client.cookies.get(COOKIE)
        assert new and new != old
        assert client.cookies.get(LEGACY_COOKIE) is None
        assert app.state.store.session_user(token_hash(old), 0) is None
        assert client.post("/api/auth/logout", json={}).status_code == 200
        client.cookies.clear()
        for name, token in [(COOKIE, new), (LEGACY_COOKIE, old)]:
            client.cookies.set(name, token)
        assert client.get("/api/session").json()["user"] is None


def test_invalid_new_cookie_never_resurrects_legacy_identity(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        make_user(client)
        valid = client.cookies.get(COOKIE)
        client.cookies.clear()
        client.cookies.set(LEGACY_COOKIE, valid)
        client.cookies.set(COOKIE, "invalid-new-session")
        assert client.get("/api/session").json()["user"] is None
        client.post("/api/auth/logout", json={})
        assert app.state.store.session_user(token_hash(valid), 0) is None


@pytest.mark.parametrize("encoding", ["comma", "json"])
def test_exact_origin_allowlist_accepts_firebase_proxy(tmp_path, monkeypatch, encoding):
    origins = ["https://aftercare-test.web.app", "https://aftercare-test.firebaseapp.com"]
    import json
    monkeypatch.setenv("APP_ORIGIN", "https://aftercare-example.a.run.app")
    monkeypatch.setenv("APP_ORIGINS", json.dumps(origins) if encoding == "json" else ",".join(origins))
    app = create_app(tmp_path)
    with TestClient(app, base_url="https://aftercare-example.a.run.app") as client:
        for origin in origins + ["https://aftercare-example.a.run.app"]:
            response = client.post("/api/demo/session", json={}, headers={"Origin": origin, "Sec-Fetch-Site": "same-origin"})
            assert response.status_code == 200
        for origin in ["https://aftercare-test.web.app.attacker.test", "https://attacker.test/aftercare-test.web.app", "null", "https://aftercare-test.web.app:444", "http://aftercare-test.web.app"]:
            assert client.post("/api/demo/session", json={}, headers={"Origin": origin}).status_code == 403
        assert client.post("/api/demo/session", json={}, headers={"Origin": origins[0], "Sec-Fetch-Site": "cross-site"}).status_code == 403


@pytest.mark.parametrize("origin", ["*", "https://*.web.app", "https://foo.test/path", "https://user:password@foo.test", "https://foo.test?token=x", "null"])
def test_unsafe_origin_configuration_fails_at_startup(tmp_path, monkeypatch, origin):
    monkeypatch.setenv("APP_ORIGINS", origin)
    with pytest.raises(ValueError):
        create_app(tmp_path)


def test_origin_normalization_is_exact_and_supports_local_ipv6():
    assert canonical_origin("https://example.test:443/") == "https://example.test"
    assert canonical_origin("http://[::1]:8080/") == "http://[::1]:8080"


def test_malformed_ids_never_reach_datastore(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        client.post("/api/demo/session", json={})
        def unexpected_read(*args):
            raise AssertionError("Malformed ID reached datastore")
        monkeypatch.setattr(app.state.store, "run", unexpected_read)
        for run_id in ["not-a-run", "null", "1", "a" * 120]:
            for suffix in ["", "/evidence", "/artifacts/release.zip"]:
                assert client.get("/api/runs/" + run_id + suffix).status_code == 404


def test_static_fallback_never_disguises_api_or_missing_assets(tmp_path):
    frontend = tmp_path / "dist"
    frontend.mkdir()
    (frontend / "index.html").write_text("<html>Aftercare</html>")
    app = create_app(tmp_path / "data", frontend)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/workspace", headers={"Accept": "text/html"}).status_code == 200
        for path in ["/api", "/api/not-found", "/assets/missing.js", "/.env", "/.git/config", "/missing.json"]:
            assert client.get(path, headers={"Accept": "text/html"}).status_code == 404
        assert client.get("/not-an-api", headers={"Accept": "application/json"}).status_code == 404


def test_slow_run_admission_does_not_block_health_event_loop(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    entered, release = threading.Event(), threading.Event()
    original_count = app.state.store.run_count
    def slow_count(user_id=None):
        entered.set()
        assert release.wait(timeout=5)
        return original_count(user_id)
    monkeypatch.setattr(app.state.store, "run_count", slow_count)
    # Avoid running the fixture: this test exercises admission scheduling only.
    def finish(user_id, run):
        app.state.controller.user_lock(user_id).release()
    monkeypatch.setattr(app.state.controller, "execute", finish)
    async def check():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post("/api/demo/session", json={})
            pending = asyncio.create_task(client.post("/api/runs", json={"scenario": "duplicate-charge"}))
            assert await asyncio.to_thread(entered.wait, 2)
            try:
                response = await asyncio.wait_for(client.get("/api/health"), timeout=1)
                assert response.status_code == 200
            finally:
                release.set()
            assert (await pending).status_code == 202
            await asyncio.gather(*list(app.state.tasks))
    asyncio.run(check())


def test_cancelled_run_admission_continues_without_stranding_locks(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    entered, release, executed = threading.Event(), threading.Event(), threading.Event()
    original_count = app.state.store.run_count
    def slow_count(user_id=None):
        entered.set()
        assert release.wait(timeout=5)
        return original_count(user_id)
    monkeypatch.setattr(app.state.store, "run_count", slow_count)
    def finish(user_id, run):
        app.state.controller.user_lock(user_id).release()
        executed.set()
    monkeypatch.setattr(app.state.controller, "execute", finish)
    async def check():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post("/api/demo/session", json={})
            pending = asyncio.create_task(client.post("/api/runs", json={"scenario": "duplicate-charge"}))
            assert await asyncio.to_thread(entered.wait, 2)
            pending.cancel()
            try:
                await pending
            except asyncio.CancelledError:
                pass
            release.set()
            assert await asyncio.to_thread(executed.wait, 2)
            await asyncio.gather(*list(app.state.tasks))
            user_id = (await client.get("/api/session")).json()["user"]["id"]
            assert not app.state.controller.user_lock(user_id).locked()
    asyncio.run(check())


def test_store_enforces_owner_and_immutable_completion(tmp_path):
    from server.engine import new_run
    app = create_app(tmp_path)
    store = app.state.store
    store.create_user("alice", "Alice", "alice@example.test")
    store.create_user("bob", "Bob", "bob@example.test")
    run = new_run("duplicate-charge")
    store.save_run("alice", run)
    with pytest.raises(ValueError, match="owner mismatch"):
        store.save_run("bob", run)
    run.update(status="blocked", completedAt="2026-10-20T00:00:00Z")
    store.seal_run("alice", run)
    run["title"] = "Changed after completion"
    with pytest.raises(ValueError, match="immutable"):
        store.save_run("alice", run)


def test_quota_and_worker_errors_release_admission_reservations(tmp_path, monkeypatch):
    app = create_app(tmp_path)
    async def check():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            session = (await client.post("/api/demo/session", json={})).json()
            user_id = session["user"]["id"]
            monkeypatch.setattr(app.state.store, "run_count", lambda user_id=None: 100 if user_id else 3000)
            response = await client.post("/api/runs", json={"scenario": "duplicate-charge"})
            assert response.status_code == 429
            assert "100-run retention limit" in response.json()["detail"]
            assert not app.state.controller.user_lock(user_id).locked()
            # All four slots remain available after quota rejection.
            for _ in range(4):
                assert app.state.execution_slots.acquire(blocking=False)
            response = await client.post("/api/runs", json={"scenario": "duplicate-charge"})
            assert response.status_code == 429
            assert response.headers["retry-after"] == "5"
            assert not app.state.controller.user_lock(user_id).locked()
            for _ in range(4):
                app.state.execution_slots.release()
    asyncio.run(check())
