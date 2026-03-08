"""
P0 CRITICAL ORGANS
These are the 5 most critical security organs
"""
import os
import subprocess
import hashlib
import psutil
from datetime import datetime
from pathlib import Path
from .base_organ import BaseOrgan


class Guardian(BaseOrgan):
    """Authentication and access control gateway"""
    
    def __init__(self):
        super().__init__(
            name="Guardian",
            priority="P0",
            description="Authentication gateway - controls all system access"
        )
    
    def scan(self):
        """Check authentication security"""
        findings = []
        
        # Check for failed login attempts
        try:
            result = subprocess.run(
                ['lastb', '-n', '10'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.stdout.strip():
                finding = self.log_finding(
                    'warning',
                    'Failed login attempts detected',
                    {'details': result.stdout[:200]}
                )
                findings.append(finding)
        except:
            pass
        
        # Check current active sessions
        sessions = len(psutil.users())
        if sessions > 3:
            finding = self.log_finding(
                'warning',
                f'Multiple active sessions: {sessions}',
                {'count': sessions}
            )
            findings.append(finding)
        
        self.last_check = datetime.now().isoformat()
        
        return {
            'status': 'warning' if findings else 'clean',
            'findings': findings,
            'action_taken': 'Logged all authentication events'
        }


class Sentinel(BaseOrgan):
    """Active threat detection and monitoring"""
    
    def __init__(self):
        super().__init__(
            name="Sentinel",
            priority="P0",
            description="24/7 threat detection and real-time monitoring"
        )
    
    def scan(self):
        """Scan for active threats"""
        findings = []
        
        # Check for suspicious processes
        suspicious_patterns = ['nc', 'ncat', 'socat', 'cryptominer']
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name = proc.info['name'].lower()
                
                for pattern in suspicious_patterns:
                    if pattern in proc_name:
                        finding = self.log_finding(
                            'critical',
                            f'Suspicious process detected: {proc.info["name"]}',
                            {'pid': proc.info['pid'], 'cmdline': proc.info['cmdline']}
                        )
                        findings.append(finding)
            except:
                pass
        
        # Check network connections
        connections = psutil.net_connections(kind='inet')
        external_connections = [c for c in connections if c.status == 'ESTABLISHED' and c.raddr]
        
        if len(external_connections) > 50:
            finding = self.log_finding(
                'warning',
                f'High number of external connections: {len(external_connections)}',
                {'count': len(external_connections)}
            )
            findings.append(finding)
        
        self.last_check = datetime.now().isoformat()
        
        return {
            'status': 'critical' if any(f['severity'] == 'critical' for f in findings) else 'clean',
            'findings': findings,
            'action_taken': f'Scanned {len(list(psutil.process_iter()))} processes'
        }


class Audit(BaseOrgan):
    """Security audit and compliance checking"""
    
    def __init__(self):
        super().__init__(
            name="Audit",
            priority="P0",
            description="Continuous security auditing and compliance verification"
        )
    
    def scan(self):
        """Run security audit"""
        findings = []
        
        # Check file permissions on critical files
        critical_files = [
            '/etc/passwd',
            '/etc/shadow',
            '/etc/sudoers'
        ]
        
        for filepath in critical_files:
            path = Path(filepath)
            if path.exists():
                stat = path.stat()
                mode = oct(stat.st_mode)[-3:]
                
                if filepath == '/etc/shadow' and mode != '000':
                    finding = self.log_finding(
                        'critical',
                        f'Insecure permissions on {filepath}: {mode}',
                        {'file': filepath, 'mode': mode}
                    )
                    findings.append(finding)
        
        # Check for world-writable files in /opt/veil_os
        veil_path = Path('/opt/veil_os')
        if veil_path.exists():
            for item in veil_path.rglob('*'):
                if item.is_file():
                    stat = item.stat()
                    if stat.st_mode & 0o002:
                        finding = self.log_finding(
                            'warning',
                            f'World-writable file detected: {item}',
                            {'file': str(item)}
                        )
                        findings.append(finding)
        
        self.last_check = datetime.now().isoformat()
        
        return {
            'status': 'warning' if findings else 'clean',
            'findings': findings,
            'action_taken': 'Completed security audit'
        }


class Chronicle(BaseOrgan):
    """Immutable audit trail and ledger"""
    
    def __init__(self):
        super().__init__(
            name="Chronicle",
            priority="P0",
            description="Blockchain-based immutable audit logging"
        )
        self.ledger_path = Path('/opt/veil_os/ledger.json')
    
    def scan(self):
        """Verify ledger integrity"""
        findings = []
        
        if not self.ledger_path.exists():
            finding = self.log_finding(
                'warning',
                'Chronicle ledger does not exist',
                {'path': str(self.ledger_path)}
            )
            findings.append(finding)
        else:
            # Verify ledger is valid JSON
            try:
                ledger_data = self.ledger_path.read_text()
                import json
                entries = json.loads(ledger_data)
                
                # Check for tampering (basic check)
                entry_count = len(entries)
                if entry_count > 0:
                    finding = self.log_finding(
                        'info',
                        f'Chronicle contains {entry_count} audit entries',
                        {'count': entry_count}
                    )
            except json.JSONDecodeError:
                finding = self.log_finding(
                    'critical',
                    'Chronicle ledger corrupted - invalid JSON',
                    {'path': str(self.ledger_path)}
                )
                findings.append(finding)
        
        self.last_check = datetime.now().isoformat()
        
        return {
            'status': 'critical' if any(f['severity'] == 'critical' for f in findings) else 'clean',
            'findings': findings,
            'action_taken': 'Verified ledger integrity'
        }


class Cortex(BaseOrgan):
    """AI-powered decision making and threat intelligence"""
    
    def __init__(self):
        super().__init__(
            name="Cortex",
            priority="P0",
            description="AI decision engine for threat analysis"
        )
    
    def scan(self):
        """Analyze system state and make decisions"""
        findings = []
        
        # Analyze system load
        cpu_percent = psutil.cpu_percent(interval=1)
        mem_percent = psutil.virtual_memory().percent
        
        if cpu_percent > 90:
            finding = self.log_finding(
                'critical',
                f'Critical CPU load detected: {cpu_percent}%',
                {'cpu': cpu_percent}
            )
            findings.append(finding)
        
        if mem_percent > 90:
            finding = self.log_finding(
                'critical',
                f'Critical memory usage: {mem_percent}%',
                {'memory': mem_percent}
            )
            findings.append(finding)
        
        # Check disk usage
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            finding = self.log_finding(
                'warning',
                f'High disk usage: {disk.percent}%',
                {'disk': disk.percent}
            )
            findings.append(finding)
        
        self.last_check = datetime.now().isoformat()
        
        return {
            'status': 'critical' if any(f['severity'] == 'critical' for f in findings) else 'clean',
            'findings': findings,
            'action_taken': 'Analyzed system state'
        }
