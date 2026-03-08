from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from veil.core.eventbus import Event, EventBus
from veil.core.panic import PanicCode, raise_panic


def _canonical_json_bytes(obj: Dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class CMOSState:
    path: Path
    lock_path: Path
    config: Dict[str, Any]
    config_hash: str


class CMOS:
    """
    CMOS = config authority with tamper detection and lock enforcement.
    """

    def __init__(self, *, bus: Optional[EventBus] = None, path: Optional[Path] = None) -> None:
        self.bus = bus or EventBus()
        self.path = path or Path(os.environ.get("VEIL_CMOS_PATH", "/opt/veil_os/config/cmos.json"))
        self.lock_path = Path(str(self.path) + ".lock")
        self._state: Optional[CMOSState] = None

    def load(self) -> CMOSState:
        self.bus.emit(Event(prefix="cmos", name="load.start", payload={"path": str(self.path)}))

        if not self.path.exists():
            raise_panic(PanicCode.CMOS_SCHEMA, "CMOS config file missing", subsystem="cmos", details={"path": str(self.path)})

        raw = self.path.read_text(encoding="utf-8", errors="strict")
        try:
            cfg = json.loads(raw)
        except Exception as e:
            raise_panic(PanicCode.CMOS_SCHEMA, f"Invalid JSON: {e}", subsystem="cmos", details={"path": str(self.path)})

        if not isinstance(cfg, dict):
            raise_panic(PanicCode.CMOS_SCHEMA, "CMOS config must be a JSON object", subsystem="cmos", details={"path": str(self.path)})

        h = sha256_hex(_canonical_json_bytes(cfg))
        st = CMOSState(path=self.path, lock_path=self.lock_path, config=cfg, config_hash=h)
        self._state = st

        self.bus.emit(Event(prefix="cmos", name="load.ok", payload={"hash": h}))
        return st

    def verify_or_panic(self) -> None:
        if self._state is None:
            self.load()

        assert self._state is not None
        cfg_now = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(cfg_now, dict):
            raise_panic(PanicCode.CMOS_SCHEMA, "CMOS config must be a JSON object", subsystem="cmos")

        now_hash = sha256_hex(_canonical_json_bytes(cfg_now))
        if now_hash != self._state.config_hash:
            self.bus.emit(Event(prefix="cmos", name="tamper.detected", payload={"expected": self._state.config_hash, "got": now_hash}))
            raise_panic(
                PanicCode.CMOS_TAMPER,
                "CMOS hash mismatch (tamper suspected)",
                subsystem="cmos",
                details={"expected": self._state.config_hash, "got": now_hash},
            )

        self.bus.emit(Event(prefix="cmos", name="verify.ok", payload={"hash": now_hash}))

    def lock(self) -> None:
        # simple lock file mechanism (hospital-grade: deterministic + auditable)
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.lock_path.exists():
            self.lock_path.write_text("locked", encoding="utf-8")
        self.bus.emit(Event(prefix="cmos", name="lock", payload={"lock_path": str(self.lock_path)}))

    def ensure_unlocked_or_panic(self) -> None:
        if self.lock_path.exists():
            raise_panic(PanicCode.CMOS_LOCKED, "CMOS is locked", subsystem="cmos", details={"lock_path": str(self.lock_path)})

    # ---- pending hooks (stubs) ----
    def encrypt_config(self) -> None:
        # Pending: config encryption
        self.bus.emit(Event(prefix="cmos", name="pending.encrypt", payload={}))

    def schema_versioning(self) -> None:
        # Pending: schema version enforcement
        self.bus.emit(Event(prefix="cmos", name="pending.schema", payload={}))

    def rollback(self) -> None:
        # Pending: rollback to last-known-good with audit trail
        self.bus.emit(Event(prefix="cmos", name="pending.rollback", payload={}))
