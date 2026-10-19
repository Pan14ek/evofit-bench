# PILOT-02 DEVELOPMENT addendum V4

**Status:** prospective TEST_ONLY development continuation; not a DA01 protocol change.

**Purpose:** align the PILOT-02 trace's EXP-02 execution-evidence admission status with the verified sidecar actually passed to the existing Method P path. The V2 applicability assumptions and bounded A0 → A0.1 profile are unchanged.

## Reason for V4

The preserved V3 trace contains both `exp02_evidence_admitted_to_p_calculations=true` and `exp02_evidence_admission_status=not_admitted`. Source inspection established why: PILOT-02 passes a digest-bound TEST_ONLY sidecar to `run_adaptation()`, and `p_adaptation.py` verifies that sidecar and uses its evaluator records in exact-pair assessment and operation planning, while the shared EXP-03 trace serializer defaults both admission fields to `not_admitted` because the EXP-03 bridge itself supplies no sidecar.

V4 corrects the PILOT-02 trace wrapper: it reports `admitted_execution_evidence` only when a sidecar was supplied and the returned Method P result confirms `TEST_ONLY` trust scope. Otherwise it reports `not_admitted`. The separate semantic-proof field remains false; the admission label refers only to execution observations supplied to P's calculations. V3 raw bytes remain unchanged and are preserved with this versioned explanation.

No adaptation rule, applicability assumption, candidate template, evaluator command, or governance rule changes. No semantic proof is added. This correction changes trace provenance only.

## Prospective execution

Repeat EXP-01 and EXP-02 on a clean committed source revision, then run unchanged B0 and the existing Method P path on that same A0.1 tree. Keep the V2 assumption digest, source-bound profile and policy inputs, TEST_ONLY trust boundary, target obligations, source scope, evaluator versions, and candidate-validation rules. Record the final trace, candidate, evaluator output and timing, and complete integrity checks. Do not predeclare an operation or result.

V4, V3, V2, V1 and the original HOLD record are executions or corrections on one architecture transition, not independent experimental units. Do not derive statistical significance from these repeated records.

## Interpretation boundary

An `admitted_execution_evidence` status means verified TEST_ONLY execution records were supplied to P's calculation. It does not mean semantic pair proof, valid obligation coverage, independent validation, policy authority, G1/G4 approval, or a measured DA01 result. Pair validity and coverage remain subject to their separate evidence requirements. The A0 four inherited active performance/reliability representations still lack exact pinned evaluator artifacts and block full candidate validation. Any unresolved requirement remains `UNKNOWN` or `HOLD`.
