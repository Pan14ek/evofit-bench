# Independent semantic-validity rules

The validity checker is separate from method execution and prediction scoring.
It consumes a candidate representation contract and raw evaluator evidence; it
does not repair a candidate or infer validity from its exit code. It emits two
separate assessments: representation/evaluator execution validity and an
obligation-specific semantic/evidence verdict.

## Representation and evaluator execution

The version 1 `semantic_verdict.schema.json` record assesses whether evaluator
execution for representation `r` is active, correctly scoped to target
architecture `A`, mapped, stage-applicable, non-vacuous, and supported by
general evaluator evidence. This verdict is an execution prerequisite; it does
not certify every obligation listed in `r.covers`.

It distinguishes `VALID_APPLICABLE`, `SEMANTIC_MISMATCH`,
`STALE_ARCHITECTURE_SCOPE`, `MISSING_ARCHITECTURE_TARGET`, `VACUOUS_SUCCESS`,
`MISSING_EVIDENCE`, `EXECUTION_FAILURE`, `INFRASTRUCTURE_FAILURE`,
`STAGE_OR_CONTEXT_MISMATCH`, and `OBLIGATION_MAPPING_MISMATCH`. A
reference-checker error or protocol violation is recorded separately and
cannot be scored as method success.

## Obligation-specific validity

For each representation `r`, obligation `q`, target architecture `A`, and
obligation-specific evidence `E_q`, the version 1
`obligation_verdict.schema.json` record independently establishes:

```text
ValidRepresentationExecution(r, A)
AND q in r.covers
AND SemanticMatch(r, q, A)
AND EvidenceContractAdequate(r, q, E_q)
AND EvidenceReferencesPresent(r, q, E_q)
```

The pair identity is `(representation_id, obligation_id)`. Each pair record
contains its architecture SHA, semantic-match result, evidence-contract
adequacy, evidence references, status, and reason codes. A missing record is
`MISSING_EVIDENCE`; a general `VALID_APPLICABLE` verdict or evaluator exit code
zero cannot be reused across obligations. The same raw artifact may be cited by
two pair verdicts, but each conclusion and adequacy decision is recorded
separately.

## Evidence and non-vacuity

Evidence records configured/resolved targets, inspected subjects, missing
targets, relevant edges or observations, process exit status, raw output hashes,
and artifact path/hash references. A zero exit with no applicable targets or no
inspected subjects is `VACUOUS_SUCCESS`. A configured target that no longer
resolves is stale/missing scope. A nonzero evaluator exit is an execution
failure; a shared runner outage is an infrastructure failure.

The frozen A0 Import Linter must be parsed and checked for target resolution on
the target source. The checker reports its missing global package targets and
whether any applicable layer subjects were inspected. It is never modified to
make B0 pass. The engineering acceptance configuration is excluded from method
bundles and cannot substitute for the old evaluator.

For architecture evaluator adequacy, clean synthetic structure must pass and a
separate corrupted structure must fail its intended rule. The fixtures live in
temporary directories; frozen application source is not edited. A clean result
alone does not prove sensitivity.

## Coverage reporting

Coverage requires both the representation execution verdict and the explicit
obligation-specific verdict for the exact pair. Duplicate valid
representations do not multiply an obligation. Missing pair evidence is not
demonstrated coverage, while its method/infrastructure failure status remains
visible.

Coverage reports distinguish invalid representations from failed pairs.
`invalid_representations` contains only active representations whose general
execution verdict is invalid or absent. A pair-specific semantic or evidence
failure leaves that list unchanged when evaluator execution itself is valid.
Pair failures are visible in the version 2 coverage assessment and do not alter
the existing active-representation denominator for `semantic_violation_rate`.

The exact DA01 obligation-to-validity matrix and candidate acceptance rules
must be approved in the G1 methodological review before measured trials. The
pair verdict is an explicit Phase A contract, not a trusted reference-run
attestation. The independent evaluator/evidence path remains a deferred G4
requirement.
