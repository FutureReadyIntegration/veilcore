"""
VeilCore Wireless Guardian
=============================
Comprehensive wireless attack surface protection for
hospital environments.

Covers:
    - Wi-Fi monitoring and rogue AP detection
    - Bluetooth pairing lockdown and scanning
    - RFID/NFC channel protection
    - RF spectrum anomaly detection
    - Wireless device inventory and fingerprinting
    - Automatic threat response for wireless intrusions

Hospitals are wireless-dense environments:
    - Clinical Wi-Fi for EHR workstations
    - IoMT devices on dedicated WLANs
    - Bluetooth medical peripherals
    - RFID badge access systems
    - NFC-enabled equipment tracking

Every wireless signal is an attack surface.
The Veil covers them all.

Author: Future Ready
System: VeilCore Hospital Cybersecurity Defense
"""

__version__ = "1.0.0"
__codename__ = "AirShield"

from core.wireless.scanner import (
    WirelessScanner,
    WiFiNetwork,
    BluetoothDevice,
    WirelessScanResult,
)
from core.wireless.hardener import (
    WirelessHardener,
    HardeningRule,
    HardeningReport,
)
from core.wireless.rfid_nfc import (
    RFIDNFCGuard,
    RFIDTag,
    NFCEvent,
)
from core.wireless.engine import WirelessGuardianEngine

__all__ = [
    "WirelessScanner",
    "WiFiNetwork",
    "BluetoothDevice",
    "WirelessScanResult",
    "WirelessHardener",
    "HardeningRule",
    "HardeningReport",
    "RFIDNFCGuard",
    "RFIDTag",
    "NFCEvent",
    "WirelessGuardianEngine",
]
