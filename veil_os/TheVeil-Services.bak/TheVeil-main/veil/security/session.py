"""
Session Manager - The Veil Session Management
=============================================
P1 Security Organ: "Every session has its time and purpose."

Provides:
- Secure session creation and management
- Session expiration and cleanup
- Activity tracking
- Concurrent session limits
"""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

from .models import Session, Role


class SessionConfig:
    """Session configuration."""
    # Session Settings
    SESSION_DURATION_MINUTES: int = 60
    EXTENDED_SESSION_DAYS: int = 7  # For "remember me"
    MAX_CONCURRENT_SESSIONS: int = 5
    ACTIVITY_TIMEOUT_MINUTES: int = 30
    
    # Cookie Settings
    COOKIE_NAME: str = "veil_session"
    COOKIE_SECURE: bool = True
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "Lax"
    
    # Storage
    DATA_DIR: Path = Path("/var/lib/veil/security")
    SESSIONS_FILE: Path = DATA_DIR / "sessions.json"


class SessionManager:
    """
    Manages user sessions for The Veil.
    
    Sessions are stored server-side with only a session ID
    sent to the client as a secure cookie.
    """
    
    def __init__(self, config: SessionConfig = None):
        self.config = config or SessionConfig()
        self._sessions: Dict[str, Session] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self._init_storage()
        self._load_sessions()
    
    def _init_storage(self):
        """Initialize storage."""
        self.config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.config.SESSIONS_FILE.exists():
            self._save_sessions()
    
    def _load_sessions(self):
        """Load sessions from storage."""
        try:
            if self.config.SESSIONS_FILE.exists():
                data = json.loads(self.config.SESSIONS_FILE.read_text())
                for session_data in data.get("sessions", []):
                    session = Session.from_dict(session_data)
                    # Skip expired sessions
                    if not session.is_expired() and session.is_valid:
                        self._sessions[session.id] = session
                        # Build user_sessions index
                        if session.user_id not in self._user_sessions:
                            self._user_sessions[session.user_id] = []
                        self._user_sessions[session.user_id].append(session.id)
        except Exception:
            self._sessions = {}
            self._user_sessions = {}
    
    def _save_sessions(self):
        """Save sessions to storage."""
        data = {
            "version": "1.0",
            "updated_at": datetime.utcnow().isoformat(),
            "sessions": [s.to_dict() for s in self._sessions.values()]
        }
        
        tmp_file = self.config.SESSIONS_FILE.with_suffix('.tmp')
        tmp_file.write_text(json.dumps(data, indent=2))
        tmp_file.rename(self.config.SESSIONS_FILE)
        self.config.SESSIONS_FILE.chmod(0o600)
    
    def _cleanup_expired(self):
        """Remove expired sessions."""
        expired = [
            sid for sid, session in self._sessions.items()
            if session.is_expired() or not session.is_valid
        ]
        
        for sid in expired:
            session = self._sessions.pop(sid, None)
            if session and session.user_id in self._user_sessions:
                self._user_sessions[session.user_id] = [
                    s for s in self._user_sessions[session.user_id] if s != sid
                ]
        
        if expired:
            self._save_sessions()
    
    def _enforce_session_limit(self, user_id: str):
        """Enforce maximum concurrent sessions per user."""
        user_session_ids = self._user_sessions.get(user_id, [])
        
        if len(user_session_ids) >= self.config.MAX_CONCURRENT_SESSIONS:
            # Remove oldest session
            oldest_id = user_session_ids[0]
            self.invalidate(oldest_id)
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def create(
        self,
        user_id: str,
        username: str,
        role: Role,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        remember_me: bool = False
    ) -> Session:
        """
        Create a new session for a user.
        Returns the session with a unique ID.
        """
        self._cleanup_expired()
        self._enforce_session_limit(user_id)
        
        now = datetime.utcnow()
        
        if remember_me:
            expires_at = now + timedelta(days=self.config.EXTENDED_SESSION_DAYS)
        else:
            expires_at = now + timedelta(minutes=self.config.SESSION_DURATION_MINUTES)
        
        session = Session(
            id=secrets.token_urlsafe(32),
            user_id=user_id,
            username=username,
            role=role,
            created_at=now,
            expires_at=expires_at,
            last_activity=now,
            ip_address=ip_address,
            user_agent=user_agent,
            is_valid=True
        )
        
        self._sessions[session.id] = session
        
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session.id)
        
        self._save_sessions()
        
        return session
    
    def get(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        self._cleanup_expired()
        
        session = self._sessions.get(session_id)
        
        if session and not session.is_expired() and session.is_valid:
            return session
        
        return None
    
    def validate(self, session_id: str) -> Optional[Session]:
        """
        Validate a session and update last activity.
        Returns the session if valid, None otherwise.
        """
        session = self.get(session_id)
        
        if not session:
            return None
        
        # Check activity timeout
        activity_timeout = datetime.utcnow() - timedelta(
            minutes=self.config.ACTIVITY_TIMEOUT_MINUTES
        )
        
        if session.last_activity < activity_timeout:
            self.invalidate(session_id)
            return None
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        self._save_sessions()
        
        return session
    
    def invalidate(self, session_id: str) -> bool:
        """Invalidate (logout) a session."""
        session = self._sessions.get(session_id)
        
        if not session:
            return False
        
        session.is_valid = False
        
        # Remove from storage
        del self._sessions[session_id]
        
        if session.user_id in self._user_sessions:
            self._user_sessions[session.user_id] = [
                s for s in self._user_sessions[session.user_id] if s != session_id
            ]
        
        self._save_sessions()
        
        return True
    
    def invalidate_all_for_user(self, user_id: str) -> int:
        """Invalidate all sessions for a user. Returns count."""
        session_ids = self._user_sessions.get(user_id, []).copy()
        count = 0
        
        for sid in session_ids:
            if self.invalidate(sid):
                count += 1
        
        return count
    
    def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user."""
        self._cleanup_expired()
        
        session_ids = self._user_sessions.get(user_id, [])
        return [
            self._sessions[sid]
            for sid in session_ids
            if sid in self._sessions and self._sessions[sid].is_valid
        ]
    
    def get_all_sessions(self) -> List[Session]:
        """Get all active sessions (admin only)."""
        self._cleanup_expired()
        return [s for s in self._sessions.values() if s.is_valid]
    
    def extend_session(self, session_id: str, minutes: int = None) -> Optional[Session]:
        """Extend a session's expiration time."""
        session = self.get(session_id)
        
        if not session:
            return None
        
        if minutes is None:
            minutes = self.config.SESSION_DURATION_MINUTES
        
        session.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        self._save_sessions()
        
        return session
    
    def get_cookie_settings(self) -> Dict[str, Any]:
        """Get cookie settings for session cookies."""
        return {
            "key": self.config.COOKIE_NAME,
            "secure": self.config.COOKIE_SECURE,
            "httponly": self.config.COOKIE_HTTPONLY,
            "samesite": self.config.COOKIE_SAMESITE,
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the SessionManager singleton instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
