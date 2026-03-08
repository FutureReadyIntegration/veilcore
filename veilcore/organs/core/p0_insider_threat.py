"""
INSIDER THREAT DETECTION AND RESPONSE
Original Concept: Marlon Ástin Williams - VoC Project
Detects and stops internal attacks from trusted users
Monitors: privilege abuse, data exfiltration, unauthorized access, physical tampering
"""
import subprocess
import psutil
import os
from pathlib import Path
from datetime import datetime, timedelta
from .base_organ import BaseOrgan


class InsiderThreat(BaseOrgan):
    def __init__(self):
        super().__init__("Insider Threat", "P0", "Internal attack detection and mitigation")
        self.quarantine_dir = Path('/opt/veil_os/insider_quarantine')
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.suspicious_users = {}
        self.data_exfil_attempts = []
        self.privilege_abuse_log = []
    
    def scan(self):
        findings = []
        
        # INSIDER THREAT 1: Detect privilege escalation attempts
        priv_escalation = self._detect_privilege_escalation()
        if priv_escalation:
            for attempt in priv_escalation:
                findings.append(self.log_finding('critical',
                    f'PRIVILEGE ESCALATION DETECTED: {attempt}'))
        
        # INSIDER THREAT 2: Detect unauthorized file access
        unauthorized_access = self._detect_unauthorized_file_access()
        if unauthorized_access:
            for access in unauthorized_access:
                findings.append(self.log_finding('critical',
                    f'UNAUTHORIZED FILE ACCESS: {access}'))
        
        # INSIDER THREAT 3: Detect data exfiltration attempts
        exfil_attempts = self._detect_data_exfiltration()
        if exfil_attempts:
            for exfil in exfil_attempts:
                findings.append(self.log_finding('critical',
                    f'DATA EXFILTRATION ATTEMPT: {exfil}'))
        
        # INSIDER THREAT 4: Detect USB/removable media insertion
        usb_threats = self._detect_usb_insertion()
        if usb_threats:
            for usb in usb_threats:
                findings.append(self.log_finding('warning',
                    f'UNAUTHORIZED USB DEVICE: {usb}'))
        
        # INSIDER THREAT 5: Detect security tool tampering
        tampering = self._detect_security_tampering()
        if tampering:
            for tamper in tampering:
                findings.append(self.log_finding('critical',
                    f'SECURITY TAMPERING DETECTED: {tamper}'))
        
        # INSIDER THREAT 6: Detect after-hours suspicious activity
        after_hours = self._detect_after_hours_activity()
        if after_hours:
            for activity in after_hours:
                findings.append(self.log_finding('warning',
                    f'SUSPICIOUS AFTER-HOURS ACTIVITY: {activity}'))
        
        self.last_check = datetime.now().isoformat()
        
        status = 'critical' if any(f['severity'] == 'critical' for f in findings) else 'clean'
        return {
            'status': status,
            'findings': findings,
            'action_taken': f'Monitored for insider threats - {len(findings)} alerts'
        }
    
    def _detect_privilege_escalation(self):
        """Detect sudo/su attempts and privilege changes"""
        attempts = []
        
        # Check recent sudo attempts
        try:
            result = subprocess.run(['grep', 'sudo', '/var/log/auth.log'],
                                  capture_output=True, text=True, timeout=2)
            
            # Look for failed sudo in last 100 lines
            recent = result.stdout.split('\n')[-100:]
            for line in recent:
                if 'incorrect password' in line.lower() or 'not in sudoers' in line.lower():
                    user = self._extract_username(line)
                    if user:
                        attempts.append(f'User {user} attempted sudo escalation')
        except:
            pass
        
        # Check for setuid bit changes (privilege persistence)
        try:
            find_cmd = ['find', '/tmp', '/var/tmp', '-perm', '-4000', '-type', 'f']
            result = subprocess.run(find_cmd, capture_output=True, text=True, timeout=5)
            if result.stdout.strip():
                attempts.append(f'SETUID binaries found in temp: {len(result.stdout.splitlines())}')
        except:
            pass
        
        return attempts[:5]
    
    def _detect_unauthorized_file_access(self):
        """Detect access to sensitive files by unauthorized users"""
        violations = []
        
        # Check for unauthorized access to sensitive directories
        sensitive_paths = [
            '/etc/shadow',
            '/etc/passwd',
            '/opt/veil_os/vault',
            '/var/log',
            '/root'
        ]
        
        # Look for unusual file access patterns
        try:
            # Check recent file access in sensitive areas
            result = subprocess.run(['find', '/etc', '-type', 'f', '-amin', '-5'],
                                  capture_output=True, text=True, timeout=3)
            recent_access = result.stdout.strip().split('\n')
            
            for filepath in recent_access:
                if filepath and any(sens in filepath for sens in ['/shadow', '/passwd', '/sudoers']):
                    violations.append(f'Recent access to {filepath}')
        except:
            pass
        
        return violations[:5]
    
    def _detect_data_exfiltration(self):
        """Detect large data transfers or suspicious file copying"""
        exfil = []
        
        # Check for large file copies to external locations
        try:
            # Look for large files in /tmp or user directories
            result = subprocess.run(['find', '/tmp', '-type', 'f', '-size', '+10M'],
                                  capture_output=True, text=True, timeout=3)
            
            large_files = result.stdout.strip().split('\n')
            for filepath in large_files:
                if filepath:
                    exfil.append(f'Large file in temp: {filepath}')
        except:
            pass
        
        # Check for database dumps
        try:
            result = subprocess.run(['find', '/tmp', '-name', '*.sql', '-o', '-name', '*.db'],
                                  capture_output=True, text=True, timeout=3)
            if result.stdout.strip():
                exfil.append('Database dump files detected in temp')
        except:
            pass
        
        return exfil[:5]
    
    def _detect_usb_insertion(self):
        """Detect USB or removable media insertion"""
        usb_devices = []
        
        try:
            # Check for newly mounted removable devices
            with open('/proc/mounts', 'r') as f:
                mounts = f.readlines()
            
            for mount in mounts:
                if '/media' in mount or '/mnt' in mount:
                    # Potential USB or external drive
                    device = mount.split()[0]
                    if 'sd' in device:  # USB devices typically show as sda, sdb, etc
                        usb_devices.append(f'Removable device mounted: {device}')
        except:
            pass
        
        return usb_devices[:3]
    
    def _detect_security_tampering(self):
        """Detect attempts to disable security tools"""
        tampering = []
        
        # Check if critical security services were stopped
        critical_services = ['auditd', 'fail2ban', 'veil-dashboard']
        
        for service in critical_services:
            try:
                result = subprocess.run(['systemctl', 'is-active', service],
                                      capture_output=True, text=True, timeout=2)
                if 'inactive' in result.stdout or 'failed' in result.stdout:
                    tampering.append(f'Critical service {service} is not running')
            except:
                pass
        
        # Check for deleted or modified security logs
        try:
            veil_logs = Path('/opt/veil_os/logs')
            if veil_logs.exists():
                # Check if any log files were recently deleted (check inode count)
                pass  # Would need baseline to compare
        except:
            pass
        
        return tampering[:5]
    
    def _detect_after_hours_activity(self):
        """Detect suspicious activity outside business hours"""
        suspicious = []
        
        # Check current time
        now = datetime.now()
        hour = now.hour
        
        # Business hours: 7 AM - 7 PM
        if hour < 7 or hour > 19:
            # Check for active user sessions
            try:
                users = psutil.users()
                if len(users) > 0:
                    for user in users:
                        suspicious.append(f'User {user.name} active at {now.strftime("%I:%M %p")}')
            except:
                pass
        
        return suspicious[:3]
    
    def _extract_username(self, log_line):
        """Extract username from log line"""
        try:
            parts = log_line.split()
            for i, part in enumerate(parts):
                if part == 'user' and i + 1 < len(parts):
                    return parts[i + 1]
        except:
            pass
        return None
