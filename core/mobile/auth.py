"""
VeilCore Mobile Authentication
================================
API key management, rate limiting, and session control.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("veilcore.mobile.auth")

KEYS_PATH = "/var/lib/veilcore/mobile/api_keys.json"


@dataclass
class APIToken:
    """API token for mobile access."""
    key: str
    operator: str
    role: str = "viewer"    # viewer, operator, admin
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used: Optional[str] = None
    request_count: int = 0
    enabled: bool = True
    ip_allowlist: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_prefix": self.key[:8] + "...",
            "operator": self.operator,
            "role": self.role,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "request_count": self.request_count,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> APIToken:
        valid = cls.__dataclass_fields__
        return cls(**{k: v for k, v in data.items() if k in valid})


class AuthManager:
    """
    Manages API authentication for the Mobile API.

    Usage:
        auth = AuthManager()
        token = auth.create_key("Dr. Smith", role="operator")
        assert auth.validate_key(token.key)
    """

    def __init__(self, keys_path: Optional[str] = None):
        self._path = keys_path or KEYS_PATH
        self._tokens: dict[str, APIToken] = {}
        self._rate_limits: dict[str, list[float]] = defaultdict(list)
        self._rate_window = 60.0       # seconds
        self._rate_max = 120           # requests per window
        self._load()

        # Ensure at least one admin key exists
        if not self._tokens:
            self._create_default_key()

    def create_key(self, operator: str, role: str = "viewer",
                   ip_allowlist: Optional[list[str]] = None) -> APIToken:
        """Create a new API key."""
        key = "vc_" + secrets.token_hex(24)
        token = APIToken(
            key=key, operator=operator, role=role,
            ip_allowlist=ip_allowlist or [],
        )
        key_hash = self._hash_key(key)
        self._tokens[key_hash] = token
        self._save()
        logger.info(f"Created API key for '{operator}' (role: {role})")
        return token

    def revoke_key(self, key: str) -> bool:
        """Revoke an API key."""
        key_hash = self._hash_key(key)
        if key_hash in self._tokens:
            token = self._tokens[key_hash]
            token.enabled = False
            self._save()
            logger.info(f"Revoked API key for '{token.operator}'")
            return True
        return False

    def validate_key(self, key: str) -> bool:
        """Validate an API key."""
        if not key:
            return False

        # Support both hashed lookup and direct match
        key_hash = self._hash_key(key)
        token = self._tokens.get(key_hash)

        # Also check direct key match (for dev/test)
        if not token:
            for t in self._tokens.values():
                if t.key == key:
                    token = t
                    break

        if not token or not token.enabled:
            return False

        token.last_used = datetime.now(timezone.utc).isoformat()
        token.request_count += 1
        return True

    def get_operator(self, key: str) -> str:
        """Get operator name for a key."""
        key_hash = self._hash_key(key)
        token = self._tokens.get(key_hash)
        if not token:
            for t in self._tokens.values():
                if t.key == key:
                    return t.operator
        return token.operator if token else "unknown"

    def get_role(self, key: str) -> str:
        """Get role for a key."""
        key_hash = self._hash_key(key)
        token = self._tokens.get(key_hash)
        if not token:
            for t in self._tokens.values():
                if t.key == key:
                    return t.role
        return token.role if token else "viewer"

    def check_rate_limit(self, key: str) -> bool:
        """Check if key is within rate limits."""
        now = time.monotonic()
        requests = self._rate_limits[key]
        # Prune old entries
        self._rate_limits[key] = [t for t in requests if now - t < self._rate_window]
        if len(self._rate_limits[key]) >= self._rate_max:
            return False
        self._rate_limits[key].append(now)
        return True

    def list_keys(self) -> list[dict[str, Any]]:
        """List all API keys (redacted)."""
        return [t.to_dict() for t in self._tokens.values()]

    def _hash_key(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def _create_default_key(self) -> None:
        """Create a default admin key for initial setup."""
        token = self.create_key("veilcore-admin", role="admin")
        logger.info(f"Default admin API key created: {token.key}")
        # Also save the plaintext key for initial setup
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path + ".initial", "w") as f:
                f.write(token.key)
            os.chmod(self._path + ".initial", 0o600)
        except Exception:
            pass

    def _save(self) -> None:
        """Persist keys to disk."""
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            data = {}
            for key_hash, token in self._tokens.items():
                data[key_hash] = {
                    "key": token.key,
                    "operator": token.operator,
                    "role": token.role,
                    "created_at": token.created_at,
                    "last_used": token.last_used,
                    "request_count": token.request_count,
                    "enabled": token.enabled,
                    "ip_allowlist": token.ip_allowlist,
                }
            with open(self._path, "w") as f:
                json.dump(data, f, indent=2)
            os.chmod(self._path, 0o600)
        except Exception as e:
            logger.error(f"Failed to save keys: {e}")

    def _load(self) -> None:
        """Load keys from disk."""
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path) as f:
                data = json.load(f)
            for key_hash, tdata in data.items():
                self._tokens[key_hash] = APIToken.from_dict(tdata)
            logger.info(f"Loaded {len(self._tokens)} API keys")
        except Exception as e:
            logger.warning(f"Failed to load keys: {e}")
