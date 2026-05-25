from fastapi.testclient import TestClient

import main
import src.utils.security as security


async def _noop():
    return None


def _test_client(monkeypatch):
    monkeypatch.setattr(main.scraper, "start", _noop)
    monkeypatch.setattr(main.scraper, "stop", _noop)
    monkeypatch.setattr(main.job_manager, "start", _noop)
    monkeypatch.setattr(main.job_manager, "stop", _noop)
    return TestClient(main.app)


def test_auth_session_lifecycle_and_sync_fetch(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "secret")
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})

    captured = {}

    async def fake_fetch(url, context_id=None, auth_storage_state_path=None):
        captured["path"] = auth_storage_state_path
        return {"metadata": {"title": "ok"}, "markdown": "body"}

    monkeypatch.setattr(main.scraper, "fetch", fake_fetch)
    client = _test_client(monkeypatch)

    imported = client.post(
        "/auth/sessions/import",
        json={
            "domain": "example.com",
            "storage_state": {"cookies": [], "origins": []},
            "session_id": "sess_1",
            "ttl_seconds": 3600,
        },
        headers={"X-API-Key": "secret"},
    )
    assert imported.status_code == 201

    resp = client.post(
        "/fetch/sync",
        json={"url": "https://example.com", "auth_session_id": "sess_1"},
        headers={"X-API-Key": "secret"},
    )
    assert resp.status_code == 200
    assert captured.get("path", "").endswith("sess_1.state.json")

    listed = client.get("/auth/sessions", headers={"X-API-Key": "secret"})
    assert listed.status_code == 200
    assert any(s["id"] == "sess_1" for s in listed.json()["sessions"])

    revoked = client.delete("/auth/sessions/sess_1", headers={"X-API-Key": "secret"})
    assert revoked.status_code == 200


def test_auth_session_domain_mismatch(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "secret")
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})
    client = _test_client(monkeypatch)

    imported = client.post(
        "/auth/sessions/import",
        json={"domain": "example.com", "storage_state": {"cookies": [], "origins": []}, "session_id": "sess_2"},
        headers={"X-API-Key": "secret"},
    )
    assert imported.status_code == 201

    resp = client.post(
        "/fetch/sync",
        json={"url": "https://another-example.com", "auth_session_id": "sess_2"},
        headers={"X-API-Key": "secret"},
    )
    assert resp.status_code == 400
