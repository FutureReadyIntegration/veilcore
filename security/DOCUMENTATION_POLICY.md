# Veil OS Documentation Policy

**System:** Veil OS Organ Engine  
**Audience:** Maintainers, Reviewers, Operators, Auditors  
**Control Type:** Administrative / Governance  
**Effective Date:** 2026-01-26  
**Status:** Authoritative

---

## 1. Purpose

This policy defines how documentation for the Veil OS Organ Engine is created,
maintained, reviewed, and enforced.

Documentation governed by this policy is treated as a **security,
operational, and compliance control**.

The purpose of this policy is to ensure that:
- Operators can safely and correctly perform actions
- System behavior is transparent and auditable
- Changes do not silently introduce risk
- Documentation reliably reflects actual system behavior

---

## 2. Scope

This policy applies to **all documentation that describes or constrains
operator behavior**, including but not limited to:

- CLI usage
- Operational procedures
- Safety guarantees
- Logging and audit behavior
- Confirmation and authorization requirements
- Error handling visible to operators

This policy applies to **all changes** that would be observable to an operator
or reviewer.

---

## 3. Documentation as a Control Artifact

Documentation governed by this policy is **not informational only**.

> Documentation is considered part of the system’s control surface.
> Deviations between documented behavior and actual behavior are defects.

Documentation is used as:
- A statement of approved operational intent
- A reference during incident response
- Evidence during audits and compliance reviews

---

## 4. Required Documentation Set

The following documents are mandatory and authoritative.

### 4.1 Operator Usage Guide
- **File:** `docs/OPERATOR_GUIDE.md`
- **Audience:** Operators, on-call staff
- **Purpose:** Defines how the CLI is used safely and correctly
- **Characteristics:**
  - Describes *current behavior only*
  - Includes examples of all supported commands
  - Describes safety semantics and defaults
  - Does not include speculative or future behavior

### 4.2 Documentation Policy (This Document)
- **File:** `docs/DOCUMENTATION_POLICY.md`
- **Audience:** Maintainers, auditors
- **Purpose:** Defines governance, enforcement, and expectations
- **Characteristics:**
  - Describes how documentation is maintained
  - Defines when updates are required
  - Establishes reviewer responsibilities

### 4.3 Audit Log Policy
- **File:** `docs/AUDIT_LOG_POLICY.md`
- **Audience:** Security, compliance, auditors
- **Purpose:** Defines audit log handling and retention

---

## 5. Mandatory Update Rule

> Any change to system behavior that affects operators MUST be accompanied by
> an update to the Operator Usage Guide in the same change set.

This includes changes to:
- Commands or subcommands
- Flags or defaults
- Safety behavior (dry-run, confirmation, authorization)
- Logging or audit behavior
- Error handling or exit conditions
- Required arguments (e.g., `--target`)

A change that modifies behavior without updating documentation is considered
**incomplete and non-compliant**.

---

## 6. Documentation Change Checklist

For every change that affects CLI behavior, the author MUST verify:

- [ ] Command list is accurate
- [ ] Flag descriptions match actual behavior
- [ ] Default behaviors are correctly stated
- [ ] Safety semantics (`--yes`, `--dry-run`, confirmation) are correct
- [ ] Examples reflect real syntax
- [ ] Removed behavior is removed from documentation
- [ ] Logging and audit descriptions remain accurate
- [ ] “Last Updated” metadata is refreshed when appropriate

This checklist represents **minimum compliance**, not best effort.

---

## 7. Review and Approval Responsibilities

### 7.1 Author Responsibilities
- Identify whether a change affects operator behavior
- Update documentation proactively
- Ensure documentation reflects final behavior, not intent

### 7.2 Reviewer Responsibilities
Reviewers MUST NOT approve a change if:
- Behavior changed without documentation updates
- Documentation is ambiguous or misleading
- Safety implications are not clearly stated

Reviewers are expected to ask:

> “If an operator follows this documentation exactly, will they be safe?”

---

## 8. Enforcement

Documentation requirements are enforced through:
- Code review expectations
- CI checks that block merges when CLI changes occur without doc updates
- Audit review of documentation vs system behavior

Enforcement is preventative, not punitive.

---

## 9. Incident and Audit Usage

During:
- Incident response
- Postmortems
- Compliance audits

The Operator Usage Guide represents **approved operational intent** at the time
of execution.

If behavior deviates from documentation:
- The deviation is treated as a defect
- The documentation version is used as the reference point

---

## 10. Threat Model (Documentation-Specific)

### Considered Risks
- Operator error due to unclear instructions
- Undocumented behavior changes
- Silent default changes
- Ambiguity during incident reconstruction

### Mitigations
- Explicit documentation requirements
- Default non-destructive behavior
- Enforced synchronization between code and docs
- Audit logging of all actions

Residual risk is considered acceptable when this policy is followed.

---

## 11. Compliance Alignment

### HIPAA
Supports:
- Administrative safeguards (45 CFR §164.308)
- Audit controls (45 CFR §164.312)
- System integrity and accountability

### SOC 2
Supports:
- Change management (CC8.x)
- Traceability and authorization
- Operational consistency

### ISO/IEC 27001
Supports:
- A.5.1 Information security policies
- A.12.1 Change management
- A.12.4 Logging and monitoring

---

## 12. Versioning and Review

This policy MUST be reviewed:
- Upon material changes to CLI behavior
- During scheduled compliance reviews
- After incidents involving operator error

Significant updates SHOULD update the effective date.

---

## 13. Summary

Documentation under this policy:
- Is authoritative
- Is enforceable
- Is auditable
- Protects operators, systems, and stakeholders

Failure to maintain accurate documentation constitutes a governance failure.
