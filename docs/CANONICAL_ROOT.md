# Canonical Root Declaration

## Purpose

This document defines the current public root truth of the VeilCore repository.

The repository contains both canonical source areas and transitional historical areas that remain under review.

This file exists so the public tree and the README tell the same story.

---

## Primary Public Root Directories

These are the primary root directories currently treated as canonical for the VeilCore platform narrative:

- `archive/`
- `assets/`
- `configs/`
- `deployment/`
- `docs/`
- `scripts/`
- `tests/`
- `veilcore/`

These directories should be considered the main public source-of-record surface for the current platform direction.

---

## Canonical Runtime Areas

The current canonical runtime paths are:

- `veilcore/veil/api.py`
- `scripts/veilcore_desktop.py`
- `scripts/prism_events.py`

The current canonical architecture areas are:

- `veilcore/core/`
- `veilcore/organs/`
- `veilcore/organ_specs/`
- `veilcore/security/`

---

## Transitional Root Directories

The following root directories still exist in the repository but should be treated as transitional, legacy-adjacent, duplicate-era, or pending rationalization until explicitly reviewed:

- `api/`
- `app/`
- `backend/`
- `bin/`
- `charts/`
- `cockpit/`
- `cockpit-frontend/`
- `config/`
- `core/`
- `dashboard/`
- `data/`
- `gui/`
- `hospital_gui/`
- `ledger/`
- `manual/`
- `organ_specs/`
- `organs/`
- `security/`
- `src/`
- `supervisor/`
- `tools/`
- `var/`
- `veil/`
- `veil_os/`
- `veil_os.egg-info/`

These are not automatically invalid, but they are not the primary public root narrative.

---

## Rule

When documenting, presenting, or extending VeilCore, prefer the canonical paths listed in this file unless a deliberate restoration or migration is being performed.

