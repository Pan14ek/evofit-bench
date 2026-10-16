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
| Strict additive DEVELOPMENT contracts | `schemas/p_*_v1.schema.json` |

## Processing and safety rules

`verify_v3_p_bundle()` accepts the method-P V3 manifest and returns a bundle
whose exact file roles and digests, common Snapshot, policy bundle, ruleset,
parent configuration and source revisions are bound. The orchestration calls
the SPEC 02 `evaluate_obligations()` implementation for both Snapshot states;
it does not add a second activation engine.

Fact and policy absences require their corresponding completeness evidence.
Impact analysis distinguishes proven reachability, possible reachability and
unresolved trace links. A new mandatory active obligation is considered even
when the old trace graph lacks an edge. Pair validity is exact to one
representation, obligation, architecture revision, stage, scope and semantic
proof. Compliance status is recorded separately from evaluator adequacy.

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

No evaluator code is synthesized or executed here. Method-side evaluator
evidence and semantic proof must be supplied and pinned. The current V3 catalog
does not carry approved mandatory classifications or executable generic
templates/cost authority, so real runs are expected to stop at `HOLD` until
those inputs are supplied under approved rules. Unknown multi-stage obligations
also remain unresolved.

Synthetic integration only exercises the closed orchestration boundary with
`TEST_ONLY` inputs and verifies the safe `HOLD` path under OPEN authority. A
successful synthetic unit-level governance decision verifies its finite
contract but does not amount to a full positively authorized V3 run. No
measured DA01 trial, G1/G4 approval, human B1 result, or claim of scientific
novelty follows from these tests. See
[`da01/P_ALGORITHM_STATUS.md`](da01/P_ALGORITHM_STATUS.md) and
[`docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md`](../../docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md).
