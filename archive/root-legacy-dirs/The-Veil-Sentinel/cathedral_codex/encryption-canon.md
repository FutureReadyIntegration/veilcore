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
