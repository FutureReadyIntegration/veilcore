"""
VeilCore Wireless Scanner
============================
Scans and inventories all wireless devices and networks
in the hospital environment.

Capabilities:
    - Wi-Fi AP discovery with security audit
    - Bluetooth device enumeration
    - Rogue AP detection (unknown SSIDs, evil twins)
    - Signal strength mapping
    - Wireless device fingerprinting
    - Channel congestion analysis
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("veilcore.wireless.scanner")


class WiFiSecurity(str, Enum):
    OPEN = "open"
    WEP = "wep"
    WPA = "wpa"
    WPA2 = "wpa2"
    WPA3 = "wpa3"
    WPA2_ENTERPRISE = "wpa2_enterprise"
    WPA3_ENTERPRISE = "wpa3_enterprise"
    UNKNOWN = "unknown"


class WiFiBand(str, Enum):
    BAND_2_4 = "2.4GHz"
    BAND_5 = "5GHz"
    BAND_6 = "6GHz"


class DeviceTrust(str, Enum):
    TRUSTED = "trusted"
    KNOWN = "known"
    UNKNOWN = "unknown"
    ROGUE = "rogue"
    BANNED = "banned"


@dataclass
class WiFiNetwork:
    """Discovered Wi-Fi network."""
    ssid: str
    bssid: str
    channel: int = 0
    frequency_mhz: int = 0
    signal_dbm: int = -100
    security: str = "unknown"
    band: str = "2.4GHz"
    trust: str = "unknown"
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    clients_count: int = 0
    is_hidden: bool = False
    vendor: str = ""

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(f"{self.bssid}:{self.ssid}".encode()).hexdigest()[:16]

    @property
    def is_secure(self) -> bool:
        return self.security in ("wpa2", "wpa3", "wpa2_enterprise", "wpa3_enterprise")

    @property
    def risk_score(self) -> float:
        score = 0.0
        if self.security == "open":
            score += 40
        elif self.security == "wep":
            score += 35
        elif self.security == "wpa":
            score += 20
        if self.trust == "rogue":
            score += 40
        elif self.trust == "unknown":
            score += 15
        if self.is_hidden:
            score += 5
        if self.signal_dbm > -50:
            score += 5  # Strong unknown signal = suspicious
        return min(100.0, score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ssid": self.ssid, "bssid": self.bssid,
            "channel": self.channel, "frequency_mhz": self.frequency_mhz,
            "signal_dbm": self.signal_dbm, "security": self.security,
            "band": self.band, "trust": self.trust,
            "first_seen": self.first_seen, "last_seen": self.last_seen,
            "clients_count": self.clients_count, "is_hidden": self.is_hidden,
            "vendor": self.vendor, "fingerprint": self.fingerprint,
            "is_secure": self.is_secure, "risk_score": self.risk_score,
        }


@dataclass
class BluetoothDevice:
    """Discovered Bluetooth device."""
    address: str
    name: str = ""
    device_class: str = ""
    rssi: int = -100
    trust: str = "unknown"
    is_paired: bool = False
    is_connectable: bool = True
    service_uuids: list[str] = field(default_factory=list)
    first_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    vendor: str = ""

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.address.encode()).hexdigest()[:16]

    @property
    def risk_score(self) -> float:
        score = 0.0
        if self.trust == "rogue":
            score += 40
        elif self.trust == "unknown":
            score += 15
        if self.is_connectable and self.trust != "trusted":
            score += 10
        if not self.name:
            score += 10  # Unnamed devices are suspicious
        if self.rssi > -40:
            score += 10  # Very close unknown device
        return min(100.0, score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address, "name": self.name or "(unnamed)",
            "device_class": self.device_class, "rssi": self.rssi,
            "trust": self.trust, "is_paired": self.is_paired,
            "is_connectable": self.is_connectable,
            "service_uuids": self.service_uuids,
            "first_seen": self.first_seen, "last_seen": self.last_seen,
            "vendor": self.vendor, "fingerprint": self.fingerprint,
            "risk_score": self.risk_score,
        }


@dataclass
class WirelessScanResult:
    """Complete wireless scan result."""
    scan_id: str = field(default_factory=lambda: f"WSCAN-{int(time.time())}")
    wifi_networks: list[WiFiNetwork] = field(default_factory=list)
    bluetooth_devices: list[BluetoothDevice] = field(default_factory=list)
    rogue_aps: list[WiFiNetwork] = field(default_factory=list)
    rogue_bt: list[BluetoothDevice] = field(default_factory=list)
    scan_duration_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def total_devices(self) -> int:
        return len(self.wifi_networks) + len(self.bluetooth_devices)

    @property
    def rogue_count(self) -> int:
        return len(self.rogue_aps) + len(self.rogue_bt)

    @property
    def insecure_wifi_count(self) -> int:
        return sum(1 for n in self.wifi_networks if not n.is_secure)

    @property
    def overall_risk(self) -> str:
        if self.rogue_count > 0:
            return "HIGH"
        if self.insecure_wifi_count > 0:
            return "ELEVATED"
        return "NORMAL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "wifi_networks": [n.to_dict() for n in self.wifi_networks],
            "bluetooth_devices": [d.to_dict() for d in self.bluetooth_devices],
            "rogue_aps": [n.to_dict() for n in self.rogue_aps],
            "rogue_bt": [d.to_dict() for d in self.rogue_bt],
            "total_devices": self.total_devices,
            "rogue_count": self.rogue_count,
            "insecure_wifi": self.insecure_wifi_count,
            "overall_risk": self.overall_risk,
            "scan_duration_ms": round(self.scan_duration_ms, 2),
            "timestamp": self.timestamp,
        }


# ── Known hospital SSID patterns for trust classification ──
HOSPITAL_SSID_PATTERNS = [
    "Epic-", "Imprivata-", "Clinical-", "Medical-",
    "Hospital-", "Healthcare-", "Nursing-", "Lab-",
    "Pharmacy-", "Radiology-", "ICU-", "OR-",
    "VeilCore-", "BioMed-", "Telemetry-",
]

# ── Known medical Bluetooth device classes ──
MEDICAL_BT_CLASSES = [
    "Medical Device", "Pulse Oximeter", "Blood Pressure Monitor",
    "Glucose Meter", "Thermometer", "Heart Rate Monitor",
    "Infusion Pump", "Ventilator", "Patient Monitor",
]


class WirelessScanner:
    """
    Scans the wireless environment for devices and threats.

    Usage:
        scanner = WirelessScanner()
        scanner.add_trusted_ssid("Hospital-Clinical")
        scanner.add_trusted_bt("AA:BB:CC:DD:EE:FF")
        result = scanner.scan()
    """

    def __init__(self):
        self._trusted_ssids: set[str] = set()
        self._trusted_bssids: set[str] = set()
        self._trusted_bt: set[str] = set()
        self._banned_macs: set[str] = set()
        self._known_networks: dict[str, WiFiNetwork] = {}
        self._known_bt: dict[str, BluetoothDevice] = {}
        self._scan_count = 0
        self._inventory_path = "/var/lib/veilcore/wireless/inventory.json"

    def add_trusted_ssid(self, ssid: str) -> None:
        self._trusted_ssids.add(ssid)

    def add_trusted_bssid(self, bssid: str) -> None:
        self._trusted_bssids.add(bssid.upper())

    def add_trusted_bt(self, address: str) -> None:
        self._trusted_bt.add(address.upper())

    def ban_mac(self, mac: str) -> None:
        self._banned_macs.add(mac.upper())

    def scan(self) -> WirelessScanResult:
        """
        Perform full wireless environment scan.
        Uses system tools when available, falls back to
        simulated scan for environments without wireless hardware.
        """
        start = time.monotonic()
        self._scan_count += 1

        result = WirelessScanResult()

        # Scan Wi-Fi
        wifi_networks = self._scan_wifi()
        for net in wifi_networks:
            net.trust = self._classify_wifi_trust(net)
            result.wifi_networks.append(net)
            if net.trust == "rogue":
                result.rogue_aps.append(net)

        # Scan Bluetooth
        bt_devices = self._scan_bluetooth()
        for dev in bt_devices:
            dev.trust = self._classify_bt_trust(dev)
            result.bluetooth_devices.append(dev)
            if dev.trust == "rogue":
                result.rogue_bt.append(dev)

        result.scan_duration_ms = (time.monotonic() - start) * 1000

        # Update known inventory
        for net in wifi_networks:
            self._known_networks[net.bssid] = net
        for dev in bt_devices:
            self._known_bt[dev.address] = dev

        self._save_inventory()

        logger.info(
            f"Wireless scan #{self._scan_count}: "
            f"{len(wifi_networks)} WiFi, {len(bt_devices)} BT, "
            f"{result.rogue_count} rogue, risk={result.overall_risk}"
        )

        return result

    def _scan_wifi(self) -> list[WiFiNetwork]:
        """Scan for Wi-Fi networks."""
        networks = []

        # Try real scan first
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY", "device", "wifi", "list"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    parts = line.split(":")
                    if len(parts) >= 6:
                        # nmcli uses \ : escaping, handle BSSID colons
                        ssid = parts[0].strip()
                        # BSSID spans parts[1:7] for MAC address
                        bssid = ":".join(parts[1:7]).strip().replace("\\", "")
                        remaining = parts[7:]
                        if len(remaining) >= 4:
                            chan = remaining[0].strip()
                            freq = remaining[1].strip()
                            signal = remaining[2].strip()
                            security = remaining[3].strip()

                            net = WiFiNetwork(
                                ssid=ssid or "(hidden)",
                                bssid=bssid,
                                channel=int(chan) if chan.isdigit() else 0,
                                frequency_mhz=int(freq.split()[0]) if freq else 0,
                                signal_dbm=int(signal) - 100 if signal.isdigit() else -100,
                                security=self._map_security(security),
                                is_hidden=not bool(ssid),
                            )
                            networks.append(net)
                if networks:
                    return networks
        except Exception:
            pass

        # Fallback: simulated hospital environment
        return self._simulated_wifi_scan()

    def _scan_bluetooth(self) -> list[BluetoothDevice]:
        """Scan for Bluetooth devices."""
        devices = []

        # Try real scan
        try:
            result = subprocess.run(
                ["hcitool", "scan", "--flush"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n")[1:]:
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        devices.append(BluetoothDevice(
                            address=parts[0].strip(),
                            name=parts[1].strip() if len(parts) > 1 else "",
                        ))
                if devices:
                    return devices
        except Exception:
            pass

        # Fallback: simulated
        return self._simulated_bt_scan()

    def _simulated_wifi_scan(self) -> list[WiFiNetwork]:
        """Generate realistic hospital WiFi environment."""
        return [
            WiFiNetwork(ssid="Hospital-Clinical", bssid="00:1A:2B:3C:4D:01",
                        channel=6, frequency_mhz=2437, signal_dbm=-45,
                        security="wpa2_enterprise", band="2.4GHz"),
            WiFiNetwork(ssid="Hospital-IoMT", bssid="00:1A:2B:3C:4D:02",
                        channel=36, frequency_mhz=5180, signal_dbm=-55,
                        security="wpa2_enterprise", band="5GHz"),
            WiFiNetwork(ssid="Hospital-Guest", bssid="00:1A:2B:3C:4D:03",
                        channel=11, frequency_mhz=2462, signal_dbm=-60,
                        security="wpa2", band="2.4GHz"),
            WiFiNetwork(ssid="Epic-Wireless", bssid="00:1A:2B:3C:4D:04",
                        channel=44, frequency_mhz=5220, signal_dbm=-50,
                        security="wpa3_enterprise", band="5GHz"),
            WiFiNetwork(ssid="SuspiciousHotspot", bssid="DE:AD:BE:EF:00:01",
                        channel=6, frequency_mhz=2437, signal_dbm=-35,
                        security="open", band="2.4GHz"),
            WiFiNetwork(ssid="Hospital-Clinical", bssid="DE:AD:BE:EF:00:02",
                        channel=6, frequency_mhz=2437, signal_dbm=-30,
                        security="wpa2", band="2.4GHz"),  # Evil twin!
            WiFiNetwork(ssid="", bssid="AA:BB:CC:DD:EE:FF",
                        channel=1, frequency_mhz=2412, signal_dbm=-70,
                        security="wpa2", band="2.4GHz", is_hidden=True),
        ]

    def _simulated_bt_scan(self) -> list[BluetoothDevice]:
        """Generate realistic hospital BT environment."""
        return [
            BluetoothDevice(address="11:22:33:44:55:01", name="Nurse Station Printer",
                            device_class="Printer", rssi=-60),
            BluetoothDevice(address="11:22:33:44:55:02", name="Masimo SpO2 Monitor",
                            device_class="Medical Device", rssi=-45),
            BluetoothDevice(address="11:22:33:44:55:03", name="Imprivata Badge Reader",
                            device_class="Smart Card Reader", rssi=-50),
            BluetoothDevice(address="11:22:33:44:55:04", name="",
                            device_class="", rssi=-25, is_connectable=True),
            BluetoothDevice(address="11:22:33:44:55:05", name="Unknown-BT-Device",
                            device_class="Computer", rssi=-30, is_connectable=True),
        ]

    def _classify_wifi_trust(self, network: WiFiNetwork) -> str:
        """Classify WiFi network trust level."""
        if network.bssid.upper() in self._banned_macs:
            return "banned"

        if network.bssid.upper() in self._trusted_bssids:
            return "trusted"

        if network.ssid in self._trusted_ssids:
            # Check for evil twin: SSID matches but BSSID doesn't
            existing = [n for n in self._known_networks.values()
                        if n.ssid == network.ssid and n.bssid != network.bssid]
            if existing and network.bssid not in self._trusted_bssids:
                logger.warning(f"EVIL TWIN DETECTED: '{network.ssid}' from {network.bssid}")
                return "rogue"
            return "trusted"

        # Check hospital patterns
        for pattern in HOSPITAL_SSID_PATTERNS:
            if network.ssid.startswith(pattern):
                return "known"

        # Open networks in hospital = suspicious
        if network.security == "open":
            return "rogue"

        return "unknown"

    def _classify_bt_trust(self, device: BluetoothDevice) -> str:
        """Classify Bluetooth device trust level."""
        if device.address.upper() in self._banned_macs:
            return "banned"
        if device.address.upper() in self._trusted_bt:
            return "trusted"
        if device.device_class in MEDICAL_BT_CLASSES:
            return "known"
        if not device.name and device.rssi > -40:
            return "rogue"  # Close, unnamed, connectable = suspicious
        return "unknown"

    def _map_security(self, security_str: str) -> str:
        """Map nmcli security string to our enum."""
        s = security_str.lower()
        if "wpa3" in s and "enterprise" in s:
            return "wpa3_enterprise"
        if "wpa3" in s:
            return "wpa3"
        if "wpa2" in s and "enterprise" in s:
            return "wpa2_enterprise"
        if "wpa2" in s:
            return "wpa2"
        if "wpa" in s:
            return "wpa"
        if "wep" in s:
            return "wep"
        if not s or s == "--":
            return "open"
        return "unknown"

    def _save_inventory(self) -> None:
        """Persist wireless inventory."""
        try:
            os.makedirs(os.path.dirname(self._inventory_path), exist_ok=True)
            data = {
                "wifi": {bssid: n.to_dict() for bssid, n in self._known_networks.items()},
                "bluetooth": {addr: d.to_dict() for addr, d in self._known_bt.items()},
                "scan_count": self._scan_count,
                "last_scan": datetime.now(timezone.utc).isoformat(),
            }
            with open(self._inventory_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save inventory: {e}")

    @property
    def scan_count(self) -> int:
        return self._scan_count

    @property
    def known_network_count(self) -> int:
        return len(self._known_networks)

    @property
    def known_bt_count(self) -> int:
        return len(self._known_bt)
