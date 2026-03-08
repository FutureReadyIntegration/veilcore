from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging
import subprocess
import sys
from typing import Iterable, List

from .organ import Organ
from .ledger import append_ledger_entry, verify_ledger

log = logging.getLogger(__name__)

# Directory containing YAML organ specs
SPECS: Path = Path(__file__).parent / "specs"

# Absolute path to the Auto-Hardener script
HARDENER_PATH: Path = Path(__file__).resolve().parents[1] / "autohardener.py"


@dataclass(frozen=True, slots=True)
class CompileResult:
    """Summary of what was compiled/activated."""
    tier: str
    activated: tuple[str, ...]


def _iter_organ_specs(spec_dir: Path = SPECS) -> Iterable[Path]:
    """Yield organ spec YAMLs in deterministic order (reproducible builds)."""
    yield from sorted(spec_dir.glob("*.yaml"), key=lambda p: p.name)


def _load_organs(spec_dir: Path = SPECS) -> List[Organ]:
    """Load all organ YAML specs into Organ objects."""
    organs: List[Organ] = []
    for spec in _iter_organ_specs(spec_dir):
        organs.append(Organ.from_yaml(spec))
    return organs


# ------------------------------------------------------------
# 🔱 HARDENER INTEGRATION
# ------------------------------------------------------------

def harden_service(target: str | Path, dry_run: bool = False) -> None:
    """
    Invoke the Veil Auto-Hardener against a target service directory.

    Example:
        harden_service("/home/user/veil_os/projects/test_project")
    """
    if not HARDENER_PATH.exists():
        raise FileNotFoundError(f"❌ Hardener not found at: {HARDENER_PATH}")

    target_path = Path(target).expanduser().resolve()

    if not target_path.exists():
        raise FileNotFoundError(f"❌ Hardening target does not exist: {target_path}")
    if not target_path.is_dir():
        raise NotADirectoryError(f"❌ Hardening target is not a directory: {target_path}")

    cmd = [sys.executable, str(HARDENER_PATH), "--target", str(target_path)]
    if dry_run:
        cmd.append("--dry-run")

    log.info("🔱 Running Auto-Hardener on: %s", target_path)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"❌ Auto-Hardener failed (exit={e.returncode}): {' '.join(cmd)}"
        ) from e

    log.info("🔱 Hardening pass complete.\n")


# ------------------------------------------------------------
# 🔱 ORGAN COMPILATION
# ------------------------------------------------------------

def compile_tier(tier: str, *, spec_dir: Path = SPECS, strict: bool = True) -> CompileResult:
    """
    Compile all organs of a given tier.

    Args:
        tier: e.g. "P0" or "P1"
        spec_dir: organ YAML spec directory
        strict: if True, stop on first organ failure; if False, continue compiling others.

    Returns:
        CompileResult(tier=..., activated=(...))
    """
    log.warning("🚨 Compiling %s Organs...\n", tier)

    organs = [o for o in _load_organs(spec_dir) if o.tier == tier]
    activated: List[str] = []

    for organ in organs:
        log.info("→ %s", organ.name)
        append_ledger_entry(organ.name, organ.tier)

        try:
            organ.activate()
            activated.append(organ.name)
        except Exception:
            log.exception("❌ Organ activation failed: %s (tier=%s)", organ.name, tier)
            if strict:
                raise

    log.info("\n✅ %s organs deployed.\n", tier)
    verify_ledger()
    return CompileResult(tier=tier, activated=tuple(activated))


def compile_p0(*, spec_dir: Path = SPECS, strict: bool = True) -> CompileResult:
    return compile_tier("P0", spec_dir=spec_dir, strict=strict)


def compile_p1(*, spec_dir: Path = SPECS, strict: bool = True) -> CompileResult:
    return compile_tier("P1", spec_dir=spec_dir, strict=strict)


# ------------------------------------------------------------
# 🔱 FULL ORGANISM COMPILATION + HARDENING
# ------------------------------------------------------------

def compile_all(
    target: str | Path | None = None,
    harden: bool = True,
    dry_run: bool = False,
    *,
    strict: bool = True,
    spec_dir: Path = SPECS,
) -> tuple[CompileResult, CompileResult]:
    """
    Compile all organs (P0 + P1) and optionally run the Auto-Hardener.

    Args:
        target: Path to a service root to harden.
        harden: Whether to run the hardener after compilation.
        dry_run: If True, hardener runs in diff-only mode.
        strict: if True, stop on first organ failure.
        spec_dir: organ spec directory.

    Returns:
        (p0_result, p1_result)
    """
    p0 = compile_p0(spec_dir=spec_dir, strict=strict)
    p1 = compile_p1(spec_dir=spec_dir, strict=strict)

    if harden:
        if not target:
            log.warning("⚠️ No hardening target provided. Skipping hardener.\n")
        else:
            harden_service(target, dry_run=dry_run)

    return p0, p1
