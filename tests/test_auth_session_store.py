import os
import time
import json

import pytest

import src.utils.security as security
from src.auth_session import AuthSessionStore
from src.utils.security import URLValidationError


def test_resolve_storage_path_marks_used_and_checks_domain(monkeypatch, tmp_path):
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})
    store = AuthSessionStore(str(tmp_path))

    created = store.create_session(
        domain="example.com",
        storage_state={"cookies": [], "origins": []},
        ttl_seconds=3600,
        session_id="sess_ok",
    )

    resolved = store.resolve_storage_path("sess_ok", "https://www.example.com/profile")
    assert resolved == created.storage_state_path

    session = store.get_session("sess_ok", require_active=False)
    assert session.last_used_at is not None

    with pytest.raises(URLValidationError):
        store.resolve_storage_path("sess_ok", "https://evil.com")


def test_prune_expired_sessions_removes_files(monkeypatch, tmp_path):
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})
    store = AuthSessionStore(str(tmp_path))

    created = store.create_session(
        domain="example.com",
        storage_state={"cookies": [], "origins": []},
        ttl_seconds=60,
        session_id="sess_expired",
    )

    meta_path = os.path.join(store.base_dir, "sess_expired.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["expires_at"] = time.time() - 10
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    removed = store.prune_expired_sessions()
    assert removed == 1
    assert not os.path.exists(meta_path)
    assert not os.path.exists(created.storage_state_path)


def test_session_files_are_restricted(monkeypatch, tmp_path):
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})
    store = AuthSessionStore(str(tmp_path))
    store.create_session(
        domain="example.com",
        storage_state={"cookies": [], "origins": []},
        ttl_seconds=3600,
        session_id="sess_perms",
    )

    meta_mode = os.stat(os.path.join(store.base_dir, "sess_perms.json")).st_mode & 0o777
    state_mode = os.stat(os.path.join(store.base_dir, "sess_perms.state.json")).st_mode & 0o777
    assert meta_mode & 0o077 == 0
    assert state_mode & 0o077 == 0
