# Scoring rules

## RQ1 impact and operations

Target identity is `(target_type, target_id)`. The scorer rebuilds the complete
classification universe from private ground truth. An oracle operation other
than `retain` is positive. It reports TP, FP within the universe, FP outside it,
FN, and TN; `FP_total = FP_in + FP_extra` is used for primary precision and F1.
TN counts only in-universe oracle negatives.

The scorer resolves target identities from the representation catalog and
general obligation registry pinned by the prediction's architecture source SHA.
A known target outside the scenario universe remains an ordinary `FP_extra`; a
target absent from the pinned registries remains an `FP_extra` and adds
`UNKNOWN_TARGET`. The sealed result derives `PROTOCOL_VIOLATION` from that
diagnostic even when no failure status was supplied by the caller. The trusted
registry is mandatory; scoring fails if either pinned artifact cannot be loaded
or verified.

Precision is `TP / (TP + FP_total)`, recall is `TP / (TP + FN)`, and F1 is
`2*TP / (2*TP + FP_total + FN)`. If the oracle has positives and the method
predicts none, all three are zero. If both positive sets are empty, all are null
and correct-empty-set detection is reported separately.

Operation accuracy compares scorer-normalized decisions over every target in
the oracle universe. Omitted existing representations become `implicit_retain`;
omitted obligation targets become scorer-only `missing_add`. `missing_add` is not
a valid emitted operation. Operation accuracy does not imply candidate validity
or coverage.

## RQ2 obligation coverage

The equal-weight denominator is the complete required obligation set loaded
from the private oracle's `required_obligations_after` field. For the frozen
DA01 oracle that set has six obligations. An obligation is counted once if at
least one active representation has a valid versioned
`obligation_verdict.schema.json` record for that exact
`(representation_id, obligation_id)` pair, alongside a valid representation
execution verdict. Membership in `representation.covers` and a general
`VALID_APPLICABLE` verdict do not establish pair validity. Every pair needs its
own semantic match, adequate evidence contract, evidence references, and the
same target architecture SHA. Missing pair records are `MISSING_EVIDENCE`.
Multiple representations for one obligation do not add weight; one
representation may cover multiple obligations only when each pair is valid.
Coverage is in `[0, 1]`; an empty denominator is a contract error.
`Coverage_before` evaluates the unchanged A0 candidate against the after
architecture. `Coverage_after` evaluates the candidate against the same
architecture and complete private obligation set.

The version 2 coverage assessment identifies every considered pair, its status,
reason codes, architecture SHA, and evidence references; `valid_cover_pairs`
provides the trace for each covered obligation. `invalid_representations` means
active representations whose evaluator-execution verdict is invalid or absent.
A failed obligation pair does not make the representation globally invalid if
its execution verdict is valid for another obligation. The existing
`semantic_violation_denominator` remains the number of active assessed
representations; pair failures are shown in pair assessments and do not change
that metric. Missing evidence is not covered.

The execution coverage schema is version 2, and the explicit pair verdict
contract is version 1. The scorer envelope remains version 1, and
`experiments/schemas/result.schema.json` is unchanged.

## Failure preservation

Method failure, evaluator invalidity, missing evidence, infrastructure failure,
protocol violation, and reference-checker error are distinct statuses. No
post-hoc dropping or imputation is done by the scorer. A single DA01 delta is
reported descriptively; no target-level significance test is valid.
