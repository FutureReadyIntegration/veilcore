from __future__ import annotations

import os
import sys
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from veil.core.eventbus import Event, EventBus
from veil.core.panic import PanicCode, raise_panic


@dataclass(frozen=True)
class PostConfig:
    required_paths: List[str]
    required_modules: List[str]
    require_venv: bool = True
    require_python_major: int = 3
    require_python_minor_at_least: int = 10


def check_filesystem(cfg: PostConfig, *, bus: Optional[EventBus] = None) -> None:
    bus = bus or EventBus()
    bus.emit(Event(prefix="post", name="fs.start", payload={"paths": cfg.required_paths}))

    for p_str in cfg.required_paths:
        p = Path(p_str)
        if not p.exists():
            raise_panic(
                PanicCode.POST_FAILURE,
                "Filesystem check failed: path missing",
                subsystem="post",
                details={"path": str(p)},
            )
        # If it's a directory, ensure it's readable (and writable if operator expects logs there)
        try:
            if p.is_dir():
                _ = list(p.iterdir())  # may raise permission error
            else:
                _ = p.stat()
        except Exception as e:
            raise_panic(
                PanicCode.POST_FAILURE,
                f"Filesystem check failed: {e}",
                subsystem="post",
                details={"path": str(p)},
            )

    bus.emit(Event(prefix="post", name="fs.ok", payload={"count": len(cfg.required_paths)}))


def check_imports(cfg: PostConfig, *, bus: Optional[EventBus] = None) -> None:
    bus = bus or EventBus()
    bus.emit(Event(prefix="post", name="imports.start", payload={"modules": cfg.required_modules}))

    for m in cfg.required_modules:
        try:
            importlib.import_module(m)
        except Exception as e:
            raise_panic(
                PanicCode.POST_FAILURE,
                "Import check failed",
                subsystem="post",
                details={"module": m, "error": str(e)},
            )

    bus.emit(Event(prefix="post", name="imports.ok", payload={"count": len(cfg.required_modules)}))


def check_runtime(cfg: PostConfig, *, bus: Optional[EventBus] = None) -> None:
    bus = bus or EventBus()
    bus.emit(Event(prefix="post", name="runtime.start", payload={}))

    # Python version sanity
    major = sys.version_info.major
    minor = sys.version_info.minor
    if major != cfg.require_python_major or minor < cfg.require_python_minor_at_least:
        raise_panic(
            PanicCode.POST_FAILURE,
            "Python version not supported",
            subsystem="post",
            details={"python": sys.version, "required": f"{cfg.require_python_major}.{cfg.require_python_minor_at_least}+"},
        )

    # Venv isolation sanity
    if cfg.require_venv:
        # sys.prefix differs from sys.base_prefix when venv is active
        if getattr(sys, "base_prefix", sys.prefix) == sys.prefix:
            raise_panic(
                PanicCode.POST_FAILURE,
                "Python environment isolation failed (not in venv)",
                subsystem="post",
                details={"sys.prefix": sys.prefix, "sys.base_prefix": getattr(sys, "base_prefix", None)},
            )

    bus.emit(
        Event(
            prefix="post",
            name="runtime.ok",
            payload={"python": f"{major}.{minor}", "venv": bool(getattr(sys, "base_prefix", sys.prefix) != sys.prefix)},
        )
    )
