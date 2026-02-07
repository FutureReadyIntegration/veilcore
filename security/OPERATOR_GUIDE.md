
---

# 📄 `docs/DOCUMENTATION_POLICY.md`
_(Governance + compliance enforcement document)_

```markdown
# Veil OS CLI Documentation & Compliance Policy

**Audience:** Maintainers, reviewers, auditors  
**Control Type:** Administrative / Governance  
**Last Updated:** 2026-01-26

---

## 1. Purpose

This policy governs how operator-facing documentation is maintained
for the Veil OS Organ Engine CLI.

Documentation is treated as a **security and compliance control**.

---

## 2. Scope

This policy applies to any change that affects:

- CLI commands or flags
- Default behaviors
- Safety semantics
- Logging or auditing behavior
- Confirmation or authorization flow
- Error handling visible to operators

If an operator would notice the change, this policy applies.

---

## 3. Required Documents

### 3.1 Operator Usage Guide
- File: `docs/OPERATOR_GUIDE.md`
- Audience: operators
- Purpose: authoritative operational procedure

### 3.2 Documentation Policy
- File: `docs/DOCUMENTATION_POLICY.md`
- Audience: maintainers, auditors
- Purpose: governance and enforcement

---

## 4. Mandatory Change Rule

> Any change to CLI behavior MUST include a corresponding update to
> `docs/OPERATOR_GUIDE.md` in the same change set.

Changes without documentation updates are **incomplete**.

---

## 5. Required Change Checklist

For every CLI change, the author MUST verify:

- [ ] Commands listed are accurate
- [ ] Flags and defaults are correct
- [ ] Safety behavior is correctly described
- [ ] Examples match real syntax
- [ ] Logging and audit behavior is unchanged or updated
- [ ] Removed behavior is removed from docs
- [ ] New behavior is documented before release

---

## 6. Review Enforcement

Reviewers MUST NOT approve changes where:
- CLI behavior changed without doc updates
- Documentation is vague or misleading
- Safety semantics are unclear

The reviewer’s guiding question:
> “Would this document prevent operator harm at 3am?”

---

## 7. Compliance Alignment

### HIPAA
Supports:
- Administrative safeguards (§164.308)
- Audit controls (§164.312)
- System integrity

### SOC 2
Supports:
- Change management (CC8.x)
- Authorization and traceability
- Incident reconstruction

### ISO/IEC 27001
Supports:
- A.5.1 Policies
- A.12.1 Change management
- A.12.4 Logging and monitoring

---

## 8. Incident & Audit Use

During:
- Incident response
- Postmortems
- Compliance audits

The Operator Usage Guide represents **approved operational intent**.

Behavior that deviates from documentation is considered a defect.

---

## 9. Versioning Expectations

Significant CLI changes SHOULD update:
- “Last Updated” in OPERATOR_GUIDE.md
- Optional CHANGELOG entry

Example:

---

## 10. Summary

- Documentation is a control artifact
- Operators rely on it for safety
- Changes require synchronized updates
- Compliance depends on consistency

This policy exists to protect:
- Patients
- Operators
- Maintainers
- The organization
## Operator Acknowledgment

Operators are expected to:
- Read and understand this guide
- Follow documented procedures
- Review changes before applying them
- Use `--yes` only with intent

Failure to follow this guide constitutes a process violation.
