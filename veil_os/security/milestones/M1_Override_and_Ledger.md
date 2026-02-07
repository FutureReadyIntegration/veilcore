# Milestone 1 — Override + Ledger (Phase 1)

Status: COMPLETE  
Version: 1.0  
Last-Updated: 2026-01-26  
Owner: Veil Sentinel / Security Engineering

---

## Purpose

Establish a governed, auditable override mechanism with an immutable,
tamper-evident ledger suitable for hospital-grade operations.

This milestone creates the foundation for all future override,
audit, emergency, and compliance functionality.

---

## Scope (In-Scope)

- Manual override creation via CLI
- Symbolic payloads (glyph + affirmation)
- Append-only ledger
- Hash-chained integrity (tamper detection)
- Ledger verification command
- Operator-visible outputs

---

## Out of Scope (Explicit)

- Emergency overrides
- Token-based overrides (QR / biometric)
- API / FastAPI integration
- Multilingual expansion beyond EN/FR
- Visualization / dashboards

---

## Implementation Summary

### Commands Implemented

- `veil override --method manual --lang <lang> --reason "<text>"`
- `veil ledger verify`
- `veil ledger path`
- `veil ledger tail --n <count>`

### Ledger Characteristics

- Format: JSON Lines (`.jsonl`)
- Append-only
- Each entry includes:
  - event_id
  - UTC timestamp
  - host
  - OS user + UID
  - override payload
  - previous hash
  - current hash

- Hash chain provides tamper evidence
- Default storage:
  - `/var/log/veil_os/override_ledger.jsonl`
  - fallback: `/opt/veil_os/logs/override_ledger.jsonl`

---

## Acceptance Tests (Authoritative)

### Test 1 — Create Override
```bash
veil override --method manual --lang en --reason "break-glass test 001"
