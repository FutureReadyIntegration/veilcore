import os
import yaml
from typing import Dict, Any, Optional

ALIASES_PATH = "/opt/veil_os/organ_specs/aliases.yaml"


class AliasRegistry:
    def __init__(self, path: str = ALIASES_PATH):
        self.path = path
        self._aliases: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            self._aliases = {}
            return
        with open(self.path, "r") as f:
            self._aliases = yaml.safe_load(f) or {}

    def refresh(self):
        self._load()

    def all(self) -> Dict[str, Any]:
        return self._aliases

    def get(self, alias: str) -> Optional[Dict[str, Any]]:
        return self._aliases.get(alias)

    def resolve_organ(self, alias: str) -> Optional[str]:
        entry = self.get(alias)
        if not entry:
            return None
        return entry.get("organ")

    def display_name(self, alias: str) -> Optional[str]:
        entry = self.get(alias)
        if not entry:
            return None
        return entry.get("display_name")

    def feeds(self, alias: str) -> Optional[list]:
        entry = self.get(alias)
        if not entry:
            return None
        return entry.get("feeds") or []


_registry: Optional[AliasRegistry] = None


def registry() -> AliasRegistry:
    global _registry
    if _registry is None:
        _registry = AliasRegistry()
    return _registry
