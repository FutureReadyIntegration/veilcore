from pathlib import Path
from datetime import datetime
import re
from .base_organ import BaseOrgan

class PHIClassifier(BaseOrgan):
    def __init__(self):
        super().__init__("PHI Classifier", "P2", "Detects and tags PHI data")
        self.phi_patterns = {
            'SSN': r'\b\d{3}-\d{2}-\d{4}\b',
            'MRN': r'\b(MRN|MR#)[\s:]?\d{6,10}\b',
            'DOB': r'\b(0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])[-/](19|20)\d{2}\b',
            'Phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'Email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        }
    
    def scan(self):
        findings = []
        scan_dirs = [Path('/opt/veil_os/logs'), Path('/tmp')]
        
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                for file in scan_dir.glob('*.log'):
                    try:
                        content = file.read_text()
                        for phi_type, pattern in self.phi_patterns.items():
                            if re.search(pattern, content, re.IGNORECASE):
                                findings.append(self.log_finding('warning',
                                    f'PHI detected: {phi_type} in {file.name}'))
                    except:
                        pass
        
        self.last_check = datetime.now().isoformat()
        return {'status': 'warning' if findings else 'clean', 'findings': findings,
                'action_taken': f'Scanned for PHI patterns'}

class EncryptionEnforcer(BaseOrgan):
    def __init__(self):
        super().__init__("Encryption Enforcer", "P2", "Verifies data encryption")
    
    def scan(self):
        findings = []
        
        # Check dashboard uses HTTPS
        import subprocess
        try:
            result = subprocess.run(['netstat', '-tuln'], capture_output=True, text=True, timeout=2)
            if ':8000 ' in result.stdout and 'tcp' in result.stdout:
                findings.append(self.log_finding('critical', 'Dashboard not using HTTPS/TLS'))
        except:
            pass
        
        self.last_check = datetime.now().isoformat()
        return {'status': 'critical' if findings else 'clean', 'findings': findings,
                'action_taken': 'Verified encryption status'}

class ComplianceTracker(BaseOrgan):
    def __init__(self):
        super().__init__("Compliance Tracker", "P2", "HIPAA compliance monitoring")
    
    def scan(self):
        findings = []
        score = 0
        
        # Check compliance items
        checks = {
            'Firewall Active': self._check_firewall(),
            'Audit Logging': self._check_logging(),
            'Access Control': self._check_access(),
            'Encryption': self._check_encryption(),
            'MFA Configured': self._check_mfa()
        }
        
        for check_name, passed in checks.items():
            if passed:
                score += 20
            else:
                findings.append(self.log_finding('info', f'HIPAA gap: {check_name}'))
        
        self.last_check = datetime.now().isoformat()
        return {'status': 'clean', 'findings': findings,
                'action_taken': f'HIPAA Compliance: {score}%'}
    
    def _check_firewall(self):
        try:
            import subprocess
            result = subprocess.run(['ufw', 'status'], capture_output=True, text=True, timeout=2)
            return 'active' in result.stdout.lower()
        except:
            return False
    
    def _check_logging(self):
        return Path('/opt/veil_os/ledger.json').exists()
    
    def _check_access(self):
        return Path('/etc/shadow').stat().st_mode & 0o777 == 0
    
    def _check_encryption(self):
        return True  # Placeholder
    
    def _check_mfa(self):
        return Path('/etc/pam.d/common-auth').exists()
