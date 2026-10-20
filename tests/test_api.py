import asyncio
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from server.main import COOKIE, create_app, password_hash, password_matches, token_hash


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path, tmp_path / "dist")


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


def register(client, email="shivam@example.com"):
    return client.post("/api/auth/register", json={"name": "Shivam Gupta", "email": email, "password": "correct horse battery staple"})


def test_password_hash_salted_and_constant_result():
    one, two = password_hash("a long password"), password_hash("a long password")
    assert one != two
    assert password_matches("a long password", one)
    assert not password_matches("wrong", one)


def test_register_session_logout_login(client, app):
    assert client.get("/api/overview").status_code == 401
    response = register(client)
    assert response.status_code == 201
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    session = client.get("/api/session").json()
    assert session["user"]["name"] == "Shivam Gupta"
    assert session["demo"] is False
    raw_token = client.cookies.get(COOKIE)
    with app.state.store.connection() as conn:
        stored = conn.execute("SELECT token FROM sessions").fetchone()["token"]
    assert stored == token_hash(raw_token) and stored != raw_token
    assert client.get("/api/overview").json()["runs"] == []
    assert client.post("/api/auth/logout", json={}).status_code == 200
    assert client.get("/api/session").json()["user"] is None
    assert client.post("/api/auth/login", json={"email": "shivam@example.com", "password": "wrongpassword"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "shivam@example.com", "password": "correct horse battery staple"}).status_code == 200
    assert register(client).status_code == 409


def test_auth_validation_and_csrf(client):
    assert client.post("/api/auth/register", json={"name": "  ", "email": "bad", "password": "short"}).status_code == 422
    assert client.post("/api/demo/session", json={}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/demo/session", json={}, headers={"sec-fetch-site": "cross-site"}).status_code == 403
    assert client.post("/api/demo/session", content="{}").status_code == 415
    assert client.post("/api/demo/session", json={}, headers={"Origin": "http://testserver"}).status_code == 200
    assert client.get("/api/session").headers["cache-control"] == "no-store"
    assert client.get("/healthz").status_code == 200


def test_demo_isolation_and_owner_checks(app):
    with TestClient(app) as one, TestClient(app) as two:
        user_one = one.post("/api/demo/session", json={}).json()["user"]
        user_two = two.post("/api/demo/session", json={}).json()["user"]
        assert user_one["id"] != user_two["id"]
        from server.engine import new_run
        run = new_run("duplicate-charge")
        app.state.store.save_run(user_one["id"], run)
        assert one.get("/api/runs/" + run["id"]).status_code == 200
        for suffix in ["", "/evidence", "/artifacts/release.zip"]:
            assert two.get("/api/runs/" + run["id"] + suffix).status_code == 404
        assert two.get("/api/overview").json()["runs"] == []
        assert one.get("/api/session").json()["demo"] is True


def test_session_expiry(client, app):
    register(client)
    with app.state.store.connection() as conn:
        conn.execute("UPDATE sessions SET expires=0")
    assert client.get("/api/session").json()["user"] is None
    assert client.get("/api/overview").status_code == 401


def test_rate_limiting(client):
    for _ in range(30):
        assert client.post("/api/auth/login", json={"email": "none@example.com", "password": "wrongpassword"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "none@example.com", "password": "wrongpassword"}).status_code == 429


def test_contract_rejects_arbitrary_scenarios(client):
    client.post("/api/demo/session", json={})
    assert client.post("/api/runs", json={"scenario": "; curl attacker"}).status_code == 422


def test_async_run_lock_and_evidence(app):
    async def check():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            await client.post("/api/demo/session", json={})
            response = await client.post("/api/runs", json={"scenario": "duplicate-charge"})
            assert response.status_code == 202
            run_id = response.json()["id"]
            conflict = await client.post("/api/runs", json={"scenario": "tenant-leak"})
            assert conflict.status_code == 409
            await asyncio.gather(*list(app.state.tasks))
            run = (await client.get("/api/runs/" + run_id)).json()
            assert run["status"] == "recovered", run["decision"]
            evidence = await client.get("/api/runs/" + run_id + "/evidence")
            assert evidence.json()["integrity"]["verified"]
            assert "attachment" in evidence.headers["content-disposition"]
            artifact = await client.get("/api/runs/" + run_id + "/artifacts/release.zip")
            assert artifact.status_code == 200 and artifact.content[:2] == b"PK"
            store = app.state.store
            user_id = (await client.get("/api/session")).json()["user"]["id"]
            run["events"][0]["detail"] = "tampered"
            store.save_run(user_id, run)
            assert (await client.get("/api/runs/" + run_id + "/evidence")).status_code == 409
    asyncio.run(check())


def test_restart_marks_incomplete_run_failed(tmp_path):
    from server.engine import new_run
    from server.store import Store
    store = Store(tmp_path)
    with store.connection() as conn:
        conn.execute("INSERT INTO users(id,name,email) VALUES('u','u','u@example.com')")
    run = new_run("duplicate-charge")
    store.save_run("u", run)
    restarted = Store(tmp_path)
    assert restarted.run("u", run["id"])["status"] == "failed"


def test_secure_cookie_and_session_rotation(tmp_path, monkeypatch):
    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("APP_ORIGIN", "https://example.test")
    app = create_app(tmp_path)
    with TestClient(app, base_url="https://example.test") as client:
        response = register(client)
        assert "Secure" in response.headers["set-cookie"]
        old = client.cookies.get(COOKIE)
        assert client.post("/api/auth/login", json={"email": "shivam@example.com", "password": "correct horse battery staple"}).status_code == 200
        assert client.cookies.get(COOKIE) != old
        with app.state.store.connection() as conn:
            assert not conn.execute("SELECT * FROM sessions WHERE token=?", (token_hash(old),)).fetchone()
        assert client.get("/healthz").headers["strict-transport-security"].startswith("max-age=")


def test_artifact_tamper_is_rejected(client, app, tmp_path):
    from server.engine import new_run
    import hashlib
    user = client.post("/api/demo/session", json={}).json()["user"]
    run = new_run("duplicate-charge")
    run["status"] = "recovered"
    run["artifacts"] = [{"name": "release.zip", "type": "release-bundle", "sha256": hashlib.sha256(b"original").hexdigest()}]
    run["completedAt"] = "2026-10-20T00:00:00Z"
    app.state.store.save_run(user["id"], run)
    app.state.store.seal_run(user["id"], run)
    folder = tmp_path / "runs" / run["id"]
    folder.mkdir(parents=True)
    (folder / "release.zip").write_bytes(b"changed")
    assert client.get("/api/runs/" + run["id"] + "/artifacts/release.zip").status_code == 409
    assert client.get("/api/runs/" + run["id"] + "/artifacts/aftercare.sqlite3").status_code == 404


def test_body_limit_for_chunked_requests(app):
    async def check():
        async def body():
            for _ in range(20):
                yield b" " * 1024
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/demo/session", content=body(), headers={"content-type": "application/json"})
            assert response.status_code == 413
    asyncio.run(check())


def test_completed_manifest_tamper_rejected_even_with_valid_event_chain(client, app):
    from server.engine import new_run
    user = client.post("/api/demo/session", json={}).json()["user"]
    run = new_run("duplicate-charge")
    run.update(status="blocked", completedAt="2026-10-20T00:00:00Z")
    app.state.store.save_run(user["id"], run)
    app.state.store.seal_run(user["id"], run)
    assert client.get("/api/runs/" + run["id"] + "/evidence").status_code == 200
    run["diff"]["after"] = "tampered source outside the event chain"
    app.state.store.save_run(user["id"], run)
    assert client.get("/api/runs/" + run["id"] + "/evidence").status_code == 409
    with pytest.raises(ValueError, match="immutable"):
        app.state.store.seal_run(user["id"], run)


def test_datastore_outage_is_retryable_and_fails_closed(client, app, monkeypatch):
    from google.api_core.exceptions import ServiceUnavailable
    monkeypatch.setattr(app.state.store, "health", lambda: (_ for _ in ()).throw(ServiceUnavailable("internal detail")))
    response = client.get("/healthz")
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert "internal detail" not in response.text


def test_overview_counts_all_retained_runs(client, app):
    from server.engine import new_run
    user = client.post("/api/demo/session", json={}).json()["user"]
    for _ in range(55):
        app.state.store.save_run(user["id"], new_run("duplicate-charge"))
    assert client.get("/api/overview").json()["metrics"]["totalRuns"] == 55
