import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.p0_organs import Guardian, Sentinel, Audit, Chronicle, Cortex
from core.p1_organs import Watchdog, Firewall, Backup, Quarantine, Vault, MFA, RBAC, HostSensor, NetworkMonitor, ThreatIntel
from core.p2_healthcare import PHIGuard, EpicConnector, ImprivataBridge, HL7Filter, FHIRGateway, DICOMShield, IoMTProtector
from core.p2_security_ops import Canary, Scanner, Patcher, Encryptor, DLPEngine, BehavioralAnalysis, AnomalyDetector
from core.p2_network import VPNManager, CertificateAuthority, KeyManager, SessionMonitor, ComplianceEngine, RiskAnalyzer, ForensicCollector, IncidentResponder, MalwareDetector, RansomwareShield, ZeroTrustEngine, Microsegmentation
from core.p2_api_web import APIGateway, LoadBalancer, WAF, IDSIPS
from core.p2_monitoring import SIEMConnector, LogAggregator, MetricsCollector, AlertManager, NotificationEngine, EmailGateway, SMSNotifier, WebhookHandler
from core.p2_dns_proxy import DNSFilter, WebProxy, ContentFilter, SSLInspector, TrafficShaper, BandwidthMonitor
from core.p2_scanning import PortScanner, VulnerabilityScanner, PatchManager, ConfigAuditor, BaselineMonitor, IntegrityChecker
from core.p2_system import FileMonitor, RegistryWatcher, ProcessMonitor, ServiceGuardian, ResourceLimiter, PerformanceMonitor, HealthChecker, UptimeTracker
from core.p2_recovery import DisasterRecovery, SnapshotManager, ReplicationEngine, FailoverController, BackupValidator
from core.p0_insider_threat import InsiderThreat
from core.p2_phi_classifier import PHIClassifier, EncryptionEnforcer, ComplianceTracker

class OrganOrchestrator:
    def __init__(self):
        self.organs = [
            # P0 - Critical (8) - ADDED InsiderThreat!
            Guardian(), Sentinel(), Audit(), Chronicle(), Cortex(),
            InsiderThreat(),
            PHIClassifier(), EncryptionEnforcer(),

            # P1 - High Priority (10)
            Watchdog(), Firewall(), Backup(), Quarantine(), Vault(),
            MFA(), RBAC(), HostSensor(), NetworkMonitor(), ThreatIntel(),

            # P2 - Healthcare (7)
            PHIGuard(), EpicConnector(), ImprivataBridge(), HL7Filter(),
            FHIRGateway(), DICOMShield(), IoMTProtector(),

            # P2 - Security Operations (7)
            Canary(), Scanner(), Patcher(), Encryptor(), DLPEngine(),
            BehavioralAnalysis(), AnomalyDetector(),

            # P2 - Network & Infrastructure (12)
            VPNManager(), CertificateAuthority(), KeyManager(), SessionMonitor(),
            ComplianceEngine(), RiskAnalyzer(), ForensicCollector(), IncidentResponder(),
            MalwareDetector(), RansomwareShield(), ZeroTrustEngine(), Microsegmentation(),

            # P2 - API & Web (4)
            APIGateway(), LoadBalancer(), WAF(), IDSIPS(),

            # P2 - Monitoring (8)
            SIEMConnector(), LogAggregator(), MetricsCollector(), AlertManager(),
            NotificationEngine(), EmailGateway(), SMSNotifier(), WebhookHandler(),

            # P2 - DNS & Proxy (6)
            DNSFilter(), WebProxy(), ContentFilter(), SSLInspector(),
            TrafficShaper(), BandwidthMonitor(),

            # P2 - Scanning (6)
            PortScanner(), VulnerabilityScanner(), PatchManager(), ConfigAuditor(),
            BaselineMonitor(), IntegrityChecker(),

            # P2 - System (8)
            FileMonitor(), RegistryWatcher(), ProcessMonitor(), ServiceGuardian(),
            ResourceLimiter(), PerformanceMonitor(), HealthChecker(), UptimeTracker(),

            # P2 - Recovery (5)
            DisasterRecovery(), SnapshotManager(), ReplicationEngine(),
            FailoverController(), BackupValidator(),
            
            # P2 - Compliance (1)
            ComplianceTracker()
        ]

        for organ in self.organs:
            organ.start()

        print(f"Orchestrator initialized: {len(self.organs)} organs loaded")

    def run_full_scan(self):
        all_findings = []
        critical_count = 0
        warning_count = 0

        for organ in self.organs:
            try:
                result = organ.scan()
                if result['findings']:
                    for finding in result['findings']:
                        all_findings.append(finding)
                        if finding['severity'] == 'critical':
                            critical_count += 1
                        elif finding['severity'] == 'warning':
                            warning_count += 1
            except Exception as e:
                print(f"Error scanning {organ.name}: {e}")

        return {
            'timestamp': datetime.now().isoformat(),
            'organs_scanned': len(self.organs),
            'critical': critical_count,
            'warnings': warning_count,
            'findings': all_findings
        }

    def get_organ_status(self):
        return [organ.get_status() for organ in self.organs]


# Create fresh instance every time this function is called
def get_orchestrator():
    return OrganOrchestrator()

# For backward compatibility - but API should use get_orchestrator()
orchestrator = get_orchestrator()
