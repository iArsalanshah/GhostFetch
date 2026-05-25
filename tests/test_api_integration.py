from fastapi.testclient import TestClient

import main
import src.utils.security as security
from src.core.scraper import ScraperError


async def _noop():
    return None


def _test_client(monkeypatch):
    monkeypatch.setattr(main.scraper, "start", _noop)
    monkeypatch.setattr(main.scraper, "stop", _noop)
    monkeypatch.setattr(main.job_manager, "start", _noop)
    monkeypatch.setattr(main.job_manager, "stop", _noop)
    return TestClient(main.app)


def test_sync_requires_api_key(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "secret")
    client = _test_client(monkeypatch)
    resp = client.get("/fetch/sync", params={"url": "https://example.com"})
    assert resp.status_code == 401


def test_sync_rejects_private_url(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "secret")
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})
    client = _test_client(monkeypatch)
    resp = client.get(
        "/fetch/sync",
        params={"url": "https://127.0.0.1"},
        headers={"X-API-Key": "secret"},
    )
    assert resp.status_code == 400


def test_sync_response_shape(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "secret")
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})

    async def fake_fetch(url, context_id=None, auth_storage_state_path=None):
        return {"metadata": {"title": "T"}, "markdown": "Body"}

    monkeypatch.setattr(main.scraper, "fetch", fake_fetch)
    client = _test_client(monkeypatch)
    resp = client.post(
        "/fetch/sync",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://example.com"
    assert data["status"] == "success"
    assert data["metadata"]["title"] == "T"
    assert data["markdown"] == "Body"


def test_events_requires_api_key(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "secret")
    client = _test_client(monkeypatch)
    resp = client.get("/events")
    assert resp.status_code == 401


def test_sync_returns_auth_status_shape(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "secret")
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})

    async def fake_fetch(url, context_id=None, auth_storage_state_path=None):
        raise ScraperError("Authentication required", "auth_required", retryable=False)

    monkeypatch.setattr(main.scraper, "fetch", fake_fetch)
    client = _test_client(monkeypatch)
    resp = client.post(
        "/fetch/sync",
        json={"url": "https://example.com"},
        headers={"X-API-Key": "secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "auth_required"
    assert data["url"] == "https://example.com"
