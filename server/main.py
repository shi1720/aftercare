"""Aftercare API. Run with: uvicorn server.main:app --host 0.0.0.0 --port 8080."""
import asyncio
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .engine import Controller, POLICY, SCENARIOS, new_run
from .evidence import canonical, verify_chain
from .store import Store
from .gitlab_evidence import GitLabEvidence

COOKIE = "aftercare_session"
SESSION_SECONDS = 60 * 60 * 24 * 7
ROOT = Path(__file__).resolve().parent.parent
HASH_SLOTS = threading.BoundedSemaphore(4)


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address")
        return value


class Registration(Credentials):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def name_valid(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value


class RunInput(BaseModel):
    scenario: Literal["duplicate-charge", "tenant-leak", "unsafe-repair"]


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    with HASH_SLOTS:
        derived = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
    return salt + ":" + derived.hex()


def password_matches(password, stored):
    if not stored:
        return False
    return secrets.compare_digest(password_hash(password, stored.split(":")[0]), stored)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def public_user(row):
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def create_app(data_dir=None, frontend_dir=None):
    if os.environ.get("AFTERCARE_STORE") == "firestore":
        from .firestore_store import FirestoreStore
        store = FirestoreStore(data_dir or os.environ.get("DATA_DIR", "/tmp/aftercare"), os.environ["GOOGLE_CLOUD_PROJECT"], os.environ.get("FIRESTORE_DATABASE", "aftercare"))
    else:
        store = Store(data_dir or os.environ.get("DATA_DIR", str(ROOT / ".data")))
    controller = Controller(store)
    frontend = Path(frontend_dir or ROOT / "web" / "dist")
    secure_cookies = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    app_origin = os.environ.get("APP_ORIGIN", "").rstrip("/")

    @asynccontextmanager
    async def lifespan(app):
        yield
        if app.state.tasks:
            # Workers persist after each step. Allow active fixed workloads to finish.
            await asyncio.gather(*list(app.state.tasks), return_exceptions=True)

    app = FastAPI(title="Aftercare", version="1.0.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.store, app.state.controller, app.state.tasks = store, controller, set()
    app.state.execution_slots = threading.BoundedSemaphore(4)
    app.state.gitlab_evidence = GitLabEvidence()

    @app.exception_handler(sqlite3.OperationalError)
    async def sqlite_unavailable(request, exc):
        return JSONResponse({"detail": "Datastore temporarily unavailable. Please retry shortly."}, status_code=503, headers={"Retry-After": "5"})

    # Google API retries are bounded by the SDK. Fail closed and expose a
    # retryable response rather than a stack trace on permission/network errors.
    from google.api_core.exceptions import GoogleAPICallError, RetryError
    async def cloud_unavailable(request, exc):
        return JSONResponse({"detail": "Datastore temporarily unavailable. Please retry shortly."}, status_code=503, headers={"Retry-After": "5"})
    app.add_exception_handler(GoogleAPICallError, cloud_unavailable)
    app.add_exception_handler(RetryError, cloud_unavailable)

    @app.middleware("http")
    async def security(request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            expected = app_origin or str(request.base_url).rstrip("/")
            origin_rejected = origin and origin != expected
            if origin_rejected or request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Cross-origin mutation rejected"}, status_code=403)
            if request.url.path.startswith("/api/"):
                if request.headers.get("content-type", "").split(";")[0] != "application/json":
                    return JSONResponse({"detail": "application/json required"}, status_code=415)
                try:
                    size = int(request.headers.get("content-length", "0"))
                except ValueError:
                    return JSONResponse({"detail": "Invalid body size"}, status_code=400)
                if size > 16384:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
                # Bound chunked bodies too; Content-Length alone is insufficient.
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 16384:
                        return JSONResponse({"detail": "Request too large"}, status_code=413)
                request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if secure_cookies:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    def rate_limit(key, limit=30, seconds=900):
        if not store.check_rate_limit(key, limit, seconds, time.time()):
            raise HTTPException(429, "Too many attempts. Please try again later.")

    def current_user(request, required=True):
        token = request.cookies.get(COOKIE, "")
        row = store.session_user(token_hash(token), time.time()) if token else None
        if not row and required:
            raise HTTPException(401, "Sign in or start an isolated sandbox")
        return row

    def issue_session(user_id, request, response):
        token = secrets.token_urlsafe(32)
        previous = request.cookies.get(COOKIE)
        store.put_session(token_hash(token), user_id, time.time()+SESSION_SECONDS, token_hash(previous) if previous else None)
        response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, secure=secure_cookies, samesite="strict", path="/")

    def owned_run(request, run_id):
        user = current_user(request)
        run = store.run(user["id"], run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        return run

    @app.get("/api/health")
    @app.get("/healthz")
    def health():
        store.health()
        return {"status": "ok", "service": "aftercare", "mode": "reference", "sandbox": True}

    @app.get("/api/session")
    def session(request: Request):
        user = current_user(request, required=False)
        return {"user": public_user(user) if user else None, "demo": bool(user["demo"]) if user else False}

    @app.post("/api/demo/session")
    def demo_session(request: Request, response: Response):
        user = current_user(request, required=False)
        if user:
            return {"user": public_user(user), "demo": bool(user["demo"])}
        rate_limit("global-demo", 300, 3600)
        rate_limit("demo:" + (request.client.host if request.client else "local"), 60, 3600)
        user_id = str(uuid.uuid4())
        email = "sandbox-" + user_id + "@aftercare.local"
        store.create_user(user_id, "Sandbox visitor", email, demo=True)
        issue_session(user_id, request, response)
        return {"user": {"id": user_id, "name": "Sandbox visitor", "email": email}, "demo": True}

    @app.post("/api/auth/register", status_code=201)
    def register(body: Registration, request: Request, response: Response):
        rate_limit("global-auth", 180, 60)
        rate_limit("register:" + (request.client.host if request.client else "local"), 20, 3600)
        user_id = str(uuid.uuid4())
        try:
            store.create_user(user_id, body.name, body.email, password_hash(body.password))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "An account with that email already exists")
        issue_session(user_id, request, response)
        return {"user": {"id": user_id, "name": body.name, "email": body.email}, "demo": False}

    @app.post("/api/auth/login")
    def login(body: Credentials, request: Request, response: Response):
        rate_limit("global-auth", 180, 60)
        rate_limit("login:" + (request.client.host if request.client else "local"), 30, 900)
        user = store.user_by_email(body.email)
        if user and user["demo"]:
            user = None
        # Same scrypt work for unknown users limits account enumeration by timing.
        valid = password_matches(body.password, user["password"] if user else "00"*16 + ":" + "00"*32)
        if not user or not valid:
            raise HTTPException(401, "Email or password is incorrect")
        issue_session(user["id"], request, response)
        return {"user": public_user(user), "demo": False}

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response):
        token = request.cookies.get(COOKIE, "")
        store.delete_session(token_hash(token))
        response.delete_cookie(COOKIE, path="/", secure=secure_cookies, httponly=True, samesite="strict")
        return {"ok": True}

    @app.get("/api/overview")
    def overview(request: Request):
        user = current_user(request)
        runs = store.runs(user["id"])
        return {"project": {"name": "RetryPay sandbox", "environment": "isolated synthetic payments"}, "runs": runs,
                "contracts": [
                    {"id": "idempotency", "name": "One checkout. One charge.", "description": "A repeated tenant + idempotency key must resolve to one synthetic debit.", "status": "enforced", "source": "server/sandbox.py:Contracts.test_retry_is_one_charge", "category": "revenue-integrity"},
                    {"id": "tenant-isolation", "name": "Tenant boundaries hold", "description": "Cross-tenant order reads return not found.", "status": "enforced", "source": "server/sandbox.py:Contracts.test_cross_tenant_order_hidden", "category": "data-isolation"},
                    {"id": "input-validation", "name": "Conflicting retries fail closed", "description": "Changing an amount under the same key cannot produce another debit.", "status": "enforced", "source": "server/sandbox.py:Contracts.test_idempotency_conflict_fails_closed", "category": "input-validation"}],
                "metrics": {"totalRuns": len(runs), "recovered": sum(r["status"] == "recovered" for r in runs), "blocked": sum(r["status"] == "blocked" for r in runs), "protectedRequests": sum(r["metrics"]["requestsReplayed"] for r in runs if r["status"] == "recovered")},
                "integration": {"mode": "reference", "gitlabConfigured": False, "detail": "Local deterministic reference controller. Import the Duo flow into GitLab to run AI diagnosis and repair."}, "policy": POLICY}

    @app.get("/api/gitlab/evidence")
    def gitlab_evidence(request: Request):
        current_user(request)
        return app.state.gitlab_evidence.get()

    @app.post("/api/runs", status_code=202)
    async def start_run(body: RunInput, request: Request):
        user = current_user(request)
        rate_limit("runs:" + user["id"], 30, 3600)
        rate_limit("global-runs", 300, 3600)
        if store.run_count(user["id"]) >= 100:
            raise HTTPException(429, "Sandbox run quota reached")
        if store.run_count() >= 3000:
            raise HTTPException(429, "Sandbox capacity reached")
        lock = controller.user_lock(user["id"])
        if not lock.acquire(blocking=False):
            raise HTTPException(409, "A recovery is already active in your sandbox")
        if not app.state.execution_slots.acquire(blocking=False):
            lock.release()
            raise HTTPException(429, "Sandbox workers are busy. Please retry shortly.")
        run = new_run(body.scenario)
        def finish_task(task):
            app.state.tasks.discard(task)
            app.state.execution_slots.release()
        try:
            store.save_run(user["id"], run)
            initial = json.loads(json.dumps(run))
            task = asyncio.create_task(asyncio.to_thread(controller.execute, user["id"], run))
            app.state.tasks.add(task)
            task.add_done_callback(finish_task)
        except Exception:
            app.state.execution_slots.release()
            lock.release()
            raise
        return initial

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str, request: Request):
        return owned_run(request, run_id)

    @app.get("/api/runs/{run_id}/evidence")
    def evidence(run_id: str, request: Request):
        run = owned_run(request, run_id)
        if not verify_chain(run["events"]) or (run["status"] != "running" and not store.seal_matches(current_user(request)["id"], run)):
            raise HTTPException(409, "Evidence integrity verification failed")
        return Response(canonical(controller.envelope(run)), media_type="application/json", headers={"Content-Disposition": 'attachment; filename="aftercare-' + run["id"] + '-evidence.json"'})

    @app.get("/api/runs/{run_id}/artifacts/{name}")
    def artifact(run_id: str, name: str, request: Request):
        run = owned_run(request, run_id)
        if run["status"] != "running" and not store.seal_matches(current_user(request)["id"], run):
            raise HTTPException(409, "Evidence integrity verification failed")
        allowed = next((artifact for artifact in run["artifacts"] if artifact["name"] == name), None)
        if not allowed or name not in {"release.zip", "sbom.cdx.json", "synthetic-ledger.json"}:
            raise HTTPException(404, "Artifact not found")
        data = store.get_artifact(run["id"], name)
        if data is None or hashlib.sha256(data).hexdigest() != allowed["sha256"]:
            raise HTTPException(409, "Artifact integrity verification failed")
        return Response(data, media_type="application/zip" if name.endswith(".zip") else "application/json", headers={"Content-Disposition": 'attachment; filename="' + name + '"'})

    if (frontend / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(frontend / "assets")), name="assets")

    @app.get("/{path:path}")
    def frontend_route(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "API route not found")
        if (frontend / "index.html").is_file():
            return FileResponse(frontend / "index.html")
        return JSONResponse({"service": "Aftercare", "detail": "API ready. Build web/ for the dashboard.", "health": "/api/health"})

    return app


app = create_app()
