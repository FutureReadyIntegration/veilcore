"""VeilCore Deployment Engine — Genesis"""
from __future__ import annotations
import json, logging, os, platform, shutil, subprocess, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
logger = logging.getLogger("veilcore.deployer.engine")

class DeployPhase(str, Enum):
    PREFLIGHT="preflight"; CORE="core"; ORGANS_P0="organs_p0"; ORGANS_P1="organs_p1"
    ORGANS_P2="organs_p2"; SUBSYSTEMS="subsystems"; SERVICES="services"
    DASHBOARD="dashboard"; VERIFICATION="verification"; COMPLETE="complete"
    FAILED="failed"; ROLLBACK="rollback"

@dataclass
class SystemRequirements:
    min_python: tuple = (3, 10)
    min_ram_gb: float = 4.0
    min_disk_gb: float = 10.0

@dataclass
class PreflightResult:
    passed: bool = True; os_name: str = ""; os_version: str = ""; python_version: str = ""
    ram_gb: float = 0.0; disk_gb: float = 0.0
    errors: list[str] = field(default_factory=list); warnings: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    def to_dict(self):
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
    def to_dict(self):
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
    def to_dict(self):
        return {"deploy_id":self.deploy_id,"success":self.success,"mode":self.mode,"phase":self.phase,"phases_completed":self.phases_completed,"organs_deployed":self.organs_deployed,"subsystems_deployed":self.subsystems_deployed,"services_created":self.services_created,"services_started":self.services_started,"errors":self.errors,"warnings":self.warnings,"duration_seconds":round(self.duration_seconds,2),"timestamp":self.timestamp,"rollback_performed":self.rollback_performed}

P0_ORGANS = ["guardian","sentinel","cortex","audit","chronicle","insider_threat","phi_classifier","encryption_enforcer","watchdog","firewall","backup","quarantine","vault","mfa"]
P1_ORGANS = ["rbac","host_sensor","network_monitor","threat_intel","phi_guard","epic_connector","imprivata_bridge","hl7_filter","fhir_gateway","dicom_shield","iomt_protector","canary","scanner","patcher"]
P2_ORGANS = ["encryptor","dlp_engine","behavioral_analysis","anomaly_detector","vpn_manager","certificate_authority","key_manager","session_monitor","compliance_engine","risk_analyzer","forensic_collector","incident_responder","malware_detector","ransomware_shield","zero_trust_engine","micro_segmentation","api_gateway","load_balancer","waf","ids_ips","siem_connector","log_aggregator","metrics_collector","alert_manager","notification_engine","email_gateway","sms_notifier","webhook_handler","dns_filter","web_proxy","content_filter","ssl_inspector","traffic_shaper","bandwidth_monitor","port_scanner","vulnerability_scanner","patch_manager","config_auditor","baseline_monitor","integrity_checker","file_monitor","registry_watcher","process_monitor","service_guardian","resource_limiter","performance_monitor","health_checker","uptime_tracker","disaster_recovery","snapshot_manager","replication_engine","failover_controller","backup_validator","compliance_tracker"]

SUBSYSTEM_MAP = {"mesh":{"name":"NerveBridge","path":"core/mesh","priority":1},"ml":{"name":"DeepSentinel","path":"core/ml","priority":2},"federation":{"name":"AllianceNet","path":"core/federation","priority":3},"pentest":{"name":"RedVeil","path":"core/pentest","priority":4},"mobile":{"name":"Watchtower","path":"core/mobile","priority":5},"accessibility":{"name":"EqualShield","path":"core/accessibility","priority":6},"wireless":{"name":"AirShield","path":"core/wireless","priority":7},"physical":{"name":"IronWatch","path":"core/physical","priority":8}}

SYSTEMD_TEMPLATE = "[Unit]\nDescription=VeilCore {organ_display} ({tier})\nAfter=network.target\n[Service]\nType=simple\nUser=veilcore\nWorkingDirectory={install_path}\nExecStart=/usr/bin/python3 {install_path}/organs/{tier_dir}/{organ_name}.py\nRestart=always\nRestartSec={restart_sec}\nNoNewPrivileges=yes\nProtectSystem=strict\nReadWritePaths={data_path} {log_path}\n[Install]\nWantedBy=multi-user.target\n"

class DeploymentEngine:
    def __init__(self):
        self._requirements = SystemRequirements()
        self._deploy_log = []
        self._backup_path = "/var/lib/veilcore/deploy-backups"

    def preflight_check(self):
        r = PreflightResult(); r.os_name = platform.system()
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        r.os_version = line.split("=")[1].strip().strip('"'); break
        except Exception: r.os_version = platform.version()
        r.checks["os_compatible"] = "ubuntu" in r.os_version.lower()
        pv = platform.python_version_tuple(); r.python_version = platform.python_version()
        r.checks["python_version"] = (int(pv[0]),int(pv[1])) >= self._requirements.min_python
        if not r.checks["python_version"]: r.errors.append("Python too old"); r.passed = False
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"): r.ram_gb = round(int(line.split()[1])/1024/1024, 1); break
        except Exception: pass
        r.checks["ram_sufficient"] = r.ram_gb >= self._requirements.min_ram_gb
        try:
            st = os.statvfs("/"); r.disk_gb = (st.f_bavail * st.f_frsize)/(1024**3)
        except Exception: pass
        r.checks["disk_sufficient"] = r.disk_gb >= self._requirements.min_disk_gb
        if not r.checks["disk_sufficient"]: r.errors.append("Disk too small"); r.passed = False
        r.checks["root_access"] = os.geteuid() == 0
        r.checks["systemd_available"] = os.path.exists("/run/systemd/system")
        if r.errors: r.passed = False
        return r

    def deploy(self, manifest):
        start = time.monotonic(); result = DeploymentResult(mode=manifest.mode)
        try:
            result.phase = DeployPhase.PREFLIGHT; pf = self.preflight_check()
            if not pf.passed and any("Disk" in e for e in pf.errors):
                result.errors.extend(pf.errors); result.phase = DeployPhase.FAILED; return result
            result.phases_completed.append(DeployPhase.PREFLIGHT)
            result.phase = DeployPhase.CORE; self._create_dirs(manifest); result.phases_completed.append(DeployPhase.CORE)
            for tier, organs, phase in [("p0_critical",P0_ORGANS,DeployPhase.ORGANS_P0),("p1_important",P1_ORGANS,DeployPhase.ORGANS_P1),("p2_standard",P2_ORGANS,DeployPhase.ORGANS_P2)]:
                result.phase = phase; result.organs_deployed += self._deploy_tier(tier, organs, manifest); result.phases_completed.append(phase)
            result.phase = DeployPhase.SUBSYSTEMS
            for sk in manifest.subsystems:
                if sk in SUBSYSTEM_MAP: os.makedirs(f"{manifest.install_path}/{SUBSYSTEM_MAP[sk]['path']}", exist_ok=True); result.subsystems_deployed += 1
            result.phases_completed.append(DeployPhase.SUBSYSTEMS)
            result.phase = DeployPhase.SERVICES; result.services_created = self._gen_services(manifest); result.phases_completed.append(DeployPhase.SERVICES)
            result.phase = DeployPhase.DASHBOARD; os.makedirs(f"{manifest.install_path}/dashboard", exist_ok=True); result.phases_completed.append(DeployPhase.DASHBOARD)
            result.phase = DeployPhase.VERIFICATION; result.services_started = self._verify(manifest); result.phases_completed.append(DeployPhase.VERIFICATION)
            result.phase = DeployPhase.COMPLETE; result.success = True; result.phases_completed.append(DeployPhase.COMPLETE)
            self._save(manifest, result)
        except Exception as e: result.phase = DeployPhase.FAILED; result.errors.append(str(e))
        result.duration_seconds = time.monotonic() - start; return result

    def _create_dirs(self, m):
        for d in [m.install_path,f"{m.install_path}/organs/p0_critical",f"{m.install_path}/organs/p1_important",f"{m.install_path}/organs/p2_standard",f"{m.install_path}/core",f"{m.install_path}/dashboard",f"{m.install_path}/services",m.data_path,f"{m.data_path}/deploy-backups",m.log_path,m.config_path]:
            os.makedirs(d, exist_ok=True)

    def _deploy_tier(self, tier, organs, manifest):
        td = f"{manifest.install_path}/organs/{tier}"; os.makedirs(td, exist_ok=True)
        for o in organs:
            p = f"{td}/{o}.py"
            if not os.path.exists(p):
                c = o.title().replace("_",""); t = tier.split("_")[0].upper()
                with open(p,"w") as f:
                    f.write("#!/usr/bin/env python3\nimport logging,time,signal,sys\n")
                    f.write(f"class {c}Organ:\n")
                    f.write(f"    def __init__(self): self.name='{o}';self.tier='{t}';self.running=False\n")
                    f.write("    def start(self): self.running=True\n")
                    f.write("    def stop(self): self.running=False\n")
                    f.write("    def heartbeat(self): return {'organ':self.name,'tier':self.tier,'ts':time.time()}\n")
                    f.write("def main():\n")
                    f.write("    logging.basicConfig(level=logging.INFO)\n")
                    f.write(f"    o={c}Organ();o.start()\n")
                    f.write("    signal.signal(signal.SIGTERM,lambda s,f:(o.stop(),sys.exit(0)))\n")
                    f.write("    while o.running: time.sleep(30);o.heartbeat()\n")
                    f.write("if __name__=='__main__': main()\n")
                os.chmod(p, 0o755)
        return len(organs)

    def _gen_services(self, manifest):
        sd = f"{manifest.install_path}/services"; os.makedirs(sd, exist_ok=True); c = 0
        for tier,cfg in {"p0_critical":{"restart_sec":5,"tier":"P0"},"p1_important":{"restart_sec":10,"tier":"P1"},"p2_standard":{"restart_sec":15,"tier":"P2"}}.items():
            for o in {"p0_critical":P0_ORGANS,"p1_important":P1_ORGANS,"p2_standard":P2_ORGANS}[tier]:
                with open(f"{sd}/veilcore-{o}.service","w") as f:
                    f.write(SYSTEMD_TEMPLATE.format(organ_display=o.replace("_"," ").title(),tier=cfg["tier"],install_path=manifest.install_path,tier_dir=tier,organ_name=o,restart_sec=cfg["restart_sec"],data_path=manifest.data_path,log_path=manifest.log_path))
                c += 1
        return c

    def _verify(self, manifest):
        v = 0
        for tier,organs in [("p0_critical",P0_ORGANS),("p1_important",P1_ORGANS),("p2_standard",P2_ORGANS)]:
            for o in organs:
                if os.path.exists(f"{manifest.install_path}/organs/{tier}/{o}.py"): v += 1
        for k in manifest.subsystems:
            if k in SUBSYSTEM_MAP and os.path.isdir(f"{manifest.install_path}/{SUBSYSTEM_MAP[k]['path']}"): v += 1
        sd = f"{manifest.install_path}/services"
        if os.path.isdir(sd): v += len([f for f in os.listdir(sd) if f.endswith(".service")])
        return v

    def _save(self, manifest, result):
        try:
            p = f"{manifest.data_path}/deploy-backups/{result.deploy_id}.json"
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p,"w") as f: json.dump({"manifest":manifest.to_dict(),"result":result.to_dict()},f,indent=2,default=str)
        except Exception: pass

    def upgrade(self, m): m.mode = "upgrade"; return self.deploy(m)

    def rollback(self, did):
        if os.path.isdir(self._backup_path): return len(os.listdir(self._backup_path)) > 0
        return False

    def generate_install_script(self, m):
        return "#!/bin/bash\n# VeilCore Installer Genesis\necho VeilCore Installer\n"

    def _log(self, msg):
        self._deploy_log.append(f"[{datetime.now(timezone.utc).isoformat()}] {msg}"); logger.info(msg)

    def summary(self):
        return {"engine":"DeploymentEngine","codename":"Genesis","total_organs":len(P0_ORGANS)+len(P1_ORGANS)+len(P2_ORGANS),"subsystems":len(SUBSYSTEM_MAP),"p0":len(P0_ORGANS),"p1":len(P1_ORGANS),"p2":len(P2_ORGANS)}
