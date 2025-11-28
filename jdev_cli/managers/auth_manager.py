"""
Authentication Manager.

SCALE & SUSTAIN Phase 1.1.6 - Auth Manager.

Manages authentication tokens and authorization scopes.

Author: JuanCS Dev
Date: 2025-11-26
"""

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass, field
from enum import Flag, auto
from pathlib import Path
from typing import Any, Dict, List, Optional
import threading


class AuthScope(Flag):
    """Authorization scopes."""
    NONE = 0
    READ = auto()           # Read files
    WRITE = auto()          # Write files
    EXECUTE = auto()        # Execute commands
    NETWORK = auto()        # Network access
    ADMIN = auto()          # Admin operations
    ALL = READ | WRITE | EXECUTE | NETWORK | ADMIN


@dataclass
class AuthToken:
    """Authentication token."""
    token_id: str
    name: str
    scopes: AuthScope
    created_at: float
    expires_at: Optional[float] = None
    last_used: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def has_scope(self, scope: AuthScope) -> bool:
        """Check if token has a specific scope."""
        return bool(self.scopes & scope)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without secret)."""
        return {
            "token_id": self.token_id,
            "name": self.name,
            "scopes": self.scopes.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_used": self.last_used,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthToken':
        """Create from dictionary."""
        return cls(
            token_id=data["token_id"],
            name=data["name"],
            scopes=AuthScope(data.get("scopes", 0)),
            created_at=data["created_at"],
            expires_at=data.get("expires_at"),
            last_used=data.get("last_used"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AuthSession:
    """Authentication session."""
    session_id: str
    token_id: str
    created_at: float
    expires_at: float
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuthenticationManager:
    """
    Manages authentication and authorization.

    Features:
    - Token-based authentication
    - Scope-based authorization
    - Session management
    - Token persistence
    - API key validation

    Example:
        auth = AuthenticationManager()

        # Create token
        token = auth.create_token(
            name="development",
            scopes=AuthScope.READ | AuthScope.WRITE,
            expires_in=86400 * 30  # 30 days
        )

        # Validate token
        is_valid = auth.validate_token(token.token_id)

        # Check authorization
        can_write = auth.authorize(token.token_id, AuthScope.WRITE)
    """

    # Token storage file
    TOKEN_FILE = ".jdev_tokens"

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        secret_key: Optional[str] = None
    ):
        self._storage_path = storage_path or Path.home() / ".jdev"
        self._secret_key = secret_key or self._get_or_create_secret()
        self._tokens: Dict[str, AuthToken] = {}
        self._token_secrets: Dict[str, str] = {}  # token_id -> hashed_secret
        self._sessions: Dict[str, AuthSession] = {}
        self._lock = threading.RLock()

        # Load existing tokens
        self._load_tokens()

    def _get_or_create_secret(self) -> str:
        """Get or create the master secret key."""
        secret_file = self._storage_path / ".secret"
        self._storage_path.mkdir(parents=True, exist_ok=True)

        if secret_file.exists():
            return secret_file.read_text().strip()

        secret = secrets.token_hex(32)
        secret_file.write_text(secret)
        secret_file.chmod(0o600)
        return secret

    def _hash_secret(self, secret: str) -> str:
        """Hash a secret using HMAC-SHA256."""
        return hmac.new(
            self._secret_key.encode(),
            secret.encode(),
            hashlib.sha256
        ).hexdigest()

    def _load_tokens(self) -> None:
        """Load tokens from storage."""
        token_file = self._storage_path / self.TOKEN_FILE

        if not token_file.exists():
            return

        try:
            with open(token_file) as f:
                data = json.load(f)

            for token_data in data.get("tokens", []):
                token = AuthToken.from_dict(token_data)
                self._tokens[token.token_id] = token

            self._token_secrets = data.get("secrets", {})

        except (json.JSONDecodeError, IOError):
            pass

    def _save_tokens(self) -> None:
        """Save tokens to storage."""
        self._storage_path.mkdir(parents=True, exist_ok=True)
        token_file = self._storage_path / self.TOKEN_FILE

        data = {
            "tokens": [t.to_dict() for t in self._tokens.values()],
            "secrets": self._token_secrets,
        }

        with open(token_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Secure permissions
        token_file.chmod(0o600)

    def create_token(
        self,
        name: str,
        scopes: AuthScope = AuthScope.READ,
        expires_in: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[AuthToken, str]:
        """
        Create a new authentication token.

        Args:
            name: Human-readable token name
            scopes: Authorization scopes
            expires_in: Expiration time in seconds (None = never)
            metadata: Additional token metadata

        Returns:
            Tuple of (token, secret) - secret is only returned once!
        """
        with self._lock:
            token_id = secrets.token_urlsafe(16)
            secret = secrets.token_urlsafe(32)

            now = time.time()
            expires_at = now + expires_in if expires_in else None

            token = AuthToken(
                token_id=token_id,
                name=name,
                scopes=scopes,
                created_at=now,
                expires_at=expires_at,
                metadata=metadata or {},
            )

            self._tokens[token_id] = token
            self._token_secrets[token_id] = self._hash_secret(secret)
            self._save_tokens()

            return token, secret

    def validate_token(
        self,
        token_id: str,
        secret: Optional[str] = None
    ) -> bool:
        """
        Validate a token.

        Args:
            token_id: Token ID
            secret: Token secret (for full validation)

        Returns:
            True if token is valid
        """
        with self._lock:
            token = self._tokens.get(token_id)

            if not token:
                return False

            if token.is_expired:
                return False

            if secret:
                hashed = self._hash_secret(secret)
                if not hmac.compare_digest(
                    hashed,
                    self._token_secrets.get(token_id, "")
                ):
                    return False

            # Update last used
            token.last_used = time.time()
            return True

    def authorize(
        self,
        token_id: str,
        required_scope: AuthScope
    ) -> bool:
        """
        Check if token is authorized for a scope.

        Args:
            token_id: Token ID
            required_scope: Required authorization scope

        Returns:
            True if authorized
        """
        with self._lock:
            token = self._tokens.get(token_id)

            if not token:
                return False

            if token.is_expired:
                return False

            return token.has_scope(required_scope)

    def get_token(self, token_id: str) -> Optional[AuthToken]:
        """Get token by ID."""
        return self._tokens.get(token_id)

    def list_tokens(self) -> List[AuthToken]:
        """List all tokens."""
        return list(self._tokens.values())

    def revoke_token(self, token_id: str) -> bool:
        """Revoke a token."""
        with self._lock:
            if token_id in self._tokens:
                del self._tokens[token_id]
                self._token_secrets.pop(token_id, None)
                self._save_tokens()
                return True
            return False

    def update_scopes(
        self,
        token_id: str,
        scopes: AuthScope
    ) -> bool:
        """Update token scopes."""
        with self._lock:
            token = self._tokens.get(token_id)
            if token:
                token.scopes = scopes
                self._save_tokens()
                return True
            return False

    def create_session(
        self,
        token_id: str,
        expires_in: int = 3600,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[AuthSession]:
        """Create an authentication session."""
        if not self.validate_token(token_id):
            return None

        with self._lock:
            session_id = secrets.token_urlsafe(32)
            now = time.time()

            session = AuthSession(
                session_id=session_id,
                token_id=token_id,
                created_at=now,
                expires_at=now + expires_in,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            self._sessions[session_id] = session
            return session

    def validate_session(self, session_id: str) -> bool:
        """Validate a session."""
        session = self._sessions.get(session_id)

        if not session:
            return False

        if time.time() > session.expires_at:
            del self._sessions[session_id]
            return False

        return self.validate_token(session.token_id)

    def end_session(self, session_id: str) -> bool:
        """End a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Clean up expired tokens and sessions."""
        cleaned = 0
        now = time.time()

        with self._lock:
            # Expired tokens
            expired_tokens = [
                tid for tid, t in self._tokens.items()
                if t.is_expired
            ]
            for tid in expired_tokens:
                del self._tokens[tid]
                self._token_secrets.pop(tid, None)
                cleaned += 1

            # Expired sessions
            expired_sessions = [
                sid for sid, s in self._sessions.items()
                if now > s.expires_at
            ]
            for sid in expired_sessions:
                del self._sessions[sid]
                cleaned += 1

            if expired_tokens:
                self._save_tokens()

        return cleaned

    def validate_api_key(self, api_key: str) -> Optional[AuthToken]:
        """
        Validate an API key in format: token_id:secret

        Args:
            api_key: API key string

        Returns:
            Token if valid, None otherwise
        """
        try:
            token_id, secret = api_key.split(":", 1)
        except ValueError:
            return None

        if self.validate_token(token_id, secret):
            return self._tokens.get(token_id)

        return None


__all__ = [
    'AuthenticationManager',
    'AuthToken',
    'AuthScope',
    'AuthSession',
]
