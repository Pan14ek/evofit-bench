# PILOT-02 DEVELOPMENT addendum V3

**Status:** prospective TEST_ONLY development continuation; not a DA01 protocol change.

**Purpose:** correct the V2 compliance classification defect and repeat the same bounded A0 → A0.1 DEVELOPMENT comparison with the existing Method P path.
**Applicability assumptions:** unchanged [V2 assumptions](PILOT_02_DEVELOPMENT_ASSUMPTIONS_V2.json).

## Reason for V3

The preserved V2 trace showed that a completed evaluator process was assigned `COMPLIANT` or `NON_COMPLIANT` from its exit code even when the same evidence reported unresolved inspection scope or target resolution. In particular, the unchanged B0 Import Linter command exited nonzero because one configured target, `app.repositories`, is absent from A0.1. That is an evaluator-scope mismatch; it does not establish an architectural violation. V2 remains byte-for-byte preserved and is not silently reinterpreted as a corrected execution.

The generic `assess_pair()` correction records compliance as `UNKNOWN` when the evidence cannot resolve evaluator identity/artifact, execution, inspection scope, configured-target resolution, stage/context, obligation mapping, or evidence-artifact integrity. Adequacy, evidence-contract satisfaction, semantic compatibility, and exact-pair proof remain separate from an observed compliance result: they can keep the pair or coverage unresolved without erasing a resolvable nonzero observation. A resolved completed nonzero result remains an observation of noncompliance and does not alone invalidate pair semantics.

The correction does not change applicability assumptions, Method P operations, candidate templates, candidate validation, policy authority, or governance rules. It does not supply semantic proof or change any DA01 restriction.

## Prospective execution

1. Run EXP-01 and EXP-02 on one clean committed source revision. Record that exact source revision and A0.1 application-tree digest.
2. Evaluate unchanged B0 and Method P on the same A0.1 tree, using the same A0 source/configuration, V2 applicability assumptions, pinned TEST_ONLY policy/profile inputs, and evaluator versions.
3. Supply the digest-validated EXP-02 execution sidecar to the existing `run_adaptation()` path before adaptation. Preserve its TEST_ONLY status and `not_admitted` semantic-pair status; it is not independent semantic evidence.
4. Validate each materialized candidate evaluator row against the complete pinned template before scoped execution. Preserve full-candidate validation across all active inherited representations.
5. Record actual operations, candidate bytes, evaluator exit codes/scopes/raw output, pair and coverage states, governance blockers, adaptation duration, and separately timed evaluator subprocesses. Do not predeclare an operation or outcome.
6. Preserve the original HOLD, V1 continuation, V2 continuation, and this V3 continuation as distinct records. These repeated executions of one transition are not independent experimental units and support no significance claim.

## Scope and interpretation

The bounded profile covers the two architecture-compliance CI obligations `AC_LAYERING` and `AC_MODULE_STRUCTURE`. It does not include a deployment observation or runtime workload. A0's four active inherited performance/reliability representations still lack exact pinned evaluator artifacts and remain mandatory for full candidate validation. A profile-scoped evaluator pass cannot turn a failed full candidate validation into success.

`Coverage_P` and `Coverage_ref` remain unclaimed unless their separate evidence and denominator requirements are met. The TEST_ONLY applicability states are declared researcher assumptions rather than independent policy authority. Any observed compliance value is limited to the resolved evaluator evidence at that scope; neither a successful process nor a zero metric proves semantic coverage. G1 remains INCOMPLETE, G4 remains NOT AUTHORIZED, and Method P readiness is unchanged. The continuation is DEVELOPMENT research execution; external review can follow its completion.
