# Independent semantic-validity rules

The validity checker is separate from method execution and prediction scoring.
It consumes a candidate representation contract and raw evaluator evidence; it
does not repair a candidate or infer validity from its exit code.

## Valid coverage predicate

For representation `r`, obligation `q`, target architecture `A`, and evidence
`E`, the checker returns valid coverage only when all of these hold:

```text
Active(r)
AND MapsTo(r, q)
AND StageApplicable(r, A)
AND SemanticCompatible(r, q, A)
AND ExecutableAndNonVacuous(r, A)
AND EvidenceContractSatisfied(r, E)
```

The result distinguishes `VALID_APPLICABLE`, `SEMANTIC_MISMATCH`,
`STALE_ARCHITECTURE_SCOPE`, `MISSING_ARCHITECTURE_TARGET`, `VACUOUS_SUCCESS`,
`MISSING_EVIDENCE`, `EXECUTION_FAILURE`, `INFRASTRUCTURE_FAILURE`,
`STAGE_OR_CONTEXT_MISMATCH`, and `OBLIGATION_MAPPING_MISMATCH`. A reference-checker
error or protocol violation is recorded separately and cannot be scored as
method success.

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

## Coverage rules

Coverage is computed at obligation level. A representation contributes only when
its independent verdict is `VALID_APPLICABLE`, its declared `covers` mapping
includes that obligation, and the evidence contract is satisfied. Duplicate
representations do not multiply an obligation. Each obligation mapped from one
representation is assessed independently. Missing evidence is not demonstrated
coverage, while its method/infrastructure failure status remains visible.

The exact DA01 obligation-to-validity matrix and any candidate acceptance rules
must be approved in the G1 methodological review before measured trials.
