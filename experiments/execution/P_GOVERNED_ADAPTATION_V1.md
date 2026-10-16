# Governed fitness-configuration adaptation — DEVELOPMENT v1

This note describes the code path implementing the merged, still-draft SPEC 03
development document. It does not amend the DA01 protocol or settle SPEC 03's
open scientific decisions.

## Module map

| SPEC 03 concern | Implementation |
| --- | --- |
| Pinned V3 inputs and SPEC 01/02 reuse | `tooling/p_adaptation.py`, `p_policy_source_v3.py`, `p_applicability.py` |
| Typed architecture, policy and obligation deltas; trace graph; conservative impact | `tooling/p_impact.py` |
| Exact representation/obligation semantic validity and mandatory coverage | `tooling/p_semantic.py` |
| Deterministic retain/replace/add/deactivate/adjust choice and bounded costs | `tooling/p_operations.py` |
| Candidate materialization, child version identity and unchanged V1 adapters | `tooling/p_candidate.py` |
| ACCEPT/REJECT/HOLD, append-only event chain, conditional publish and rollback | `tooling/p_governance.py` |
| Strict additive DEVELOPMENT contracts | `schemas/p_*_v1.schema.json`, `p_adaptation_evidence_v2.schema.json` |

## Processing and safety rules

`verify_v3_p_bundle()` accepts the method-P V3 manifest and returns a bundle
whose exact file roles and digests, common Snapshot, policy bundle, ruleset,
parent configuration and source revisions are bound. The orchestration calls
the SPEC 02 `evaluate_obligations()` implementation for both Snapshot states;
it does not add a second activation engine.

The returned V3 bundle is an identity-registered verification result; a
caller-constructed object cannot claim verified provenance. Evidence sidecars
are verified by a configured trust registry against their canonical digest,
scope, revisions and source bindings. V1 adaptation evidence retains its prior
artifact-hash meaning and cannot authorize ADD/REPLACE. V2 binds the full
canonical template descriptor digest to the pinned V3 capability source;
executable artifact bytes are independently checked against their digest.
Missing verifier authority remains unresolved. Publication rechecks the sealed
governance decision, and rollback compares the revalidated configuration
digest with the exact requested target.

Fact and policy absences require their corresponding completeness evidence.
Impact analysis distinguishes proven reachability, possible reachability and
unresolved trace links. A new mandatory active obligation is considered even
when the old trace graph lacks an edge. Pair validity is exact to one
representation, obligation, architecture revision, stage, scope and semantic
proof. Coverage excludes stale revisions, invalid digests and conflicting
duplicate assessments. Compliance status is recorded separately from
evaluator adequacy.

Coverage counts each mandatory obligation once and never treats `UNKNOWN` as
`INACTIVE`. Operation choice needs exact pair evidence, real hash-bound
templates, known cost, and a completed bounded search. The candidate copies the
parent configuration and records its parent digest, source/policy/ruleset
identity, operations, artifact hashes and a deterministic child version ID.
V1 candidate output is a compatibility projection; V1 prediction is emitted
only after governance returns `ACCEPT`. Publication is conditional on the
validated context and parent digest still matching. Rollback requires fresh
positive checks in the current context.

## Explicit limits

The runtime does not synthesize evaluator code. Method-side evaluator evidence
and semantic proof must be supplied and pinned. The integration suite executes
an independently authored TEST_ONLY evaluator; this is not a production
evaluator. The current V3 catalog does not carry production-approved mandatory
classifications, executable generic templates, or cost authority, so real runs
remain on the `HOLD` path until those inputs are supplied under approved rules.
Unknown multi-stage obligations also remain unresolved.

Synthetic V3 no-op and ADD attempts use signed TEST_ONLY policy/evidence inputs,
a hash-pinned evaluator, typed impact, exact-pair evidence, candidate
materialization, and full-descriptor authorization for ADD. Both correctly
HOLD before accepted output: the current Snapshot Registry has one
`closure_claim_id`, so its selected claim cannot establish applicability for
both the before and after revisions. This contract blocker is recorded in the
implementation traceability report; it is not bypassed. A successful
synthetic unit-level governance decision verifies its finite contract but does
not amount to a positively accepted V3 P run. No measured DA01 trial, G1/G4
approval, human B1 result, or claim of scientific novelty follows from these
tests. See
[`da01/P_ALGORITHM_STATUS.md`](da01/P_ALGORITHM_STATUS.md) and
[`docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md`](../../docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md).
