from __future__ import annotations
import json, hashlib
from pathlib import Path
from veil.core.panic import panic, PanicCode


class CMOSConfig:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = self._load()
        self.hash = self._hash(self.data)

    def _load(self) -> dict:
        return json.loads(self.path.read_text())

    def _hash(self, data: dict) -> str:
        raw = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    def verify(self) -> None:
        current = self._hash(self._load())
        if current != self.hash:
            panic(PanicCode.CMOS_TAMPER, "CMOS hash mismatch")
