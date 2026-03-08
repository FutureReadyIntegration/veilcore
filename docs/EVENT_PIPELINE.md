# VeilCore Event Pipeline

## Purpose

The VeilCore event pipeline turns system behavior into visible, actionable defensive state.

It connects:

- engines
- API
- dashboard
- operator awareness

---

## Canonical Event Path

1. engine state changes
2. event emitted
3. event stored / exposed
4. `/events` returns structured records
5. dashboard poller consumes records
6. Prism feed updates
7. subsystem state and overlay react

---

## Example

Example engine failure:

```bash
POST /engines/ml/fail

---

## 5) `docs/IMMUTABILITY_AND_ACCOUNTABILITY.md`

```bash
cat > docs/IMMUTABILITY_AND_ACCOUNTABILITY.md <<'EOF'
# Immutability and Accountability

## Principle

VeilCore is intended to make actions, decisions, and work attributable.

The objective is not only security.
It is accountability.

---

## Why This Matters

Many systems fail because:

- actions are poorly tracked
- trust is ambiguous
- responsibility is deniable
- work can be altered without clear trace
- humans must guess legitimacy under pressure

VeilCore is intended to reduce these problems.

---

## Accountability Goals

VeilCore should evolve toward:

- immutable event history
- attributable actions
- explicit identity linkage
- traceable state changes
- non-repudiable operational records

---

## Intended Outcomes

With immutability and accountability:

- hostile actions are easier to reconstruct
- operator actions are traceable
- trust is based on system evidence
- work is harder to deny or erase
- hospitals and critical operators gain audit confidence

---

## Design Direction

VeilCore should move toward:

1. immutable ledger-backed records
2. signed action envelopes
3. controlled state mutation
4. sovereign authorization paths
5. reliable event journaling

---

## Human Factor Reduction

VeilCore is intended to reduce reliance on emotional trust judgments like:

- “is this really my teammate?”
- “should I trust this request?”
- “does this look legitimate?”

Instead, trust should come from system validation and attributable proof.

