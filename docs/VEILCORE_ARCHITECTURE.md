# VeilCore Architecture

Author: Marlon Ástin Williams
Project: VeilCore Defense Platform
Branch: beta-foundation

---

## 1. Concept

Traditional security protects the perimeter.

VeilCore protects the Core.

Instead of allowing attackers to reach real infrastructure after a perimeter failure, VeilCore places a defensive veil of organs, engines, event handling, and containment logic between hostile activity and protected systems.

Attackers interact with the Veil, not the Core.

---

## 2. Core Principle

Traditional model:

User -> Firewall -> Server
              ^
           Attacker

If the firewall fails, the attacker can reach the real environment.

VeilCore model:

User -> Veil -> Core
         ^
      Attacker

The Veil absorbs, studies, contains, and redirects hostile interaction before it reaches the protected system truth layer.

---

## 3. Core vs Veil

### The Core

The Core is the protected truth layer.

It includes things such as:

- hospital systems
- patient-related infrastructure
- identity and policy truth
- continuity logic
- accountability records
- protected command authority

The Core should not directly trust hostile input.

### The Veil

The Veil is the protective interaction layer.

It is responsible for:

- interception
- challenge
- containment
- deception
- delay
- event generation
- controlled visibility

The Veil exists to keep the Core shielded.

---

## 4. Organ Architecture

VeilCore uses a distributed defensive model built from organs.

Primary organ path:

veilcore/organs/

Organs are modular security and operational units. They monitor, react, emit state, and participate in coordinated system defense.

Examples include:

- analytics
- audit
- auth
- auto_lockdown
- firewall
- forensic
- guardian
- hospital
- insider_threat
- metrics
- quarantine
- sentinel
- telemetry
- zero_trust

This structure gives VeilCore a living-system defensive model instead of a single monolithic control point.

---

## 5. Engine Layer

VeilCore also includes specialized engines in:

veilcore/core/

Examples include:

- core/accessibility
- core/cloud
- core/compliance
- core/federation
- core/mesh
- core/ml
- core/mobile
- core/pentest
- core/physical
- core/wireless

These engines provide higher-level capabilities such as:

- machine learning threat scoring
- penetration simulation
- wireless defense
- physical security integration
- accessibility support
- cloud and federation support

---

## 6. Event Fabric

VeilCore is event-driven.

Events are produced when engines or organs change state or detect conditions.

Examples include:

- engine.degraded
- engine.restarted
- physical.camera_feed_lost
- physical.sensor_triggered

These events flow through the platform and are used for:

- dashboard visibility
- threat awareness
- system reaction
- operator insight
- future automation chains

This event system is a core part of VeilCore’s defensive architecture.

---

## 7. API Layer

The canonical API source of record is:

veilcore/veil/api.py

The API provides live system visibility and engine control.

Important routes include:

- GET /health
- GET /organs
- GET /events
- POST /engines/{engine_id}/start
- POST /engines/{engine_id}/stop
- POST /engines/{engine_id}/restart
- POST /engines/{engine_id}/fail

This API is the command and visibility layer for live VeilCore operations.

---

## 8. Desktop / Prism Layer

The current desktop runtime is centered on the VeilCore desktop and Prism event presentation.

Primary runtime files include:

- scripts/veilcore_desktop.py
- scripts/prism_events.py

The desktop provides:

- subsystem health cards
- event feed visualization
- mesh / overlay visuals
- telemetry display
- integrated terminal behavior
- operator awareness

This is not intended to be a passive dashboard only. It is the operator-facing expression of the event-driven defense model.

---

## 9. Deception and Containment

Traditional security systems often focus on blocking.

VeilCore is designed around a stronger model:

- detect
- contain
- observe
- redirect
- preserve continuity

The goal is to keep attackers interacting with defensive layers instead of real protected infrastructure.

This changes the architecture from passive monitoring into active defensive mediation.

---

## 10. Hospital Focus

VeilCore is designed for healthcare and critical infrastructure conditions.

That includes environments involving:

- hospital operations
- clinical systems
- HL7 / FHIR related integrations
- medical networks
- patient-impacting infrastructure
- continuity-sensitive operations

The platform is designed to reduce ransomware impact and preserve operational continuity under attack pressure.

---

## 11. Accessibility Engine

VeilCore includes an accessibility direction as a core platform concern.

Relevant path:

veilcore/core/accessibility/

This area includes support work for:

- audio interaction
- screen reader support
- braille-oriented functionality
- accessible operator interaction

Accessibility is treated as a first-class platform concern, not an afterthought.

---

## 12. Accountability and Ledger Direction

VeilCore is intended to support traceability and accountability.

Relevant artifacts include:

- ledger.json
- ledger_legacy.json
- security and audit policies
- event history

The long-term goal is a platform where actions, decisions, and state changes are attributable and difficult to silently erase or deny.

This supports both security response and operational accountability.

---

## 13. Security Documentation Layer

Security and policy documentation is present under:

veilcore/security/

This includes materials such as:

- incident response
- access control policy
- audit log policy
- system overview
- threat model
- risk analysis
- operator guidance

This layer helps align the codebase with governance, audit, and operational review.

---

## 14. Current Canonical Source Areas

The primary active source areas currently treated as canonical are:

- veilcore/veil/
- veilcore/core/
- veilcore/organs/
- veilcore/organ_specs/
- veilcore/security/
- scripts/
- docs/

These areas represent the current source-of-record direction for the beta-foundation branch.

---

## 15. Current Beta Status

Branch:

beta-foundation

Current confirmed platform characteristics include:

- live API behavior
- working event route
- engine fail testing
- dashboard reaction to events
- physical engine integration
- desktop launch path
- in-platform terminal usage
- repository cleanup and source-of-record alignment

VeilCore is beyond concept stage and exists as an operational beta-foundation platform.

---

## 16. Future Direction

Planned or implied future directions include:

- sovereign core enforcement
- signed action envelopes
- automated containment chains
- stronger immutability
- clearer hospital deployment packages
- deeper accessibility validation
- federation across sites
- stronger operator accountability

---

## 17. Summary

VeilCore is a defensive architecture built around one principle:

The Veil protects the Core.

Instead of trusting the perimeter, VeilCore places a defensive fabric between hostile reality and protected system truth.

That defensive fabric is made of organs, engines, events, containment logic, visibility systems, and accountability direction.

The result is a platform designed not only to detect cyber pressure, but to contain it, study it, and preserve continuity while protecting critical systems.
