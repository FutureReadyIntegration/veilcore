# VeilCore Repo Layout

## Canonical Layout

The intended repo structure for the current VeilCore beta-foundation branch is:

- README.md
- LICENSE
- NOTICE
- SECURITY.md
- .gitignore
- docs/
- scripts/
- configs/
- deployment/
- archive/
- assets/
- tests/
- veilcore/

---

## Directory Purpose

### docs/
Architecture, runtime, doctrine, release, and platform documentation.

### scripts/
Desktop launcher, UI scripts, event UI support, and platform scripts.

### configs/
Configuration files used by runtime components.

### deployment/
Systemd units, launchers, and deployment assets.

### archive/
Historical, broken, replaced, or non-canonical material kept for reference.

### assets/
Screenshots, diagrams, and presentation assets.

### tests/
Validation, integration, and simulation tests.

### veilcore/
Canonical platform source tree.

---

## Repo Discipline Rule

New material should be placed intentionally.

Do not leave deployment files, broken experiments, backup files, or runtime artifacts at the repo root.

