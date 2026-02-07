# Cathedral Codex Bundle

This file is generated. Do not edit directly.

## glyph-doctrine.md
- sha256: `2bd8c14f34b9f43cca2b6f24412990f4ccf32b7f47c0c9af35c1d98b0709b124`
- status: OK

# Glyph Doctrine
Version: 0.1.0
Owner: Security Engineering
Status: Draft
Last-Updated: 2026-01-26

## Purpose
Define the meaning of core “glyphs” (signals) used across Veil OS: Preview, Apply, Audit, Evidence, Target, Seal.

## Definitions
- PREVIEW: dry-run execution; no file writes allowed.
- APPLY: real writes; requires explicit operator intent.
- SEAL: integrity marker for evidence artifacts.

## Rules
1. Preview-first is mandatory.
2. Apply requires dual confirmation: GUI gate + CLI --yes.
3. Every run emits an audit event.

## Test Cases
- Running without --yes MUST imply Preview.
- Running with --yes MUST record APPLY in audit.


---

## override-authority.md
- sha256: `a6cb293aef5e74bcd0f2b2948fe9af98d6d8e0590b6eafd4b1db2aac8a2bfc14`
- status: OK

# Override Authority
Version: 0.1.0
Owner: Security Engineering
Status: Draft
Last-Updated: 2026-01-26

## Purpose
Define who can authorize APPLY (real writes) and under what conditions an emergency override is permitted.

## Roles
- Operator: may run PREVIEW, may request APPLY.
- Approver: authorized to approve APPLY execution.
- Maintainer: maintains codex and tooling.

## Rules
1. PREVIEW is always permitted.
2. APPLY requires explicit operator intent (`--yes`) and typed confirmation in GUI.
3. Emergency override is permitted only during incident response and must be documented in the run evidence bundle.

## Evidence Requirements
An APPLY run MUST record:
- operator identity (OS user)
- target path
- command executed
- time (UTC)
- outcome (exit code)
- approver identity (if applicable)

## Test Cases
- Running without `--yes` MUST remain PREVIEW.
- APPLY without confirmation MUST be blocked.


---

## encryption-canon.md
- sha256: `8ddda250a8a7088dee07802efa3e844bc5f5dac42d68a4c7c736427d314dd86f`
- status: OK

# Encryption Canon
Version: 0.1.0
Owner: Security Engineering
Status: Draft
Last-Updated: 2026-01-26

## Purpose
Define how audit logs and evidence bundles are protected at rest and in transit.

## Data Classes
- Audit Log: JSONL security record.
- Evidence Bundle: per-run artifact containing command, outputs, and change evidence.

## Rules
1. Audit logs must be stored in a restricted directory with least-privilege permissions.
2. Evidence bundles must be stored in a restricted directory with least-privilege permissions.
3. If evidence is exported off-host, transport must be secured (approved secure copy method).

## Minimum File Permissions (example)
- Audit directory: 750
- Audit files: 640
- Evidence directory: 750
- Evidence files: 640

## Test Cases
- Non-authorized users MUST NOT read audit or evidence files.
- Evidence export MUST be explicit and logged.


---

## accessibility-oaths.md
- sha256: `e82d8425cb83c99a291df2e88e9da4c324755a90392972184a14c69cce72316a`
- status: OK

# Accessibility Oaths
Version: 0.1.0
Owner: Operations Engineering
Status: Draft
Last-Updated: 2026-01-26

## Purpose
Ensure the system is usable under stress (on-call, incident response) without command memorization.

## Rules
1. GUI must expose primary actions as buttons: Compile, Compile P0, Compile All, Harden.
2. GUI must show command preview before execution.
3. PREVIEW must be default (no surprise writes).
4. APPLY must require explicit intent and confirmation.
5. Output must be visible and copyable for ticketing.

## Usability Requirements
- No required terminal usage for routine runs.
- Targets must be selectable via browse or saved list.
- Clear visual distinction between PREVIEW and APPLY modes.

## Test Cases
- An operator can complete a PREVIEW run without typing commands.
- APPLY requires deliberate multi-step confirmation.


---

## deployment-psalms.md
- sha256: `9cf422f56e916f746a5891003d0e68b61c3f8e80a9cc3732f8f1fffb34cbdde7`
- status: OK

# Deployment Psalms
Version: 0.1.0
Owner: Platform Engineering
Status: Draft
Last-Updated: 2026-01-26

## Purpose
Define safe deployment and upgrade procedures for Veil OS tooling.

## Rules
1. Install/upgrade must be reproducible using the pinned venv path.
2. Changes must be reviewed and documented (see Documentation Policy).
3. Release must include version info and rollback instructions.

## Standard Install Location
- Venv: /srv/veil_os/api_venv
- Source: /opt/veil_os

## Upgrade Procedure (example)
1. Pull/update source.
2. Reinstall editable:
   `/srv/veil_os/api_venv/bin/python -m pip install -e /opt/veil_os --force-reinstall`
3. Validate:
   - `veil --help`
   - `veil-gui` launches
4. Record change ticket / change id.

## Test Cases
- Upgrade does not break existing entrypoints.
- Rollback can restore prior version.


---

## emergence-protocols.md
- sha256: `42ea69d03dc4e65b01ffe9d0f4372edae990ac05db3f27c20fc3bf1549254cc6`
- status: OK

# Emergence Protocols
Version: 0.1.0
Owner: Incident Response
Status: Draft
Last-Updated: 2026-01-26

## Purpose
Define incident response triggers and required actions for Veil OS operations.

## Triggers
- Unexpected configuration changes
- Audit log anomalies
- Failed hardening/compile runs impacting service health
- Suspected unauthorized APPLY execution

## Response Requirements
1. Preserve audit logs and evidence bundles.
2. Identify: operator, host, target, command, UTC time, outcome.
3. Stop further APPLY runs until reviewed.
4. Document incident and remediation steps.

## Postmortem
- Verify documentation matches observed behavior.
- Update codex and operator guide if procedure gaps are found.

## Test Cases
- Incident workflow can reconstruct “who did what” from audit log.
- Evidence bundles are available for failed runs.


---

## seal-registry.md
- sha256: `c8316b9690d9c858737735520657892c1ef13a903cea220b04862684311627ac`
- status: OK

# Seal Registry
Version: 0.1.0
Owner: Security Engineering
Status: Draft
Last-Updated: 2026-01-26

## Purpose
Define the concept of “seals” (integrity markers) and how they are produced and verified.

## Seal Types
- Doc Seal: sha256 of each codex markdown file.
- Bundle Seal: sha256 of the compiled bundle output.
- Evidence Seal: sha256 for evidence bundle manifest (if used).

## Rules
1. Every codex doc MUST have a Doc Seal computed by the compiler.
2. The compiler MUST output a machine-readable seal registry (JSON).
3. Seals MUST be regenerated when codex files change.
4. Seal mismatches indicate tampering or drift and must be investigated.

## Test Cases
- Changing any codex file changes its seal.
- Seal registry includes all required files.



---
