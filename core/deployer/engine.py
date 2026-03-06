"""
VeilCore Deployment Engine — Genesis
"""
from __future__ import annotations
import json, logging, os, platform, shutil, subprocess, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.deployer.engine")

class DeployPhase(str, Enum):
    PREFLIGHT="preflight"; DEPENDENCIES="dependencies"; CORE="core"
    ORGANS_P0="organs_p0"; ORGANS_P1="organs_p1"; ORGANS_P2="organs_p2"
    SUBSYSTEMS="subsystems"; SERVICES="services"; DASHBOARD="dashboard"
    VERIFICATION="verification"; COMPLETE="complete"; FAILED="failed"; ROLLBACK="rollback"

class DeployMode(str, Enum):
    FRESH="fresh"; UPGRADE="upgrade"; REPAIR="repair"; SUBSYSTEMS_ONLY="subsystems_only"

@dataclass
class SystemRequirements:
    min_python: tuple = (3, 10)
    min_ram_gb: float = 4.0
    min_disk_gb: float = 10.0
    supported_os: list[str] = field(default_factory=lambda: ["Ubuntu 24.04","Ubuntu 22.04","Ubuntu 20.04"])
    required_packages: list[str] = field(default_factory=lambda: ["python3","python3-pip","python3-venv","systemd","openssl","curl","jq"])
    python_packages: list[str] = field(default_factory=lambda: ["fastapi","uvicorn","aiohttp","pyyaml","numpy","scikit-learn","cryptography"])

@dataclass
class PreflightResult:
    passed: bool = True; os_name: str = ""; os_version: str = ""; python_version: str = ""
    ram_gb: float = 0.0; disk_gb: float = 0.0
    errors: list[str] = field(default_factory=list); warnings: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]:
        return {"passed":self.passed,"os":f"{self.os_name} {self.os_version}","python":self.python_version,"ram_gb":self.ram_gb,"disk_gb":round(self.disk_gb,1),"errors":self.errors,"warnings":self.warnings,"checks":self.checks}

@dataclass
class DeploymentManifest:
    mode: str = "fresh"; hospital_name: str = ""; install_path: str = "/opt/veilcore"
    data_path: str = "/var/lib/veilcore"; log_path: str = "/var/log/veilcore"
    config_path: str = "/etc/veilcore"; dashboard_port: int = 8443; enable_ssl: bool = True
    enable_federation: bool = False; federation_peers: list[str] = field(default_factory=list)
    enable_mobile_api: bool = True; mobile_api_port: int = 8444
    organ_tiers: list[str] = field(default_factory=lambda: ["P0","P1","P2"])
    subsystems: list[str] = field(default_factory=lambda: ["mesh","ml","federation","pentest","mobile","accessibility","wireless","physical"])
    def to_dict(self) -> dict[str, Any]:
        return {"mode":self.mode,"hospital_name":self.hospital_name,"install_path":self.install_path,"data_path":self.data_path,"log_path":self.log_path,"config_path":self.config_path,"dashboard_port":self.dashboard_port,"enable_ssl":self.enable_ssl,"enable_federation":self.enable_federation,"enable_mobile_api":self.enable_mobile_api,"organ_tiers":self.organ_tiers,"subsystems":self.subsystems}

@dataclass
class DeploymentResult:
    deploy_id: str = field(default_factory=lambda: f"DEPLOY-{int(time.time())}")
    success: bool = False; mode: str = "fresh"; phase: str = "preflight"
    phases_completed: list[str] = field(default_factory=list)
    organs_deployed: int = 0; subsystems_deployed: int = 0
    services_created: int = 0; services_started: int = 0
    errors: list[str] = field(default_factory=list); warnings: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rollback_performed: bool = False
    def to_dict(self) -> dict[str, Any]:
        return {"deploy_id":self.deploy_id,"success":self.success,"mode":self.mode,"phase":self.phase,"phases_completed":self.phases_completed,"organs_deployed":self.organs_deployed,"subsystems_deployed":self.subsystems_deployed,"services_created":self.services_created,"services_started":self.services_started,"errors":self.errors,"warnings":self.warnings,"duration_seconds":round(self.duration_seconds,2),"timestamp":self.timestamp,"rollback_performed":self.rollback_performed}

P0_ORGANS = ["guardian","sentinel","cortex","audit","chronicle","insider_threat","phi_classifier","encryption_enforcer","watchdog","firewall","backup","quarantine","vault","mfa"]
P1_ORGANS = ["rbac","host_sensor","network_monitor","threat_intel","phi_guard","epic_connector","imprivata_bridge","hl7_filter","fhir_gateway","dicom_shield","iomt_protector","canary","scanner","patcher"]
P2_ORGANS = ["encryptor","dlp_engine","behavioral_analysis","anomaly_detector","vpn_manager","certificate_authority","key_manager","session_monitor","compliance_engine","risk_analyzer","forensic_collector","incident_responder","malware_detector","ransomware_shield","zero_trust_engine","micro_segmentation","api_gateway","load_balancer","waf","ids_ips","siem_connector","log_aggregator","metrics_collector","alert_manager","notification_engine","email_gateway","sms_notifier","webhook_handler","dns_filter","web_proxy","content_filter","ssl_inspector","traffic_shaper","bandwidth_monitor","port_scanner","vulnerability_scanner","patch_manager","config_auditor","baseline_monitor","integrity_checker","file_monitor","registry_watcher","process_monitor","service_guardian","resource_limiter","performance_monitor","health_checker","uptime_tracker","disaster_recovery","snapshot_manager","replication_engine","failover_controller","backup_validator","compliance_tracker"]

SUBSYSTEM_MAP = {
    "mesh":{"name":"NerveBridge","path":"core/mesh","priority":1},
    "ml":{"name":"DeepSentinel","path":"core/ml","priority":2},
    "federation":{"name":"AllianceNet","path":"core/federation","priority":3},
    "pentest":{"name":"RedVeil","path":"core/pentest","priority":4},
    "mobile":{"name":"Watchtower","path":"core/mobile","priority":5},
    "accessibility":{"name":"EqualShield","path":"core/accessibility","priority":6},
    "wireless":{"name":"AirShield","path":"core/wireless","priority":7},
    "physical":{"name":"IronWatch","path":"core/physical","priority":8},
}

SYSTEMD_TEMPLATE = """[Unit]
Description=VeilCore {organ_display} ({tier})
After=network.target
Wants=veilcore-orchestrator.service
[Service]
Type=simple
User=veilcore
Group=veilcore
WorkingDirectory={install_path}
ExecStart=/usr/bin/python3 {install_path}/organs/{tier_dir}/{organ_name}.py
Restart=always
RestartSec={restart_sec}
StandardOutput=journal
StandardError=journal
SyslogIdentifier=veilcore-{organ_name}
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths={data_path} {log_path}
PrivateTmp=yes
[Install]
WantedBy=multi-user.target
"""

class DeploymentEngine:
    def __init__(self):
        self._requirements = SystemRequirements()
        self._deploy_log: list[str] = []
        self._backup_path = "/var/lib/veilcore/deploy-backups"

    def preflight_check(self) -> PreflightResult:
        result = PreflightResult()
        result.os_name = platform.system()
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        result.os_version = line.split("=")[1].strip().strip('"'); break
        except Exception:
            result.os_version = platform.version()
        is_ubuntu = "ubuntu" in result.os_version.lower()
        result.checks["os_compatible"] = is_ubuntu
        if not is_ubuntu: result.warnings.append(f"Non-Ubuntu OS: {result.os_version}")
        py_ver = platform.python_version_tuple()
        result.python_version = platform.python_version()
        py_ok = (int(py_ver[0]),int(py_ver[1])) >= self._requirements.min_python
        result.checks["python_version"] = py_ok
        if not py_ok: result.errors.append(f"Python {result.python_version} too old"); result.passed = False
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        result.ram_gb = round(int(line.split()[1])/1024/1024, 1); break
        except Exception: result.ram_gb = 0
        result.checks["ram_sufficient"] = result.ram_gb >= self._requirements.min_ram_gb
        try:
            stat = os.statvfs("/")
            result.disk_gb = (stat.f_bavail * stat.f_frsize)/(1024**3)
        except Exception: result.disk_gb = 0
        result.checks["disk_sufficient"] = result.disk_gb >= self._requirements.min_disk_gb
        if not result.checks["disk_sufficient"]: result.errors.append(f"Disk {result.disk_gb:.1f}GB < {self._requirements.min_disk_gb}GB"); result.passed = False
        result.checks["root_access"] = os.geteuid() == 0
        result.checks["systemd_available"] = os.path.exists("/run/systemd/system")
        if result.errors: result.passed = False
        return result

    def deploy(self, manifest: DeploymentManifest) -> DeploymentResult:
        start = time.monotonic()
        result = DeploymentResult(mode=manifest.mode)
        try:
            result.phase = DeployPhase.PREFLIGHT
            preflight = self.preflight_check()
            if not preflight.passed and any("Disk" in e for e in preflight.errors):
                result.errors.extend(preflight.errors); result.phase = DeployPhase.FAILED; return result
            result.phases_completed.append(DeployPhase.PREFLIGHT)
            self._log(f"Preflight: {preflight.python_version}, {preflight.ram_gb}GB RAM")
            result.phase = DeployPhase.CORE
            self._create_directories(manifest)
            result.phases_completed.append(DeployPhase.CORE)
            for tier, organs, phase in [("p0_critical",P0_ORGANS,DeployPhase.ORGANS_P0),("p1_important",P1_ORGANS,DeployPhase.ORGANS_P1),("p2_standard",P2_ORGANS,DeployPhase.ORGANS_P2)]:
                result.phase = phase
                count = self._deploy_organ_tier(tier, organs, manifest)
                result.organs_deployed += count
                result.phases_completed.append(phase)
            result.phase = DeployPhase.SUBSYSTEMS
            for sub_key in manifest.subsystems:
                if sub_key in SUBSYSTEM_MAP:
                    self._deploy_subsystem(sub_key, manifest); result.subsystems_deployed += 1
            result.phases_completed.append(DeployPhase.SUBSYSTEMS)
            result.phase = DeployPhase.SERVICES
            result.services_created = self._generate_services(manifest)
            result.phases_completed.append(DeployPhase.SERVICES)
            result.phase = DeployPhase.DASHBOARD
            os.makedirs(f"{manifest.install_path}/dashboard", exist_ok=True)
            result.phases_completed.append(DeployPhase.DASHBOARD)
            result.phase = DeployPhase.VERIFICATION
            result.services_started = self._verify_deployment(manifest)
            result.phases_completed.append(DeployPhase.VERIFICATION)
            result.phase = DeployPhase.COMPLETE; result.success = True
            result.phases_completed.append(DeployPhase.COMPLETE)
            self._save_manifest(manifest, result)
        except Exception as e:
            result.phase = DeployPhase.FAILED; result.errors.append(str(e)); result.success = False
        result.duration_seconds = time.monotonic() - start
        return result

    def _create_directories(self, manifest):
        for d in [manifest.install_path,f"{manifest.install_path}/organs/p0_critical",f"{manifest.install_path}/organs/p1_important",f"{manifest.install_path}/organs/p2_standard",f"{manifest.install_path}/core",f"{manifest.install_path}/dashboard",f"{manifest.install_path}/scripts",f"{manifest.install_path}/specs",f"{manifest.install_path}/services",manifest.data_path,f"{manifest.data_path}/mesh",f"{manifest.data_path}/ml",f"{manifest.data_path}/federation",f"{manifest.data_path}/wireless",f"{manifest.data_path}/physical",f"{manifest.data_path}/accessibility",f"{manifest.data_path}/deploy-backups",manifest.log_path,manifest.config_path]:
            os.makedirs(d, exist_ok=True)

    def _deploy_organ_tier(self, tier, organs, manifest):
        tier_dir = f"{manifest.install_path}/organs/{tier}"
        os.makedirs(tier_dir, exist_ok=True)
        count = 0
        for organ in organs:
            organ_file = f"{tier_dir}/{organ}.py"
            if not os.path.exists(organ_file):
                self._create_organ_stub(organ, tier, organ_file)
            count += 1
        return count

    def _create_organ_stub(self, organ, tier, path):
        display = organ.replace("_"," ").title()
        cls = organ.title().replace("_","")
        t = tier.split("_")[0].upper()
        content = f'#!/usr/bin/env python3\n"""VeilCore Organ: {display} — Tier: {tier}"""\nimport logging,time,signal,sys\nlogger=logging.getLogger("veilcore.organ.{organ}")\nclass {cls}Organ:\n    def __init__(self): self.name="{organ}";self.tier="{t}";self.running=False\n    def start(self): self.running=True;logger.info(f"{{self.name}} started [{{self.tier}}]")\n    def stop(self): self.running=False;logger.info(f"{{self.name}} stopped")\n    def heartbeat(self): return {{"organ":self.name,"tier":self.tier,"status":"running" if self.running else "stopped","ts":time.time()}}\ndef main():\n    logging.basicConfig(level=logging.INFO,format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")\n    o={cls}Organ()\n    signal.signal(signal.SIGTERM,lambda s,f:(o.stop(),sys.exit(0)))\n    signal.signal(signal.SIGINT,lambda s,f:(o.stop(),sys.exit(0)))\n    o.start()\n    while o.running: time.sleep(30);o.heartbeat()\nif __name__=="__main__": main()\n'
        try:
            with open(path,"w") as f: f.write(content)
            os.chmod(path, 0o755)
        except Exception: pass

    def _deploy_subsystem(self, key, manifest):
        path = f"{manifest.install_path}/{SUBSYSTEM_MAP[key]['path']}"
        os.makedirs(path, exist_ok=True)

    def _generate_services(self, manifest):
        svc_dir = f"{manifest.install_path}/services"; os.makedirs(svc_dir, exist_ok=True); count = 0
        for tier,cfg in {"p0_critical":{"restart_sec":5,"tier":"P0"},"p1_important":{"restart_sec":10,"tier":"P1"},"p2_standard":{"restart_sec":15,"tier":"P2"}}.items():
            organs = {"p0_critical":P0_ORGANS,"p1_important":P1_ORGANS,"p2_standard":P2_ORGANS}[tier]
            for organ in organs:
                content = SYSTEMD_TEMPLATE.format(organ_display=organ.replace("_"," ").title(),tier=cfg["tier"],install_path=manifest.install_path,tier_dir=tier,organ_name=organ,restart_sec=cfg["restart_sec"],data_path=manifest.data_path,log_path=manifest.log_path)
                try:
                    with open(f"{svc_dir}/veilcore-{organ}.service","w") as f: f.write(content)
                    count += 1
                except Exception: pass
        return count

    def _verify_deployment(self, manifest):
        v = 0
        for tier,organs in [("p0_critical",P0_ORGANS),("p1_important",P1_ORGANS),("p2_standard",P2_ORGANS)]:
            for organ in organs:
                if os.path.exists(f"{manifest.install_path}/organs/{tier}/{organ}.py"): v += 1
        for key in manifest.subsystems:
            if key in SUBSYSTEM_MAP and os.path.isdir(f"{manifest.install_path}/{SUBSYSTEM_MAP[key]['path']}"): v += 1
        svc_dir = f"{manifest.install_path}/services"
        if os.path.isdir(svc_dir): v += len([f for f in os.listdir(svc_dir) if f.endswith(".service")])
        return v

    def _save_manifest(self, manifest, result):
        try:
            path = f"{manifest.data_path}/deploy-backups/{result.deploy_id}.json"
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path,"w") as f: json.dump({"manifest":manifest.to_dict(),"result":result.to_dict(),"log":self._deploy_log},f,indent=2,default=str)
        except Exception: pass

    def upgrade(self, manifest):
        manifest.mode = "upgrade"; return self.deploy(manifest)

    def rollback(self, deploy_id):
        if os.path.isdir(self._backup_path): return len(os.listdir(self._backup_path)) > 0
        return False

    def generate_install_script(self, manifest):
        return f"#!/bin/bash\n# VeilCore Installer — Genesis\n# Hospital: {manifest.hospital_name or 'Unconfigured'}\nset -euo pipefail\necho '🔱 VeilCore Installer — Genesis'\n"

    def _log(self, msg):
        self._deploy_log.append(f"[{datetime.now(timezone.utc).isoformat()}] {msg}")
        logger.info(msg)

    def summary(self):
        return {"engine":"DeploymentEngine","codename":"Genesis","total_organs":len(P0_ORGANS)+len(P1_ORGANS)+len(P2_ORGANS),"subsystems":len(SUBSYSTEM_MAP),"p0":len(P0_ORGANS),"p1":len(P1_ORGANS),"p2":len(P2_ORGANS)}
EOF