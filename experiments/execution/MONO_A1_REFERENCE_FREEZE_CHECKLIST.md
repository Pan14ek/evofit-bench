# MONO-A1 reference-freeze procedure and W0 checklist

**Checkpoint:** `G-A1-C4-REF-FROZEN`

**Applies to:** MONO-E1 ΔA4 reference freeze

**Current status:** `NOT_READY` — exact ΔA4 source revisions and reference inputs remain unassigned/unverified. This checklist does not freeze or authorize a reference.

## Gate rule

Do not execute Method P on ΔA4 until W0 records `G-A1-C4-REF-FROZEN` as complete. The E1 reference must also be frozen and read back before either B0 or P starts. An unchecked item, unavailable source, unresolved required obligation, missing evaluator, or failed Git/readback check keeps the checkpoint `NOT_READY`. Do not treat a draft reference as a frozen reference.

The E1 transition labels are A0.3→A0.4. ΔA4 is the Reporting → Tasks public query-port migration. The exact commit and tree SHAs remain `UNASSIGNED` until W0 verifies this source change and confirms it is isolated from subsequent ΔA5 data-ownership and ΔA6 domain-event changes.

## W0 completion checklist

For every item, record the evidence path or digest and the reviewer/date. Leave the status unchecked until the evidence exists.

- [ ] **Source pair:** record before/after state IDs, full commit SHAs, tree SHAs, and commit lineage from the approved ΔA4 checkpoint. Read both commit and tree objects from Git. Confirm the source diff contains the ΔA4 Reporting → Tasks public query-port migration and is isolated from subsequent ΔA5 data-ownership and ΔA6 domain-event changes.
- [ ] **Stable fixture:** pin the workload, database fixture, environment, and permitted source changes shared by both arms.
- [ ] **Architecture facts:** derive facts independently from the pinned trees. Bind every fact used by the reference to the corresponding source SHA and raw evidence digest; mark unresolved facts `UNKNOWN`.
- [ ] **Target universe:** enumerate affected and unaffected representations and obligation targets. Independently justify the expected `retain`/no-op labels for this negative control; do not copy labels from B0 or P output.
- [ ] **Obligation denominator:** derive the full mandatory `Q(A_after)` from its source and policy inputs. Record `ACTIVE`, `INACTIVE`, and `UNKNOWN` with fact references. Keep unresolved mandatory obligations and do not calculate a complete denominator from partial inputs.
- [ ] **Exact-pair requirements:** for each active mandatory obligation, define required representation/evaluator pairs, scope, evaluator identity/version, pinned source/tree, artifact and configuration digests, capabilities, and evidence requirements. Missing or inadequate evaluators leave the affected pair `UNKNOWN`.
- [ ] **Method identities:** pin unchanged B0 and frozen Method P source/configuration identities, runner identity, input allowlists, and source-to-image provenance where available. Record unresolved provenance as `UNKNOWN`.
- [ ] **Schema validation:** validate the complete reference with `mono_a1_reference_v1.schema.json`. Keep it scorer-only; it must not appear in either method input bundle.
- [ ] **Freeze and readback:** only after the preceding items pass, call `freeze_reference(...)` once in a new scorer-only custody directory. Then call `load_verified_reference(...)` and verify exact reference bytes, seal metadata, source commit/tree identities, timestamp, and `MONO-E1` study ID.
- [ ] **Isolation:** create separate B0 and P bundles. Run `verify_method_input_isolation(...)` and independently review each allowlist and bundle inventory for reference, scorer, oracle, `.git`, network, and cross-arm exclusion.
- [ ] **Checkpoint record:** record `G-A1-C4-REF-FROZEN = PASS` only after all applicable checks above pass. Include the reference digest, freeze timestamp, source SHAs, evidence inventory, and W0 reviewer. Otherwise record `NOT_READY` with the missing items.

## Record

- W0 owner/reviewer: `UNASSIGNED`
- Before state / commit / tree: `A0.3 / UNASSIGNED / UNASSIGNED`
- After state / commit / tree: `A0.4 / UNASSIGNED / UNASSIGNED`
- Reference ID / SHA-256 / freeze timestamp: `UNASSIGNED / UNASSIGNED / NOT_FROZEN`
- Checkpoint: `G-A1-C4-REF-FROZEN = NOT_READY`
- Missing evidence: `exact ΔA4 source revisions, complete source-derived reference inputs, evaluator pins, and W0 readback`

## E2 source binding

This checklist covers the MONO-E1 gate. MONO-E2 uses the approved predecessor `A0_MONOLITH` at commit `b78b0967be937634b7762baccf5ac6892b279a73` and final `A1_MODULAR_MONOLITH`. Its after commit/tree remain unassigned until final A1 verification. The E2 reference schema rejects a different predecessor and requires complete Git SHAs before a reference can be sealed.
