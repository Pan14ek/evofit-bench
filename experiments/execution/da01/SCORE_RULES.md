# Scoring rules

## RQ1 impact and operations

Target identity is `(target_type, target_id)`. The scorer rebuilds the complete
classification universe from private ground truth. An oracle operation other
than `retain` is positive. It reports TP, FP within the universe, FP outside it,
FN, and TN; `FP_total = FP_in + FP_extra` is used for primary precision and F1.
TN counts only in-universe oracle negatives. Unknown targets remain visible as
extra decisions and protocol violations.

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
DA01 oracle that set has six obligations. An
obligation is counted once if at least one active representation has valid
independent semantic evidence for it. Multiple representations for one
obligation do not add weight; one representation may cover multiple obligations,
each tested independently. Coverage is in `[0, 1]`; an empty denominator is a
contract error. `Coverage_before` evaluates the unchanged A0 candidate against
the after architecture. `Coverage_after` evaluates the candidate against the
same architecture.

The report includes uncovered obligations, stale/invalid representations,
violation counts by category, their denominator (active assessed
representations), and the coverage delta. Missing evidence is not covered.

## Failure preservation

Method failure, evaluator invalidity, missing evidence, infrastructure failure,
protocol violation, and reference-checker error are distinct statuses. No
post-hoc dropping or imputation is done by the scorer. A single DA01 delta is
reported descriptively; no target-level significance test is valid.
