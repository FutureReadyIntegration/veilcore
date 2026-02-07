"""
BASE ORGAN CLASS
All 78 security organs inherit from this
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional
import json
from pathlib import Path


class BaseOrgan(ABC):
    """Base class for all Veil OS security organs"""

    def __init__(self, name: str, priority: str, description: str):
        self.name = name
        self.priority = priority
        self.description = description
        self.status = "stopped"
        self.last_check = None
        self.findings = []

    @abstractmethod
    def scan(self) -> Dict:
        """
        Each organ implements its own scan logic
        Returns: {
            'status': 'clean' | 'warning' | 'critical',
            'findings': [...],
            'action_taken': '...'
        }
        """
        pass

    def start(self):
        """Start the organ"""
        self.status = "running"
        self.findings = []  # Clear findings on start

    def stop(self):
        """Stop the organ"""
        self.status = "stopped"

    def clear_findings(self):
        """Clear accumulated findings"""
        self.findings = []

    def log_finding(self, severity: str, message: str, details: Dict = None):
        """Log a security finding"""
        finding = {
            'timestamp': datetime.now().isoformat(),
            'organ': self.name,
            'severity': severity,
            'message': message,
            'details': details or {}
        }
        # DON'T accumulate - just return it
        # self.findings.append(finding)  # REMOVED - was causing stale findings

        # Write to organ-specific log
        log_file = Path(f"/opt/veil_os/logs/{self.name.lower().replace(' ', '_')}.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with log_file.open('a') as f:
            f.write(json.dumps(finding) + '\n')

        return finding

    def get_status(self) -> Dict:
        """Get current organ status"""
        return {
            'name': self.name,
            'priority': self.priority,
            'status': self.status,
            'description': self.description,
            'last_check': self.last_check,
            'findings_count': 0  # Always 0 since we don't accumulate anymore
        }
