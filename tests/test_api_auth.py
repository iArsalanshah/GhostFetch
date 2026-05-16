import pytest
from fastapi import HTTPException

import main


def test_enforce_api_key_allows_when_disabled(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", False)
    main._enforce_api_key(None)


def test_enforce_api_key_rejects_missing_key_when_required(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "secret")
    with pytest.raises(HTTPException) as exc:
        main._enforce_api_key(None)
    assert exc.value.status_code == 401


def test_enforce_api_key_rejects_when_not_configured(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "")
    with pytest.raises(HTTPException) as exc:
        main._enforce_api_key("anything")
    assert exc.value.status_code == 503


def test_enforce_api_key_accepts_valid_key(monkeypatch):
    monkeypatch.setattr(main.settings, "REQUIRE_API_KEY", True)
    monkeypatch.setattr(main.settings, "API_KEY", "secret")
    main._enforce_api_key("secret")
