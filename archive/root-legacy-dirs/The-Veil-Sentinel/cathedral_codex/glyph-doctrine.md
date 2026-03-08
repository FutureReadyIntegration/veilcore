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
