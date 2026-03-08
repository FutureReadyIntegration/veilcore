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
