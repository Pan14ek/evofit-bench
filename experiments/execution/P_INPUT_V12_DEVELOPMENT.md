# Snapshot v1.2 DEVELOPMENT extension

**Status:** additive, unfrozen DEVELOPMENT contract. It is not a DA01 protocol
amendment, policy approval, production trust grant, or measured input.

## Purpose

Snapshot v1.1 has one `policy_registry.closure_claim_id`. A SPEC 02 assessment
over a before/after architecture pair needs a separate exact-revision closure
claim for each state. One claim cannot safely bind both revisions. Snapshot
v1.2 adds `policy_registry.closure_claim_ids`, a unique list of claim IDs, so
each state can be independently checked without widening the meaning of the
v1.1 field.

## Contract and verification

The new
[`architecture_policy_snapshot_v1_2.schema.json`](schemas/architecture_policy_snapshot_v1_2.schema.json)
keeps the v1.1 fact, policy, source, and completeness-claim shapes. Its only
Snapshot projection change is the versioned registry closure field. The
separately pinned V3 policy source accepts registry schema v1.1 or v1.2. For
v1.2, every listed identifier must bind exactly one
`AUTHORITATIVE_POLICY_REGISTRY` completeness claim. A claim can close a state
only when its state, architecture revision, scope, registry version, `as_of`,
source provenance, authority and evidence all validate for that state.

Incomplete, stale, duplicated, wrongly scoped, or mismatched evidence remains
unresolved and cannot establish absence or authorize a positive applicability
decision. V1.1 retains its single-claim behavior, including UNKNOWN/HOLD when
that claim does not prove both required states. The V2 exporter continues to
emit Snapshot v1.1; the v1.2 projection is available only through the V3
DEVELOPMENT path. Existing v1.1 schema bytes and frozen V1/V2 contracts are
unchanged.

## Evidence boundary

The V3 no-op and ADD integration scenarios use independent synthetic policy,
completeness, evaluator and sidecar evidence under `TEST_ONLY` trust. They
exercise verification code and accepted V1 adapters; they do not create
production authority or approve P. Missing evidence still produces
UNKNOWN/HOLD. G1 remains INCOMPLETE, G4 remains NOT AUTHORIZED, and
`p_interface.py` remains NOT_READY.
