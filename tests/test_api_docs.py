"""API reference remains usable with the application's self-only script CSP."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from server.main import create_app


def test_api_explorer_uses_only_local_assets_and_live_schema(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        response = client.get("/api/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "script-src 'self'" in response.headers["content-security-policy"]
        html = response.text
        assert "Send request" in client.get("/api/docs-assets/docs.js").text
        assert "<script>" not in html and "<style>" not in html
        assert not re.search(r"\bon\w+\s*=", html, re.IGNORECASE)
        assets = re.findall(r'(?:src|href)="([^"]+)"', html)
        assert "/api/docs-assets/docs.js" in assets
        assert "/api/docs-assets/docs.css" in assets
        assert all(not asset.startswith(("http:", "https:", "//")) for asset in assets)
        for asset in assets:
            if asset.startswith("/api/docs-assets/"):
                assert client.get(asset).status_code == 200
        javascript = client.get("/api/docs-assets/docs.js").text
        assert "fetch('/api/openapi.json'" in javascript
        assert "credentials: 'same-origin'" in javascript
        assert "textContent" in javascript and "innerHTML" not in javascript
        schema = client.get("/api/openapi.json").json()
        assert "/api/auth/login" in schema["paths"]
        assert "/api/runs/{run_id}/evidence" in schema["paths"]
        assert "/api/docs" not in schema["paths"]
        assert client.get("/api/docs-assets/missing.js").status_code == 404


def test_container_includes_api_explorer_assets():
    root = Path(__file__).resolve().parents[1]
    assert "COPY server/ server/" in (root / "Dockerfile").read_text()
    for name in ["index.html", "docs.js", "docs.css"]:
        assert (root / "server" / "static" / "docs" / name).is_file()
