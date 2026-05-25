import json
import logging
import os
import time
import uuid
from json import JSONDecodeError
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from src.utils.config import settings
from src.utils.security import URLValidationError, validate_context_id, validate_domain_host

logger = logging.getLogger("GhostFetch.AuthSession")


@dataclass
class AuthSession:
    id: str
    domain: str
    storage_state_path: str
    created_at: float
    expires_at: float
    last_used_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "domain": self.domain,
            "storage_state_path": self.storage_state_path,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_used_at": self.last_used_at,
            "status": "active" if self.expires_at > time.time() else "expired",
        }


class AuthSessionStore:
    DIR_MODE = 0o700
    FILE_MODE = 0o600

    def __init__(self, storage_dir: str):
        self.base_dir = os.path.join(storage_dir, "auth_sessions")
        os.makedirs(self.base_dir, exist_ok=True)
        self._restrict_permissions(self.base_dir, self.DIR_MODE)

    def _restrict_permissions(self, path: str, mode: int) -> None:
        try:
            os.chmod(path, mode)
        except OSError:
            logger.debug("Failed to set permissions for %s", path, exc_info=True)

    def _write_json_atomic(self, path: str, payload: Dict[str, Any]) -> None:
        temp_path = f"{path}.tmp.{uuid.uuid4().hex}"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        self._restrict_permissions(temp_path, self.FILE_MODE)
        os.replace(temp_path, path)
        self._restrict_permissions(path, self.FILE_MODE)

    def _meta_path(self, session_id: str) -> str:
        return os.path.join(self.base_dir, f"{session_id}.json")

    def _state_path(self, session_id: str) -> str:
        return os.path.join(self.base_dir, f"{session_id}.state.json")

    def _safe_session_id(self, value: Optional[str]) -> str:
        if value:
            validated = validate_context_id(value)
            if validated is None:
                raise URLValidationError("Invalid session_id")
            return validated
        return uuid.uuid4().hex

    def create_session(self, domain: str, storage_state: Dict[str, Any], ttl_seconds: int, session_id: Optional[str] = None) -> AuthSession:
        safe_domain = validate_domain_host(domain)
        sid = self._safe_session_id(session_id)
        now = time.time()

        state_path = self._state_path(sid)
        meta_path = self._meta_path(sid)
        self.prune_expired_sessions()
        self._write_json_atomic(state_path, storage_state)

        session = AuthSession(
            id=sid,
            domain=safe_domain,
            storage_state_path=state_path,
            created_at=now,
            expires_at=now + max(60, ttl_seconds),
            last_used_at=None,
        )
        self._write_json_atomic(meta_path, session.to_dict())
        return session

    def get_session(self, session_id: str, require_active: bool = True) -> AuthSession:
        sid = self._safe_session_id(session_id)
        meta_path = self._meta_path(sid)
        if not os.path.exists(meta_path):
            raise URLValidationError("auth_session_id not found")

        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        session = AuthSession(
            id=data["id"],
            domain=data["domain"],
            storage_state_path=data["storage_state_path"],
            created_at=float(data["created_at"]),
            expires_at=float(data["expires_at"]),
            last_used_at=data.get("last_used_at"),
        )
        if require_active and session.expires_at <= time.time():
            self.revoke_session(sid)
            raise URLValidationError("auth_session_id expired")
        if not os.path.exists(session.storage_state_path):
            raise URLValidationError("auth session storage state is missing")
        return session

    def list_sessions(self) -> List[Dict[str, Any]]:
        self.prune_expired_sessions()
        sessions: List[Dict[str, Any]] = []
        for name in os.listdir(self.base_dir):
            if not name.endswith(".json") or name.endswith(".state.json"):
                continue
            path = os.path.join(self.base_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(data)
            except (OSError, JSONDecodeError, ValueError, KeyError):
                logger.debug("Skipping unreadable auth session metadata file: %s", path, exc_info=True)
                continue
        sessions.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        return sessions

    def mark_used(self, session_id: str) -> None:
        session = self.get_session(session_id, require_active=False)
        session.last_used_at = time.time()
        self._write_json_atomic(self._meta_path(session.id), session.to_dict())

    def resolve_storage_path(self, session_id: str, target_url: str) -> str:
        session = self.get_session(session_id)
        host = (urlparse(target_url).hostname or "").lower().rstrip(".")
        if not host:
            raise URLValidationError("URL must include a hostname")
        if host != session.domain and not host.endswith(f".{session.domain}"):
            raise URLValidationError("URL host does not match auth session domain")
        self.mark_used(session_id)
        return session.storage_state_path

    def prune_expired_sessions(self) -> int:
        removed = 0
        now = time.time()
        for name in os.listdir(self.base_dir):
            if not name.endswith(".json") or name.endswith(".state.json"):
                continue
            path = os.path.join(self.base_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                expires_at = float(data.get("expires_at", 0))
                if expires_at > now:
                    continue
                sid = self._safe_session_id(data.get("id"))
                if self.revoke_session(sid):
                    removed += 1
            except (OSError, JSONDecodeError, ValueError, KeyError, URLValidationError):
                logger.debug("Skipping auth session during cleanup: %s", path, exc_info=True)
                continue
        return removed

    def revoke_session(self, session_id: str) -> bool:
        sid = self._safe_session_id(session_id)
        removed = False
        for path in (self._meta_path(sid), self._state_path(sid)):
            if os.path.exists(path):
                os.remove(path)
                removed = True
        return removed


auth_session_store = AuthSessionStore(settings.STORAGE_DIR)
