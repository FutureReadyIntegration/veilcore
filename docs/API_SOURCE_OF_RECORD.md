# API Source of Record

## Canonical API

The canonical VeilCore API implementation is:

- `veilcore/veil/api.py`

This is the active FastAPI application used for current VeilCore runtime and testing.

---

## Legacy / Non-Canonical API Copy

A legacy backend API stub previously existed at:

- `veilcore/backend/veil/api.py`

That file is not the primary source of record for the current VeilCore platform and has been archived.

---

## Runtime Rule

When updating, testing, or documenting the VeilCore API, use:

- `veilcore/veil/api.py`

Do not treat backend legacy copies as canonical unless intentionally restoring historical behavior.

