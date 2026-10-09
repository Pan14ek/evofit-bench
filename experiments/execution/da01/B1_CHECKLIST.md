# B1 manual adaptation checklist

**Checklist version:** `B1_MANUAL_ADAPTATION_V1`

**Status:** protocol template only; no operator decision has been recorded.

Use only the separately exported B1 input bundle. Do not open the repository
checkout, scenario definition, ground truth, validation report, engineering
acceptance implementation, scorer output, P traceability model, or another
method's files. The checklist does not contain DA01 expected answers.

## Operator record

- Operator pseudonym/ID:
- Architecture and fitness-engineering experience:
- Prior exposure to this architecture delta or its expected adaptation:
- Independent of P method development and results (yes/no, with rationale):
- Blind to reference answers before prediction sealing (yes/no):
- Authorized input bundle SHA-256:
- Start time (UTC):
- End time (UTC):
- Adaptation time (minutes):
- Tools and evaluator capability inventory used:
- Access or protocol deviations:

If an independent operator cannot be named and their prior knowledge recorded,
mark the B1 execution **NOT READY**. Do not substitute a simulated answer.

## Decision procedure

1. Inspect the before/after architecture source and structural diff. Record the
   architectural mechanisms that changed, with file/observation references.
2. Review each existing fitness representation, its criterion, stage, evaluator,
   intended semantics, coverage mapping, and evidence contract.
3. For each existing representation, choose `retain`, `replace`, `deactivate`,
   or `adjust`. Record a reason and uncertainty. Do not mark a representation
   affected without a proposed operation.
4. Inspect the complete general obligation registry. Determine which obligations
   apply to the target architecture from the authorized observations. Do not use
   a scenario-specific new-obligation list.
5. For each discovered obligation without an adequate representation, propose an
   `add` operation and identify a stable representation ID, evaluator artifact,
   stage, semantic mapping, applicability scope, and evidence contract.
6. Check evaluator compatibility using only the shared capability inventory and
   generic templates. Record resolved targets, inspected subjects, raw exit
   status, evidence hashes, and any limitation. Do not copy a prepared reference
   checker.
7. Validate the complete candidate configuration. Preserve a failed candidate
   and rollback rationale if validation fails.
8. Seal the prediction and candidate hashes before any independent scoring.
   Record prediction time, candidate-construction time, validation time, total
   adaptation time, rationale, and remaining uncertainty.

## Decision record (one row per explicit decision)

| Target type | Target ID | Operation | Rationale/evidence reference | Uncertainty |
| --- | --- | --- | --- | --- |
| | | | | |

## Candidate and evidence record

- Candidate configuration version and SHA-256:
- Evaluator artifact paths and SHA-256 values:
- Per-representation coverage mapping:
- Applicability and semantic checks performed:
- Raw stdout/stderr paths and hashes:
- Candidate self-validation result:
- Rollback/failure record, if any:
- Deviations and unresolved questions:

This checklist is a reproducible procedure, not a B1 result. B1 remains
**NOT READY** until a genuinely independent human operator performs and seals it.
