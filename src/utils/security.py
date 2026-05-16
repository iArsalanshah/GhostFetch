import ipaddress
import socket
from typing import Optional, Set
from urllib.parse import urlparse

from src.utils.config import settings


class URLValidationError(ValueError):
    pass


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
        if _is_blocked_ip(host) and block_private:
            raise URLValidationError("Private or restricted IP addresses are not allowed")
        return
    except ValueError:
        pass

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


def validate_target_url(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        raise URLValidationError("URL is required")

    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    if scheme not in settings.ALLOWED_URL_SCHEMES:
        raise URLValidationError(f"URL scheme must be one of: {', '.join(settings.ALLOWED_URL_SCHEMES)}")

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
    scheme = parsed.scheme.lower()
    if scheme not in ("https",):
        raise URLValidationError("callback_url must use https")

    _validate_host(parsed.hostname, block_private=settings.BLOCK_PRIVATE_NETWORKS)

    if settings.CALLBACK_ALLOWED_HOSTS:
        host = (parsed.hostname or "").lower().rstrip(".")
        allowed = any(host == h or host.endswith(f".{h}") for h in settings.CALLBACK_ALLOWED_HOSTS)
        if not allowed:
            raise URLValidationError("callback_url host is not allowlisted")

    return value
