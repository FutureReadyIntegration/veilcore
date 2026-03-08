# Root Cleanup Plan

## Purpose

This document identifies what belongs at the repository root and what should be moved elsewhere.

The goal is to keep the root intentional, readable, and aligned with the current VeilCore platform.

---

## Root-Level Files That Should Exist

These are valid top-level files for the current VeilCore repo:

- README.md
- LICENSE
- NOTICE
- SECURITY.md
- .gitignore

Optional top-level files that may exist later:

- CONTRIBUTING.md
- CHANGELOG.md

---

## Root-Level Directories That Should Exist

These are valid top-level directories for the current VeilCore repo:

- docs/
- scripts/
- configs/
- deployment/
- archive/
- assets/
- tests/
- veilcore/

---

## Root-Level Rule

If a file at repo root is not:

- documentation
- license/policy
- config metadata
- or a deliberate entrypoint

then it likely belongs in one of:

- deployment/
- archive/
- configs/
- docs/

---

## Current Intent

VeilCore root should communicate:

1. what VeilCore is
2. where the canonical runtime lives
3. where deployment assets live
4. where archive material lives
5. where documentation lives

