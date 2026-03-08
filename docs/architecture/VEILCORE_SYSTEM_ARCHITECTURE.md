# VeilCore System Architecture

## Overview

VeilCore is a modular hospital security platform built around a living runtime architecture composed of engines, organs, and event-driven response systems.

The system is designed to detect, analyze, and mitigate cyber and physical threats in healthcare environments.

Core design principles:

- Zero Trust enforcement
- Event-driven architecture
- Modular organ subsystem design
- Immutable audit capability
- Operator visibility and accountability

---

# System Layers

VeilCore operates across several runtime layers.

## Layer 1 — Operator Interface

Primary human interaction layers.

Components:

- VeilCore Desktop UI
- Prism Event Dashboard
- Embedded VeilCore Terminal
- Accessibility Engine

Location:

scripts/
veilcore/core/accessibility/

Responsibilities:

- display system status
- show live threat events
- allow operator interaction
- provide accessible interfaces

---

## Layer 2 — API Gateway

The system control interface.

Canonical source:

veilcore/veil/api.py

Primary endpoints include:

GET /events

POST /engines/{engine_id}/start  
POST /engines/{engine_id}/stop  
POST /engines/{engine_id}/restart  
POST /engines/{engine_id}/fail  

Responsibilities:

- route system commands
- provide system telemetry
- provide event stream to UI

---

## Layer 3 — Engine Manager

Engine Manager orchestrates subsystem engines.

Location:

core/engine_manager.py

Engines include:

- ML Threat Detection
- Physical Security Engine
- PenTest Engine
- Wireless Engine
- Mesh Network Engine
- Federation Engine

Responsibilities:

- start / stop engines
- monitor engine health
- emit system events

---

## Layer 4 — Organ System

Organs are modular operational subsystems.

Location:

veilcore/organs/

Examples:

audit  
firewall  
guardian  
dispatcher  
sentinel  
telemetry  
forensic  
imprivata  
hl7  
fhir  
vault  

Responsibilities:

- perform specialized security functions
- respond to events
- enforce policies

Each organ includes:

runner.py

and optional engine or support modules.

---

## Layer 5 — Organ Specifications

Organ configuration and metadata.

Location:

veilcore/organ_specs/

Specifications define:

- organ purpose
- runtime configuration
- dependencies
- behavior rules

---

## Layer 6 — Event Pipeline

Events drive system awareness.

Example flow:

Sensor Trigger  
→ Engine detects anomaly  
→ Event emitted  
→ API event stream  
→ Desktop dashboard update  

Event storage:

veilcore/data/events.json

---

## Layer 7 — Security Governance

Documentation and security policy.

Location:

veilcore/security/

Includes:

Threat model  
Incident response  
Access control policies  
Risk analysis  

---

# Accessibility Layer

VeilCore includes an accessibility engine designed to support operators with disabilities.

Components include:

- screen reader integration
- audio alerts
- braille interface support

Location:

veilcore/core/accessibility/

---

# Deployment Model

Typical deployment includes:

Hospital network sensors  
Server running VeilCore API and engines  
Operator workstations running VeilCore Desktop  

---

# Design Philosophy

VeilCore uses a defensive philosophy based on:

Detection  
Containment  
Operator awareness  
System accountability

The system prioritizes mitigation over simple alerting.

