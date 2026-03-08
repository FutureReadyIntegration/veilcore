"""
Audit Log - The Veil Audit Logging System
=========================================
P1 Security Organ: "I witness all that passes through The Veil."

Provides:
- Tamper-proof audit logging with hash chains
- Structured event logging
- Query and search capabilities
- Compliance-ready audit trail
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator
from threading import Lock
import gzip

from .models import AuditEvent, AuditLevel, User, Session


class AuditConfig:
    """Audit configuration."""
    # Storage
    DATA_DIR: Path = Path("/var/lib/veil/audit")
    LOG_FILE: Path = DATA_DIR / "audit.log"
    
    # Rotation
    MAX_LOG_SIZE_MB: int = 100
    MAX_LOG_FILES: int = 90  # Keep 90 days
    COMPRESS_OLD_LOGS: bool = True
    
    # Integrity
    ENABLE_HASH_CHAIN: bool = True
    HASH_ALGORITHM: str = "sha256"


class AuditLog:
    """
    Tamper-proof audit logging for The Veil.
    
    Features:
    - Hash chain for tamper detection
    - Atomic writes
    - Log rotation and compression
    - Structured JSON logging
    """
    
    def __init__(self, config: AuditConfig = None):
        self.config = config or AuditConfig()
        self._lock = Lock()
        self._last_hash: Optional[str] = None
        self._event_count: int = 0
        self._init_storage()
    
    def _init_storage(self):
        """Initialize audit storage."""
        self.config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load last hash from existing log
        if self.config.LOG_FILE.exists():
            try:
                with open(self.config.LOG_FILE, 'r') as f:
                    for line in f:
                        pass  # Read to last line
                    if line:
                        event = json.loads(line)
                        self._last_hash = event.get("_hash")
                        self._event_count = event.get("_seq", 0)
            except Exception:
                pass
    
    def _compute_hash(self, event_data: Dict[str, Any]) -> str:
        """Compute hash for an event, chained to previous hash."""
        # Create hashable string (excluding hash field)
        data = {k: v for k, v in event_data.items() if not k.startswith('_')}
        data["_prev_hash"] = self._last_hash or "GENESIS"
        data["_seq"] = self._event_count
        
        hash_input = json.dumps(data, sort_keys=True).encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()
    
    def _rotate_if_needed(self):
        """Rotate log file if it exceeds max size."""
        if not self.config.LOG_FILE.exists():
            return
        
        size_mb = self.config.LOG_FILE.stat().st_size / (1024 * 1024)
        if size_mb < self.config.MAX_LOG_SIZE_MB:
            return
        
        # Rotate
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        rotated = self.config.DATA_DIR / f"audit_{timestamp}.log"
        
        self.config.LOG_FILE.rename(rotated)
        
        # Compress if enabled
        if self.config.COMPRESS_OLD_LOGS:
            with open(rotated, 'rb') as f_in:
                with gzip.open(str(rotated) + '.gz', 'wb') as f_out:
                    f_out.writelines(f_in)
            rotated.unlink()
        
        # Clean up old logs
        self._cleanup_old_logs()
    
    def _cleanup_old_logs(self):
        """Remove logs older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.config.MAX_LOG_FILES)
        
        for log_file in self.config.DATA_DIR.glob("audit_*.log*"):
            try:
                # Extract timestamp from filename
                name = log_file.stem.replace('.log', '')
                parts = name.split('_')
                if len(parts) >= 2:
                    date_str = parts[1]
                    log_date = datetime.strptime(date_str, "%Y%m%d")
                    if log_date < cutoff:
                        log_file.unlink()
            except Exception:
                continue
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    def log(
        self,
        level: AuditLevel,
        category: str,
        action: str,
        user: Optional[User] = None,
        session: Optional[Session] = None,
        ip_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Args:
            level: Severity level
            category: Event category (auth, patient, organ, system, security)
            action: Action performed (login, logout, create, update, etc.)
            user: User who performed the action
            session: Session context
            ip_address: Client IP address
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional event details
            success: Whether the action succeeded
            error_message: Error message if failed
        
        Returns:
            The logged AuditEvent
        """
        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            level=level,
            category=category,
            action=action,
            user_id=user.id if user else (session.user_id if session else None),
            username=user.username if user else (session.username if session else None),
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            success=success,
            error_message=error_message
        )
        
        self._write_event(event)
        return event
    
    def _write_event(self, event: AuditEvent):
        """Write event to log file with hash chain."""
        with self._lock:
            self._rotate_if_needed()
            
            event_data = event.to_dict()
            
            # Add hash chain if enabled
            if self.config.ENABLE_HASH_CHAIN:
                self._event_count += 1
                event_data["_seq"] = self._event_count
                event_data["_prev_hash"] = self._last_hash or "GENESIS"
                event_data["_hash"] = self._compute_hash(event_data)
                self._last_hash = event_data["_hash"]
            
            # Atomic write
            with open(self.config.LOG_FILE, 'a') as f:
                f.write(json.dumps(event_data) + '\n')
    
    # ========================================================================
    # Convenience Methods
    # ========================================================================
    
    def auth_login(
        self,
        username: str,
        ip_address: str,
        success: bool,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log a login attempt."""
        self.log(
            level=AuditLevel.SECURITY if success else AuditLevel.WARNING,
            category="auth",
            action="login",
            ip_address=ip_address,
            details={"username": username, **(details or {})},
            success=success,
            error_message=error_message
        )
    
    def auth_logout(
        self,
        user: User = None,
        session: Session = None,
        ip_address: str = None
    ):
        """Log a logout."""
        self.log(
            level=AuditLevel.INFO,
            category="auth",
            action="logout",
            user=user,
            session=session,
            ip_address=ip_address,
            success=True
        )
    
    def patient_action(
        self,
        action: str,
        patient_id: str,
        user: User = None,
        session: Session = None,
        ip_address: str = None,
        details: Dict[str, Any] = None,
        success: bool = True,
        error_message: str = None
    ):
        """Log a patient-related action."""
        self.log(
            level=AuditLevel.INFO if success else AuditLevel.WARNING,
            category="patient",
            action=action,
            user=user,
            session=session,
            ip_address=ip_address,
            resource_type="patient",
            resource_id=patient_id,
            details=details,
            success=success,
            error_message=error_message
        )
    
    def organ_action(
        self,
        action: str,
        organ_name: str,
        user: User = None,
        session: Session = None,
        ip_address: str = None,
        details: Dict[str, Any] = None,
        success: bool = True,
        error_message: str = None
    ):
        """Log an organ-related action."""
        self.log(
            level=AuditLevel.SECURITY,
            category="organ",
            action=action,
            user=user,
            session=session,
            ip_address=ip_address,
            resource_type="organ",
            resource_id=organ_name,
            details=details,
            success=success,
            error_message=error_message
        )
    
    def system_action(
        self,
        action: str,
        user: User = None,
        session: Session = None,
        ip_address: str = None,
        details: Dict[str, Any] = None,
        success: bool = True,
        error_message: str = None
    ):
        """Log a system-level action."""
        self.log(
            level=AuditLevel.CRITICAL if "restart" in action else AuditLevel.WARNING,
            category="system",
            action=action,
            user=user,
            session=session,
            ip_address=ip_address,
            details=details,
            success=success,
            error_message=error_message
        )
    
    def security_event(
        self,
        action: str,
        ip_address: str = None,
        details: Dict[str, Any] = None,
        success: bool = True,
        error_message: str = None
    ):
        """Log a security event (failed auth, lockout, etc.)."""
        self.log(
            level=AuditLevel.SECURITY,
            category="security",
            action=action,
            ip_address=ip_address,
            details=details,
            success=success,
            error_message=error_message
        )
    
    # ========================================================================
    # Query Methods
    # ========================================================================
    
    def query(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        level: AuditLevel = None,
        category: str = None,
        action: str = None,
        username: str = None,
        resource_type: str = None,
        resource_id: str = None,
        success: bool = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Query audit events with filters.
        """
        events = []
        
        for event in self._read_events():
            # Apply filters
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            if level and event.level != level:
                continue
            if category and event.category != category:
                continue
            if action and event.action != action:
                continue
            if username and event.username != username:
                continue
            if resource_type and event.resource_type != resource_type:
                continue
            if resource_id and event.resource_id != resource_id:
                continue
            if success is not None and event.success != success:
                continue
            
            events.append(event)
            
            if len(events) >= limit:
                break
        
        return events
    
    def _read_events(self) -> Generator[AuditEvent, None, None]:
        """Read events from log file (newest first)."""
        if not self.config.LOG_FILE.exists():
            return
        
        # Read all lines and reverse for newest first
        with open(self.config.LOG_FILE, 'r') as f:
            lines = f.readlines()
        
        for line in reversed(lines):
            try:
                data = json.loads(line.strip())
                yield AuditEvent.from_dict(data)
            except Exception:
                continue
    
    def get_recent(self, count: int = 50) -> List[AuditEvent]:
        """Get the most recent events."""
        return self.query(limit=count)
    
    def get_failed_logins(
        self,
        since: datetime = None,
        ip_address: str = None
    ) -> List[AuditEvent]:
        """Get failed login attempts."""
        if since is None:
            since = datetime.utcnow() - timedelta(hours=24)
        
        events = self.query(
            start_time=since,
            category="auth",
            action="login",
            success=False,
            limit=1000
        )
        
        if ip_address:
            events = [e for e in events if e.ip_address == ip_address]
        
        return events
    
    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the audit log using hash chain.
        Returns verification results.
        """
        if not self.config.ENABLE_HASH_CHAIN:
            return {"verified": False, "error": "Hash chain not enabled"}
        
        if not self.config.LOG_FILE.exists():
            return {"verified": True, "events": 0, "message": "No log file"}
        
        prev_hash = "GENESIS"
        count = 0
        errors = []
        
        with open(self.config.LOG_FILE, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    data = json.loads(line.strip())
                    
                    # Check sequence
                    expected_seq = count + 1
                    if data.get("_seq") != expected_seq:
                        errors.append(f"Line {line_num}: Sequence mismatch")
                    
                    # Check previous hash
                    if data.get("_prev_hash") != prev_hash:
                        errors.append(f"Line {line_num}: Hash chain broken")
                    
                    # Verify hash
                    stored_hash = data.get("_hash")
                    computed_data = {k: v for k, v in data.items() if not k.startswith('_')}
                    computed_data["_prev_hash"] = prev_hash
                    computed_data["_seq"] = expected_seq
                    hash_input = json.dumps(computed_data, sort_keys=True).encode('utf-8')
                    computed_hash = hashlib.sha256(hash_input).hexdigest()
                    
                    if stored_hash != computed_hash:
                        errors.append(f"Line {line_num}: Hash mismatch (tampered?)")
                    
                    prev_hash = stored_hash
                    count += 1
                    
                except Exception as e:
                    errors.append(f"Line {line_num}: Parse error - {str(e)}")
        
        return {
            "verified": len(errors) == 0,
            "events": count,
            "errors": errors,
            "message": "Integrity verified" if not errors else f"{len(errors)} integrity errors found"
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_audit_log: Optional[AuditLog] = None


def get_audit_log() -> AuditLog:
    """Get the AuditLog singleton instance."""
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog()
    return _audit_log
