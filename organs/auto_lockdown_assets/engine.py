"""
Veil Auto-Lockdown Organ
========================
P0 Security Organ: "When threats emerge, I respond without hesitation."

Automated threat response system:
- Graduated response levels (warn → restrict → lockdown)
- Automatic account suspension
- Network isolation triggers
- Incident recording and recovery
- Integration with Guardian, RBAC, and Alert systems

This organ executes defensive actions automatically when threats are detected.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
import threading


# ============================================================================
# Configuration
# ============================================================================

class LockdownConfig:
    """Configuration for auto-lockdown system."""
    # Response thresholds
    WARN_THRESHOLD: int = 30
    RESTRICT_THRESHOLD: int = 50
    SUSPEND_THRESHOLD: int = 70
    LOCKDOWN_THRESHOLD: int = 90
    
    # Timing
    WARNING_DURATION_MINUTES: int = 30
    RESTRICTION_DURATION_MINUTES: int = 60
    SUSPENSION_DURATION_HOURS: int = 4
    LOCKDOWN_REVIEW_HOURS: int = 24
    
    # Auto-escalation
    ESCALATION_WINDOW_MINUTES: int = 15
    MAX_WARNINGS_BEFORE_ESCALATION: int = 3
    
    # Storage
    DATA_DIR: Path = Path("/var/lib/veil/lockdown")


# ============================================================================
# Data Models  
# ============================================================================

class ResponseLevel(str, Enum):
    """Graduated response levels."""
    NONE = "none"               # No action
    MONITOR = "monitor"         # Increased monitoring
    WARN = "warn"               # Warning to user/admin
    RESTRICT = "restrict"       # Reduced privileges
    SUSPEND = "suspend"         # Account suspension
    LOCKDOWN = "lockdown"       # Full system lockdown
    QUARANTINE = "quarantine"   # Network isolation


class ActionType(str, Enum):
    """Types of automated actions."""
    LOG_EVENT = "log_event"
    SEND_ALERT = "send_alert"
    WARN_USER = "warn_user"
    WARN_ADMIN = "warn_admin"
    REDUCE_PRIVILEGES = "reduce_privileges"
    FORCE_LOGOUT = "force_logout"
    SUSPEND_ACCOUNT = "suspend_account"
    BLOCK_IP = "block_ip"
    ISOLATE_DEVICE = "isolate_device"
    TRIGGER_BACKUP = "trigger_backup"
    SYSTEM_LOCKDOWN = "system_lockdown"


@dataclass
class ThreatEvent:
    """A detected threat event."""
    id: str
    timestamp: datetime
    source: str  # Which organ detected it
    threat_type: str
    severity: int  # 0-100
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResponseAction:
    """An automated response action."""
    id: str
    timestamp: datetime
    action_type: ActionType
    target_type: str  # user, ip, device, system
    target_id: str
    trigger_event_id: str
    executed: bool = False
    success: bool = False
    result_message: str = ""
    rollback_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type.value,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "trigger_event_id": self.trigger_event_id,
            "executed": self.executed,
            "success": self.success,
            "result_message": self.result_message,
            "rollback_at": self.rollback_at.isoformat() if self.rollback_at else None,
        }


@dataclass
class LockdownState:
    """Current lockdown state for a target."""
    target_type: str
    target_id: str
    level: ResponseLevel
    activated_at: datetime
    expires_at: Optional[datetime]
    trigger_event_ids: List[str] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)
    
    def is_active(self) -> bool:
        if self.level == ResponseLevel.NONE:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


# ============================================================================
# Response Engine
# ============================================================================

class AutoLockdown:
    """
    Automated Threat Response Engine.
    
    Implements graduated response to security threats with automatic
    escalation and recovery.
    """
    
    def __init__(self, data_dir: Path = None):
        self.config = LockdownConfig()
        self.data_dir = data_dir or self.config.DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # State tracking
        self._lockdown_states: Dict[str, LockdownState] = {}  # target_key -> state
        self._pending_actions: List[ResponseAction] = []
        self._action_history: List[ResponseAction] = []
        self._event_history: List[ThreatEvent] = []
        self._warning_counts: Dict[str, int] = {}  # target_key -> warning count
        
        # Action handlers (to be registered by other organs)
        self._action_handlers: Dict[ActionType, Callable] = {}
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Register default handlers
        self._register_default_handlers()
        self._load_state()
    
    def _register_default_handlers(self):
        """Register default action handlers."""
        self._action_handlers[ActionType.LOG_EVENT] = self._handle_log_event
        self._action_handlers[ActionType.SEND_ALERT] = self._handle_send_alert
        self._action_handlers[ActionType.WARN_USER] = self._handle_warn_user
        self._action_handlers[ActionType.WARN_ADMIN] = self._handle_warn_admin
    
    def _load_state(self):
        """Load persisted state."""
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for key, state_data in data.get("lockdown_states", {}).items():
                    self._lockdown_states[key] = LockdownState(
                        target_type=state_data["target_type"],
                        target_id=state_data["target_id"],
                        level=ResponseLevel(state_data["level"]),
                        activated_at=datetime.fromisoformat(state_data["activated_at"]),
                        expires_at=datetime.fromisoformat(state_data["expires_at"]) if state_data.get("expires_at") else None,
                        trigger_event_ids=state_data.get("trigger_event_ids", []),
                        actions_taken=state_data.get("actions_taken", []),
                    )
            except Exception:
                pass
    
    def _save_state(self):
        """Save state to disk."""
        state_file = self.data_dir / "state.json"
        data = {
            "lockdown_states": {},
            "last_updated": datetime.utcnow().isoformat(),
        }
        for key, state in self._lockdown_states.items():
            data["lockdown_states"][key] = {
                "target_type": state.target_type,
                "target_id": state.target_id,
                "level": state.level.value,
                "activated_at": state.activated_at.isoformat(),
                "expires_at": state.expires_at.isoformat() if state.expires_at else None,
                "trigger_event_ids": state.trigger_event_ids,
                "actions_taken": state.actions_taken,
            }
        state_file.write_text(json.dumps(data, indent=2))
    
    def register_handler(self, action_type: ActionType, handler: Callable):
        """Register a handler for an action type."""
        self._action_handlers[action_type] = handler
    
    def process_threat(self, event: ThreatEvent) -> List[ResponseAction]:
        """
        Process a threat event and determine appropriate response.
        
        Returns list of actions taken.
        """
        with self._lock:
            self._event_history.append(event)
            
            # Determine response level based on severity
            response_level = self._determine_response_level(event)
            
            # Check for escalation
            target_key = self._get_target_key(event)
            current_state = self._lockdown_states.get(target_key)
            
            if current_state and current_state.is_active():
                # Check for escalation
                response_level = self._check_escalation(event, current_state, response_level)
            
            # Generate and execute response actions
            actions = self._generate_actions(event, response_level)
            executed_actions = []
            
            for action in actions:
                result = self._execute_action(action)
                executed_actions.append(result)
            
            # Update lockdown state
            self._update_lockdown_state(event, response_level, executed_actions)
            self._save_state()
            
            return executed_actions
    
    def _determine_response_level(self, event: ThreatEvent) -> ResponseLevel:
        """Determine response level based on threat severity."""
        severity = event.severity
        
        if severity >= self.config.LOCKDOWN_THRESHOLD:
            return ResponseLevel.LOCKDOWN
        elif severity >= self.config.SUSPEND_THRESHOLD:
            return ResponseLevel.SUSPEND
        elif severity >= self.config.RESTRICT_THRESHOLD:
            return ResponseLevel.RESTRICT
        elif severity >= self.config.WARN_THRESHOLD:
            return ResponseLevel.WARN
        else:
            return ResponseLevel.MONITOR
    
    def _check_escalation(
        self, 
        event: ThreatEvent, 
        current_state: LockdownState,
        proposed_level: ResponseLevel
    ) -> ResponseLevel:
        """Check if response should be escalated."""
        target_key = self._get_target_key(event)
        
        # Count warnings in escalation window
        cutoff = datetime.utcnow() - timedelta(minutes=self.config.ESCALATION_WINDOW_MINUTES)
        recent_events = [
            e for e in self._event_history
            if self._get_target_key(e) == target_key and e.timestamp > cutoff
        ]
        
        # Escalate if too many warnings
        warning_count = self._warning_counts.get(target_key, 0)
        if warning_count >= self.config.MAX_WARNINGS_BEFORE_ESCALATION:
            levels = list(ResponseLevel)
            current_idx = levels.index(proposed_level)
            if current_idx < len(levels) - 1:
                return levels[current_idx + 1]
        
        # Escalate if multiple events
        if len(recent_events) >= 3:
            levels = list(ResponseLevel)
            current_idx = levels.index(proposed_level)
            if current_idx < len(levels) - 1:
                return levels[current_idx + 1]
        
        # Don't de-escalate
        if current_state:
            levels = list(ResponseLevel)
            current_idx = levels.index(current_state.level)
            proposed_idx = levels.index(proposed_level)
            if proposed_idx < current_idx:
                return current_state.level
        
        return proposed_level
    
    def _generate_actions(self, event: ThreatEvent, level: ResponseLevel) -> List[ResponseAction]:
        """Generate response actions for a threat."""
        actions = []
        action_id_base = f"ACT-{int(time.time() * 1000)}"
        
        # Always log
        actions.append(ResponseAction(
            id=f"{action_id_base}-LOG",
            timestamp=datetime.utcnow(),
            action_type=ActionType.LOG_EVENT,
            target_type="system",
            target_id="audit",
            trigger_event_id=event.id,
        ))
        
        if level == ResponseLevel.MONITOR:
            # Increased monitoring only
            pass
        
        elif level == ResponseLevel.WARN:
            # Warning actions
            if event.user_id:
                actions.append(ResponseAction(
                    id=f"{action_id_base}-WARN-USER",
                    timestamp=datetime.utcnow(),
                    action_type=ActionType.WARN_USER,
                    target_type="user",
                    target_id=event.user_id,
                    trigger_event_id=event.id,
                    rollback_at=datetime.utcnow() + timedelta(minutes=self.config.WARNING_DURATION_MINUTES),
                ))
            
            actions.append(ResponseAction(
                id=f"{action_id_base}-WARN-ADMIN",
                timestamp=datetime.utcnow(),
                action_type=ActionType.WARN_ADMIN,
                target_type="system",
                target_id="admin",
                trigger_event_id=event.id,
            ))
        
        elif level == ResponseLevel.RESTRICT:
            # Reduce privileges
            if event.user_id:
                actions.append(ResponseAction(
                    id=f"{action_id_base}-RESTRICT",
                    timestamp=datetime.utcnow(),
                    action_type=ActionType.REDUCE_PRIVILEGES,
                    target_type="user",
                    target_id=event.user_id,
                    trigger_event_id=event.id,
                    rollback_at=datetime.utcnow() + timedelta(minutes=self.config.RESTRICTION_DURATION_MINUTES),
                ))
            
            actions.append(ResponseAction(
                id=f"{action_id_base}-ALERT",
                timestamp=datetime.utcnow(),
                action_type=ActionType.SEND_ALERT,
                target_type="system",
                target_id="security_team",
                trigger_event_id=event.id,
            ))
        
        elif level == ResponseLevel.SUSPEND:
            # Account suspension
            if event.user_id:
                actions.append(ResponseAction(
                    id=f"{action_id_base}-LOGOUT",
                    timestamp=datetime.utcnow(),
                    action_type=ActionType.FORCE_LOGOUT,
                    target_type="user",
                    target_id=event.user_id,
                    trigger_event_id=event.id,
                ))
                
                actions.append(ResponseAction(
                    id=f"{action_id_base}-SUSPEND",
                    timestamp=datetime.utcnow(),
                    action_type=ActionType.SUSPEND_ACCOUNT,
                    target_type="user",
                    target_id=event.user_id,
                    trigger_event_id=event.id,
                    rollback_at=datetime.utcnow() + timedelta(hours=self.config.SUSPENSION_DURATION_HOURS),
                ))
            
            if event.ip_address:
                actions.append(ResponseAction(
                    id=f"{action_id_base}-BLOCK-IP",
                    timestamp=datetime.utcnow(),
                    action_type=ActionType.BLOCK_IP,
                    target_type="ip",
                    target_id=event.ip_address,
                    trigger_event_id=event.id,
                    rollback_at=datetime.utcnow() + timedelta(hours=self.config.SUSPENSION_DURATION_HOURS),
                ))
        
        elif level in (ResponseLevel.LOCKDOWN, ResponseLevel.QUARANTINE):
            # Full lockdown
            actions.append(ResponseAction(
                id=f"{action_id_base}-BACKUP",
                timestamp=datetime.utcnow(),
                action_type=ActionType.TRIGGER_BACKUP,
                target_type="system",
                target_id="all",
                trigger_event_id=event.id,
            ))
            
            if event.device_id:
                actions.append(ResponseAction(
                    id=f"{action_id_base}-ISOLATE",
                    timestamp=datetime.utcnow(),
                    action_type=ActionType.ISOLATE_DEVICE,
                    target_type="device",
                    target_id=event.device_id,
                    trigger_event_id=event.id,
                ))
            
            if level == ResponseLevel.LOCKDOWN:
                actions.append(ResponseAction(
                    id=f"{action_id_base}-LOCKDOWN",
                    timestamp=datetime.utcnow(),
                    action_type=ActionType.SYSTEM_LOCKDOWN,
                    target_type="system",
                    target_id="all",
                    trigger_event_id=event.id,
                ))
        
        return actions
    
    def _execute_action(self, action: ResponseAction) -> ResponseAction:
        """Execute a response action."""
        handler = self._action_handlers.get(action.action_type)
        
        if handler:
            try:
                success, message = handler(action)
                action.executed = True
                action.success = success
                action.result_message = message
            except Exception as e:
                action.executed = True
                action.success = False
                action.result_message = f"Error: {str(e)}"
        else:
            action.executed = False
            action.success = False
            action.result_message = f"No handler for {action.action_type.value}"
        
        self._action_history.append(action)
        return action
    
    def _update_lockdown_state(
        self, 
        event: ThreatEvent, 
        level: ResponseLevel,
        actions: List[ResponseAction]
    ):
        """Update lockdown state for the target."""
        target_key = self._get_target_key(event)
        
        # Calculate expiration
        if level == ResponseLevel.WARN:
            expires = datetime.utcnow() + timedelta(minutes=self.config.WARNING_DURATION_MINUTES)
        elif level == ResponseLevel.RESTRICT:
            expires = datetime.utcnow() + timedelta(minutes=self.config.RESTRICTION_DURATION_MINUTES)
        elif level == ResponseLevel.SUSPEND:
            expires = datetime.utcnow() + timedelta(hours=self.config.SUSPENSION_DURATION_HOURS)
        elif level in (ResponseLevel.LOCKDOWN, ResponseLevel.QUARANTINE):
            expires = datetime.utcnow() + timedelta(hours=self.config.LOCKDOWN_REVIEW_HOURS)
        else:
            expires = None
        
        # Update or create state
        if target_key in self._lockdown_states:
            state = self._lockdown_states[target_key]
            state.level = level
            state.expires_at = expires
            state.trigger_event_ids.append(event.id)
            state.actions_taken.extend([a.id for a in actions])
        else:
            self._lockdown_states[target_key] = LockdownState(
                target_type=event.user_id and "user" or event.ip_address and "ip" or "system",
                target_id=event.user_id or event.ip_address or "system",
                level=level,
                activated_at=datetime.utcnow(),
                expires_at=expires,
                trigger_event_ids=[event.id],
                actions_taken=[a.id for a in actions],
            )
        
        # Update warning count
        if level == ResponseLevel.WARN:
            self._warning_counts[target_key] = self._warning_counts.get(target_key, 0) + 1
    
    def _get_target_key(self, event: ThreatEvent) -> str:
        """Get unique key for target identification."""
        if event.user_id:
            return f"user:{event.user_id}"
        elif event.device_id:
            return f"device:{event.device_id}"
        elif event.ip_address:
            return f"ip:{event.ip_address}"
        return "system:global"
    
    # Default action handlers
    def _handle_log_event(self, action: ResponseAction) -> Tuple[bool, str]:
        """Log the event to audit."""
        # In production, this would call the audit organ
        return True, f"Event logged: {action.trigger_event_id}"
    
    def _handle_send_alert(self, action: ResponseAction) -> Tuple[bool, str]:
        """Send alert to security team."""
        # In production, this would send email/SMS/webhook
        return True, f"Alert sent to {action.target_id}"
    
    def _handle_warn_user(self, action: ResponseAction) -> Tuple[bool, str]:
        """Warn the user."""
        # In production, this would display warning in UI
        return True, f"Warning displayed to user {action.target_id}"
    
    def _handle_warn_admin(self, action: ResponseAction) -> Tuple[bool, str]:
        """Warn administrators."""
        # In production, this would notify admins
        return True, "Administrator notified"
    
    # Public methods for manual control
    def manual_lockdown(self, target_type: str, target_id: str, level: ResponseLevel, reason: str) -> LockdownState:
        """Manually trigger a lockdown."""
        with self._lock:
            event = ThreatEvent(
                id=f"MANUAL-{int(time.time() * 1000)}",
                timestamp=datetime.utcnow(),
                source="manual",
                threat_type="manual_lockdown",
                severity=90 if level == ResponseLevel.LOCKDOWN else 50,
                user_id=target_id if target_type == "user" else None,
                ip_address=target_id if target_type == "ip" else None,
                device_id=target_id if target_type == "device" else None,
                details={"reason": reason},
            )
            
            self.process_threat(event)
            
            target_key = f"{target_type}:{target_id}"
            return self._lockdown_states.get(target_key)
    
    def lift_lockdown(self, target_type: str, target_id: str, reason: str) -> bool:
        """Manually lift a lockdown."""
        with self._lock:
            target_key = f"{target_type}:{target_id}"
            if target_key in self._lockdown_states:
                state = self._lockdown_states[target_key]
                state.level = ResponseLevel.NONE
                state.expires_at = datetime.utcnow()
                
                # Log the lift
                self._event_history.append(ThreatEvent(
                    id=f"LIFT-{int(time.time() * 1000)}",
                    timestamp=datetime.utcnow(),
                    source="manual",
                    threat_type="lockdown_lifted",
                    severity=0,
                    details={"reason": reason, "previous_level": state.level.value},
                ))
                
                self._save_state()
                return True
            return False
    
    def get_lockdown_state(self, target_type: str, target_id: str) -> Optional[LockdownState]:
        """Get current lockdown state for a target."""
        target_key = f"{target_type}:{target_id}"
        state = self._lockdown_states.get(target_key)
        if state and state.is_active():
            return state
        return None
    
    def get_active_lockdowns(self) -> List[LockdownState]:
        """Get all active lockdowns."""
        return [s for s in self._lockdown_states.values() if s.is_active()]
    
    def get_action_history(self, limit: int = 100) -> List[ResponseAction]:
        """Get recent action history."""
        return sorted(self._action_history, key=lambda a: a.timestamp, reverse=True)[:limit]
    
    def cleanup_expired(self):
        """Clean up expired lockdowns."""
        with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, state in self._lockdown_states.items()
                if state.expires_at and state.expires_at < now
            ]
            
            for key in expired_keys:
                state = self._lockdown_states[key]
                state.level = ResponseLevel.NONE
            
            # Reset warning counts for expired lockdowns
            for key in expired_keys:
                self._warning_counts.pop(key, None)
            
            self._save_state()
            return len(expired_keys)


# Singleton instance
_auto_lockdown: Optional[AutoLockdown] = None

def get_auto_lockdown() -> AutoLockdown:
    """Get the singleton AutoLockdown instance."""
    global _auto_lockdown
    if _auto_lockdown is None:
        _auto_lockdown = AutoLockdown()
    return _auto_lockdown


# Organ metadata
ORGAN_METADATA = {
    "name": "auto_lockdown",
    "tier": "P0",
    "glyph": "🔒",
    "description": "Automated Threat Response - When threats emerge, I respond",
    "affirmation": "When threats emerge, I respond without hesitation.",
    "dependencies": ["guardian", "audit", "sentinel", "insider_threat"],
    "provides": ["automated_response", "graduated_lockdown", "threat_mitigation"],
}
