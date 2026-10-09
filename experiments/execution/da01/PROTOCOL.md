# DA01 execution protocol — Phase A

**Protocol:** `DA01_EXECUTION_PROTOCOL`, version `1.0.0`

**State:** prepared for independent methodological review

**Boundary:** synthetic cases only; no measured DA01 B0/B1/P execution.

## Research scope

RQ1 scores affected-target identification and operation selection. RQ2 scores
valid coverage of the complete post-change obligation set and semantic validity
of evaluator representations. One architecture delta is one research unit;
its targets, requests, or log rows are not independent architecture samples.
DA01 cannot support runtime-performance, reliability-improvement, or population
significance claims.

The original architecture tag is `arch-a0-monolith-v1`, resolving to
`b78b0967be937634b7762baccf5ac6892b279a73`. The reviewed target candidate used by
the preparation tooling is `5231a637d1489f83d4c17649c235a6ce2a2f40ac`. The target
is recorded as an explicit SHA; this tooling does not create or move architecture
tags. The frozen A0 evaluator is retained as an experiment input. Engineering
acceptance under `architecture/acceptance/` is not a B0 evaluator or a method
answer source.

## Review gates

| Gate | Required evidence | Phase A status |
| --- | --- | --- |
| G0 — architecture freeze | Frozen A0 tag unchanged; explicit target SHA; app source untouched | Reviewed and recorded; no final architecture tag created |
| G1 — protocol freeze | Scoring, B1 checklist, missing-data rules, validity predicates, and P algorithm frozen | Partial; P algorithm and independent sign-off remain open |
| G2 — isolation audit | Allowlist inspection and negative file/history/network probes | Passed with the digest-pinned local image recorded in `READINESS.md` |
| G3 — synthetic rehearsal | Contract, sealing, scoring, stale/vacuous evaluator, and coverage tests | Passed in repository quality; see `READINESS.md` |
| G4 — measured-run authorization | Explicit human approval after G0–G3 review | Not authorized by this task |

No gate automatically advances to measured execution. A failed or unavailable
shared reference checker is not a method score. Method failures, evaluator
invalidity, missing evidence, infrastructure failures, protocol violations, and
reference-checker errors retain separate status and reason codes.

## Method contracts

### B0

B0 preserves the frozen A0 fitness configuration byte-for-byte. Its prediction
and applied-operation lists are empty. During scoring, omitted existing
representation operations normalize to implicit `retain`; an undiscovered new
obligation normalizes to scorer-only `missing_add`. The old A0 Import Linter is
assessed against the target architecture for scope, applicability, non-vacuity,
and evidence. Exit code zero alone does not establish coverage.

### B1

B1 is a real human procedure using `B1_CHECKLIST.md`, the common architecture
observations, general obligation registry, A0 fitness representations, and the
shared evaluator capability inventory. It does not use P's traceability graph or
impact engine. It must record operator identity/experience, access, prior
knowledge exposure, decision and adaptation time, rationale, uncertainty, and
the complete candidate. No independent human session is represented here; B1 is
**NOT READY** until one is documented. No human answer is fabricated.

### P

P has a versioned, technology-agnostic input/output interface. Its method input
may include the A0 traceability artifact. It must not receive ground truth,
reference scoring, engineering acceptance implementation, another method's
outputs, or the complete DA01 scenario. This repository does not define or
implement the scientific `Impact` model, activation policy, mapping rules,
candidate generation, or governed acceptance/rollback algorithm. Those decisions
need an independently reviewable algorithm specification before a P method can
be called implemented. P is **NOT READY**.

## RQ1 scoring

The scorer reconstructs the universe from the private oracle's existing
representation IDs and new-obligation IDs. Target identity is the pair
`(target_type, target_id)`. Positive means an oracle operation other than
`retain`. `TP`, `FP_in`, `FP_extra`, `FN`, and `TN` are reported separately;
`FP_total = FP_in + FP_extra` enters precision and F1. `TN` covers only in-universe
negative targets. Unknown IDs remain protocol violations and visible extra
decisions.

Operation accuracy uses scorer-normalized operations over the complete oracle
universe. Omitted existing representations become `implicit_retain`; omitted
obligation targets become `missing_add`, which is never an emitted operation.
Duplicate or contradictory decisions invalidate prediction validation. If the
oracle has positive targets but the method predicts none, precision, recall, and
F1 are zero. If both sets are empty in a synthetic negative control, all three
are `null` and correct-empty-set detection is reported separately.

## RQ2 scoring

For each required obligation `q`, coverage is one if at least one active
representation has an independently resolvable mapping to `q`, applies to the
target architecture and stage, is semantically compatible, executes
non-vacuously, and satisfies its evidence contract. Otherwise it is zero.
Coverage is the sum divided by the full active obligation count; the initial
weight is one for every obligation. An obligation is counted once, regardless
of duplicate representations. A representation can support multiple
obligations, each assessed independently.

`Coverage_before` evaluates the unchanged A0 configuration against the target
architecture. `Coverage_after` evaluates a materialized candidate against that
same target. Missing evidence conservatively means not demonstrated as covered,
while the method's failure reason remains separately recorded.

## Prediction sealing and immutability

Predictions are deterministic canonical JSON, written once with exact-byte
SHA-256 and a UTC seal timestamp. Existing prediction or seal paths are never
overwritten. The scorer verifies the hash before use and accepts no prediction
output path. Scoring is a pure transformation from a verified sealed prediction,
oracle input, and independent validity evidence to a separate result object.

## Evidence and timing

Provenance separates architecture source, infrastructure source, method source,
fitness configuration version, and workload profile identity/hash. It records
input bundle file hashes, prediction seal, evaluator raw exit status and output
hashes, evidence references, environment, UTC timestamps, and failure reasons.
Workload profile bytes remain unchanged; their A0 profile name is workload
provenance, not the target architecture label. DA01 does not require canonical
A0 load runs.

Time fields separate diff, impact, decision, candidate, method validation, and
reference validation. B0 adaptation time is zero by definition. B1 requires
actual human wall time. Reference scoring time is excluded from adaptation time.

## Execution stop

Phase A stops after synthetic validation and readiness reporting. No scored DA01
prediction, actual B1 operator decision, or B0/B1/P outcome is produced. Any later
measured run requires a separate explicit authorization after methodological
review.
