import ipaddress
import os
import re
import socket
from typing import Optional, Set
from urllib.parse import urlparse

from src.utils.config import settings


class URLValidationError(ValueError):
    pass


CONTEXT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _validate_scheme(parsed, allowed_schemes) -> None:
    scheme = parsed.scheme.lower()
    if scheme not in allowed_schemes:
        raise URLValidationError(f"URL scheme must be one of: {', '.join(allowed_schemes)}")


def _is_blocked_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(
        (
            addr.is_private,
            addr.is_loopback,
            addr.is_link_local,
            addr.is_multicast,
            addr.is_reserved,
            addr.is_unspecified,
        )
    )


def _resolve_ips(hostname: str) -> Set[str]:
    ips: Set[str] = set()
    for result in socket.getaddrinfo(hostname, None):
        sockaddr = result[4]
        if sockaddr:
            ips.add(sockaddr[0])
    return ips


def _validate_host(hostname: Optional[str], *, block_private: bool) -> None:
    if not hostname:
        raise URLValidationError("URL must include a hostname")

    host = hostname.strip().lower().rstrip(".")
    if not host:
        raise URLValidationError("URL hostname is empty")

    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise URLValidationError("Localhost/local domains are not allowed")

    # If the hostname is already a literal IP, validate directly.
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if _is_blocked_ip(host) and block_private:
            raise URLValidationError("Private or restricted IP addresses are not allowed")
        return

    if not block_private:
        return

    try:
        resolved_ips = _resolve_ips(host)
    except socket.gaierror as exc:
        raise URLValidationError(f"Hostname resolution failed: {exc}") from exc

    if not resolved_ips:
        raise URLValidationError("Hostname did not resolve to an IP address")

    for ip in resolved_ips:
        if _is_blocked_ip(ip):
            raise URLValidationError("Resolved host points to private or restricted IP space")


def validate_domain_host(domain: str) -> str:
    if not isinstance(domain, str) or not domain.strip():
        raise URLValidationError("domain is required")

    host = domain.strip().lower().rstrip(".")
    _validate_host(host, block_private=settings.BLOCK_PRIVATE_NETWORKS)
    return host


def validate_target_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise URLValidationError("URL is required")

    parsed = urlparse(url.strip())
    _validate_scheme(parsed, settings.ALLOWED_URL_SCHEMES)

    if parsed.username or parsed.password:
        raise URLValidationError("URLs with embedded credentials are not allowed")

    _validate_host(parsed.hostname, block_private=settings.BLOCK_PRIVATE_NETWORKS)
    return url.strip()


def validate_callback_url(callback_url: Optional[str]) -> Optional[str]:
    if callback_url is None:
        return None

    value = callback_url.strip()
    if not value:
        return None

    parsed = urlparse(value)
    _validate_scheme(parsed, ("https",))

    _validate_host(parsed.hostname, block_private=settings.BLOCK_PRIVATE_NETWORKS)

    if settings.CALLBACK_ALLOWED_HOSTS:
        host = (parsed.hostname or "").lower().rstrip(".")
        allowed = any(host == h or host.endswith(f".{h}") for h in settings.CALLBACK_ALLOWED_HOSTS)
        if not allowed:
            raise URLValidationError("callback_url host is not allowlisted")

    return value


def validate_proxy_url(proxy_url: str) -> str:
    if not isinstance(proxy_url, str) or not proxy_url.strip():
        raise URLValidationError("Proxy URL is required")
    value = proxy_url.strip()
    parsed = urlparse(value)
    _validate_scheme(parsed, ("http", "https"))
    _validate_host(parsed.hostname, block_private=settings.BLOCK_PRIVATE_NETWORKS)
    return value


def validate_context_id(context_id: Optional[str]) -> Optional[str]:
    if context_id is None:
        return None
    value = context_id.strip()
    if not CONTEXT_ID_PATTERN.fullmatch(value):
        raise URLValidationError("context_id must match ^[a-zA-Z0-9_-]{1,64}$")
    return value


def context_storage_path(storage_dir: str, context_id: str) -> str:
    filename = f"context_{context_id}.json"
    base_dir = os.path.abspath(storage_dir)
    path = os.path.abspath(os.path.join(base_dir, filename))
    if os.path.commonpath([base_dir, path]) != base_dir:
        raise URLValidationError("Resolved context storage path is outside storage directory")
    return path
