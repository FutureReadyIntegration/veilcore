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
