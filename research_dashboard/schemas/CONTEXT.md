# Context — research_dashboard/schemas

> Dashboard reader contracts only. These schemas do not replace or amend experiment schemas.

## Responsibility

Validate the subset and structural shape of corrected, scored experiment results consumed by the read-only dashboard.

## Landmarks

- results_v2.schema.json — corrected PR #48 result reader contract, schema version 2.

## Constraints

Do not use this schema to modify frozen results, scorer rules, scenario inputs, or scientific protocol contracts. The loader also checks record counts, finite numbers, identifiers, and source digests.

## Verification

Run make test-research-dashboard.
