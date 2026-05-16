import pytest

import src.utils.security as security
from src.utils.config import settings
from src.utils.security import URLValidationError, validate_callback_url, validate_target_url


def test_validate_target_url_accepts_https(monkeypatch):
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})
    assert validate_target_url("https://example.com/path") == "https://example.com/path"


def test_validate_target_url_rejects_localhost():
    with pytest.raises(URLValidationError):
        validate_target_url("http://localhost:8080")


def test_validate_target_url_rejects_credentialed_url():
    with pytest.raises(URLValidationError):
        validate_target_url("https://user:pass@example.com")


def test_validate_callback_requires_https():
    with pytest.raises(URLValidationError):
        validate_callback_url("http://hooks.example.com/callback")


def test_validate_callback_allows_none():
    assert validate_callback_url(None) is None


def test_validate_target_url_rejects_private_ip():
    with pytest.raises(URLValidationError):
        validate_target_url("https://127.0.0.1")


def test_validate_callback_allowlist(monkeypatch):
    monkeypatch.setattr(settings, "CALLBACK_ALLOWED_HOSTS", ("hooks.example.com",))
    monkeypatch.setattr(security, "_resolve_ips", lambda host: {"93.184.216.34"})
    assert validate_callback_url("https://hooks.example.com/path") == "https://hooks.example.com/path"
    with pytest.raises(URLValidationError):
        validate_callback_url("https://evil.example.net/path")
