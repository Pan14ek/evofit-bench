# Context — synthetic Method P fixtures

> **Audience:** maintainers of independent development tests. **Type:** test data documentation, not architecture evidence, policy authority, protocol input, or experiment output.

## Responsibility

Hold small, independently-authored generic examples for SPEC 03 unit and integration tests.

## Boundaries

- All identities and values are synthetic and marked TEST_ONLY.
- Fixture expectations come from SPEC 03 contracts, not DA01 expected operations or ground truth.
- Do not add private oracle, scorer, scenario-answer, or measured experiment data here.

## Verification

Tests hash the fixture bytes and exercise deterministic parsing and decision behavior. These tests are engineering evidence only and do not authorize G1 or G4.
