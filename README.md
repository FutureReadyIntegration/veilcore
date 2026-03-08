# VeilCore

**VeilCore** is an event-driven cyber defense platform for healthcare and critical infrastructure.

It is built around a **Veil / Core** model:

- **Veil** — intercepts, challenges, contains, deceives, and delays hostile interaction.
- **Core** — protects sovereign system truth, policy, identity, and operational continuity.
- **Organs / Engines** — autonomous defensive subsystems responsible for specific security, resilience, and operations functions.
- **Prism** — the live command-center dashboard and operator surface.
- **Terminal** — the in-platform VeilCore terminal for command execution and administrative control.

VeilCore is designed to preserve continuity during cyber incidents, reduce ransomware impact, enforce accountability, and move hostile activity away from protected operational systems.

---

## Current Platform State

VeilCore currently includes:

- Live FastAPI backend
- `/events` event stream
- Engine control endpoints
- Desktop command dashboard
- Neural mesh / subsystem visualization
- Physical engine integration
- ML engine state testing
- In-platform terminal
- Accessibility engine foundation
- Immutability and accountability direction
- Healthcare resilience-first architecture

---

## Core Design Model

### The Veil
The Veil is the protective interaction layer.

Its purpose is to:

- absorb hostile contact
- redirect malicious behavior
- isolate suspicious activity
- delay or trap adversarial progress
- preserve the integrity of the Core

### The Core
The Core is the protected truth layer.

Its purpose is to own:

- policy truth
- identity trust
- action authorization
- accountability
- continuity state
- protected operations

### Organs / Engines
VeilCore uses distributed defensive modules called **organs** and **engines**.

Examples include:

- DeepSentinel
- IronWatch
- NerveBridge
- Prism
- RedVeil
- SkyVeil
- TrustForge
- AuditIron
- EqualShield
- AirShield

These modules emit state, consume events, and participate in coordinated defense behavior.

---

## Event-Driven Defense

VeilCore uses an event-driven model.

Example operational loop:

1. engine state changes
2. event emitted
3. `/events` updated
4. Prism dashboard reacts
5. subsystem visual state changes
6. operator sees live defensive state

This creates a real-time control-plane feedback loop rather than a passive dashboard-only model.

---

## Canonical Runtime Paths

### API
```bash
uvicorn veilcore.veil.api:app --host 127.0.0.1 --port 9444

---

## 2) `docs/ARCHITECTURE.md`

```bash
cat > docs/ARCHITECTURE.md <<'EOF'
# VeilCore Architecture

## Overview

VeilCore is an event-driven cyber defense platform structured around a **Veil / Core / Organ** model.

Its architecture is intended to preserve continuity, enforce accountability, and reduce compromise propagation in healthcare and critical infrastructure environments.

---

## Architectural Layers

### 1. Interaction Layer
This is where the outside world touches the system.

Examples:

- inbound requests
- suspicious activity
- external telemetry
- attacker interaction
- untrusted contact surfaces

This layer is assumed to be hostile or uncertain.

---

### 2. Veil Layer
The Veil is the containment, challenge, and deception layer.

Responsibilities:

- intercept hostile interaction
- separate untrusted contact from protected state
- redirect or contain malicious behavior
- delay adversarial progress
- provide controlled observability

The Veil exists so the Core is not directly exposed to hostile input.

---

### 3. Event Fabric
VeilCore uses an event fabric to turn system behavior into structured events.

Examples:

- engine degradation
- physical triggers
- state changes
- warnings
- critical incidents

The event fabric is the connective tissue between engines, dashboard, and defensive control logic.

---

### 4. Organ / Engine Layer
Organs and engines are autonomous defensive and operational modules.

Examples include:

- DeepSentinel (ML threat prediction / state)
- IronWatch (physical security)
- NerveBridge (mesh communication)
- RedVeil (pentest / adversarial space)
- Prism (dashboard / command)
- SkyVeil (cloud hybrid)
- TrustForge (HITRUST)
- AuditIron (SOC 2)
- EqualShield (accessibility)
- AirShield (wireless defense)

Each engine is expected to:
- emit state
- report health
- produce events
- accept commands where appropriate

---

### 5. Prism Command Layer
Prism is the live operator surface.

Responsibilities:

- display subsystem state
- show event feed
- visualize engine relationships
- expose command-and-control awareness
- provide a live dashboard for operational response

Prism is not sovereign truth. It is the operator-facing control and visibility layer.

---

### 6. Core Layer
The Core is the protected truth zone.

Responsibilities:

- policy truth
- action authorization
- identity trust
- accountability
- continuity state
- protected command authority

The Core must not directly trust hostile or unverified input.

---

### 7. Infrastructure Layer
This includes:

- host systems
- services
- deployment components
- operating environment
- hardware and resilience substrate

---

## VeilCore Operating Doctrine

VeilCore follows these principles:

1. assume breach pressure
2. preserve continuity
3. separate hostile input from sovereign truth
4. contain rather than merely observe
5. make work and actions accountable
6. reduce human trust ambiguity
7. favor event-driven state awareness over passive monitoring

---

## Canonical Runtime Components

### API
- `veilcore.veil.api:app`
- local host default: `127.0.0.1:9444`

### Desktop
- `scripts/veilcore_desktop.py`

### Events
- `/events`

### Engine Controls
- `/engines/{id}/...`

---

## Current Demonstrated Loop

A demonstrated VeilCore operational loop currently exists:

1. engine state changed
2. event emitted
3. `/events` updated
4. dashboard poller read event
5. subsystem card reacted
6. overlay / visual system updated

This confirms the platform is beyond static concept stage.

---

## Future Direction

Future architectural hardening includes:

- sovereign core boundaries
- signed action envelopes
- immutable action ledger
- stronger identity proofs
- automated containment chains
- deeper accessibility integration
- deployment simplification
- hospital-specific resilience workflows

