# MONO_E1_DEV_P_DECISIONS_V1 — DEVELOPMENT report

## Status and provenance

The synthetic experiment executed through the existing V3 verified-input path under TEST_ONLY trust. It is independent of official MONO-E1 A0.3→A0.4 execution.

- Scenarios: 8; technical Method P repetitions: 24; B0_SYNTH baselines: 8
- Author-declared reference SHA-256: `5dcf0b2784a3fce370d5d3fd097397174025a76b3c8d2396d82423ea0f221bfa`
- Pre-registration source commit: `c7ca08f73fda5473adbe2690ea3dc0a527fee69d`
- Scorer source commit: `03263ecad08112e3f6214650b40762b168ae294b`
- Method version: `P_GOVERNED_ADAPTATION_DEVELOPMENT_V1`
- Reference scope: AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT

## Scoring pipeline correction

The first post-execution scoring attempt failed because it expected an extra nested `result` object that the raw execution records do not contain. This occurred after all 24 Method P calls; it changed no raw records and triggered no Method P rerun. The corrected scorer reverified the raw manifest and all input bundle archives before scoring under commit `03263ecad08112e3f6214650b40762b168ae294b`.

## Observations

| Scenario | Expected op/gov | B0_SYNTH | Differs? | P operation / governance | Reason codes | Correct / incorrect / not evaluable | Unnecessary / missed | Duration min–max (ms) | Evidence completeness | Raw Method P SHA-256 digests |
|---|---|---|---|---|---|---:|---:|---:|---|---|
| A1 | retain / ACCEPT | UNCHANGED_CONFIGURATION | False | retain / ACCEPT, ACCEPT, ACCEPT | none | 3 / 0 / 0 | 0 / 0 | 483.27–489.87 | COMPLETE, COMPLETE, COMPLETE | 450fd2b88e666f308a07de278fa23d705e73862a3698f282ee0f7ad3c44d63ca<br>88b5401e5cb4cb89544fd3641f5a1f0497942700494be9abb8e255bdb5f4d569<br>ca0a58a87fb22b6c95c864d91d20b42f7c446dfeae248b8ea2684f1d58432e88 |
| A2 | retain / ACCEPT | UNCHANGED_CONFIGURATION | False | retain / ACCEPT, ACCEPT, ACCEPT | none | 3 / 0 / 0 | 0 / 0 | 461.24–476.71 | COMPLETE, COMPLETE, COMPLETE | a447f7061713a90007ae392b7d28fd3304953ff082bbb1ff2a6801b4c28e75c3<br>3c0b4eabb93e0035a44b70bcf1d5b14b4375a4e720288fbce8c09d8d6e85f82a<br>adc7f801c69bbd0794ec7ecde18aa1f955557d5ed9945f7f0e219aa6705f4684 |
| B1 | add / ACCEPT | UNCHANGED_CONFIGURATION | True | add / ACCEPT, ACCEPT, ACCEPT | none | 3 / 0 / 0 | 0 / 0 | 450.29–462.13 | INCOMPLETE, INCOMPLETE, INCOMPLETE | 27435e26044f3fdbb04de694a6440e066922d2e13fd7fce800fb2732110cc6f8<br>ebfc5a6f417c4b88deab50d4801e63b9c166a512ec56d3b90cafa5980bc58ba2<br>4e2135dff81a8431c6187c7a7cfd770232639f4fbb01d0662e246e0138fc55f2 |
| B2 | add / ACCEPT | UNCHANGED_CONFIGURATION | True | add / ACCEPT, ACCEPT, ACCEPT | none | 3 / 0 / 0 | 0 / 0 | 450.84–461.86 | INCOMPLETE, INCOMPLETE, INCOMPLETE | 6ad8b09ec7188a828b52f6d3e31f15c10586c23ef29a7a53fc657489a391cdfe<br>a2c3f8bc9dc6fb8fcfc367eec37d9144e88f924ded9daa16503ae0925272bc7e<br>024df731429b0b60064e5ada8e42fe196b133b8f445e228d3dc877993fc0bfe7 |
| C1 | replace / ACCEPT | UNCHANGED_CONFIGURATION | True | replace / ACCEPT, ACCEPT, ACCEPT | none | 3 / 0 / 0 | 0 / 0 | 456.22–466.03 | INCOMPLETE, INCOMPLETE, INCOMPLETE | 350da0c218d385c11980f1769b24ba51c85c630b045b5a65158147fec5f4d384<br>b47cd7189ef4d69e9d4e71eee46e9616c07862eb80f857646ef91be56e991ae9<br>602f6ecf324429a5742f1af83f70a35404f514d45ab155e17c837154c3f38eae |
| C2 | replace / ACCEPT | UNCHANGED_CONFIGURATION | True | replace / ACCEPT, ACCEPT, ACCEPT | none | 3 / 0 / 0 | 0 / 0 | 476.83–500.40 | INCOMPLETE, INCOMPLETE, INCOMPLETE | 2e8872e7a71120611259abbe276a1d0061d25f7f9e968ff89beccad316e24579<br>1271e34aac278e37f7b60e043e20643a1b9418787090d2e6e0c2df6bc4c80cda<br>fb4794e050473361514bd3743f9e83f468858ef31c5269c84dcea1c492aea0e9 |
| D1 | hold / HOLD | UNCHANGED_CONFIGURATION | False | hold / HOLD, HOLD, HOLD | CANDIDATE_NOT_POSITIVELY_VALIDATED, COST_MODEL_UNRESOLVED, COST_VERDICT_UNRESOLVED, INPUT_AUTHORITY_OR_COMPLETENESS_UNRESOLVED, INVARIANT_VERDICTS_NOT_ALL_POSITIVE, MANDATORY_APPLICABILITY_UNKNOWN, MANDATORY_CLASSIFICATION_UNRESOLVED, UNKNOWN_MANDATORY_LINK_PREVENTS_TRANSITION, VERIFIED_GOVERNANCE_PIPELINE_PROOF_MISSING | 3 / 0 / 0 | 0 / 0 | 369.34–376.07 | UNKNOWN, UNKNOWN, UNKNOWN | a099e7d70bcb9aeba84e8c2fc41d9aad14aa68f9ccfcddffffef304aa582d463<br>0ed318d808997fba9af91d40c08f27313e5a6a43816108328df5bf0d53f30ccf<br>d2119c12b18cb1254ceb94153e8b70f2bad3cc98fa4a86ad6e4cb708d002859c |
| D2 | hold / HOLD | UNCHANGED_CONFIGURATION | False | hold / REJECT, REJECT, REJECT | ACTIVE_MANDATORY_CONTROL_UNCOVERED, INVARIANT_VIOLATION_PROVEN, MATERIALIZABLE_TEMPLATE_MISSING, REPLACEMENT_NOT_MATERIALIZABLE | 0 / 3 / 0 | 0 / 0 | 420.72–438.70 | INCOMPLETE, INCOMPLETE, INCOMPLETE | 59b6e2e187fc22a1cfde5bdefc4a741527b768808900305f39c7acfe4e80d0f6<br>5a8bd6475602a09169523d3b7551a7f1d3d327a1a11e2f13bf8681db936bbf32<br>3fe343901893f51e0b5adc851f6cbf51bf4391501b0863169ba2ebc7c0db16f5 |

## Aggregate descriptive metrics

- Correct / incorrect / not evaluable: 21 / 3 / 0 of 24 technical repetitions.
- Operation decision accuracy: 24 / 24 = 1.0 (execution failures: 0).
- Combined operation/governance/semantic accuracy: 21 / 24 = 0.875 (not evaluable: 0).
- Unnecessary adaptation: 0 / 12 = 0.0.
- Missed required adaptation: 0 / 12 = 0.0.
- HOLD outcomes: governance HOLD=3; appropriate HOLD operation=3; inappropriate HOLD=0; missed expected HOLD=0; HOLD operation with registered-governance mismatch=3.
- Execution failures: 0.
- Repetition decision stability: 8 / 8 scenarios had identical operation, governance, plan digest, and candidate digest across technical repetitions.
- Operation confusion matrix (rows are author-declared expected operations):

```json
{
  "add": {
    "add": 6
  },
  "hold": {
    "hold": 6
  },
  "replace": {
    "replace": 6
  },
  "retain": {
    "retain": 6
  }
}
```
- Execution duration by observed operation (nanoseconds):

```json
{
  "add": {
    "count": 6,
    "max": 462127791,
    "mean": 454897805.3333333,
    "min": 450285500
  },
  "hold": {
    "count": 6,
    "max": 438698250,
    "mean": 400109118.0,
    "min": 369337250
  },
  "replace": {
    "count": 6,
    "max": 500404792,
    "mean": 473592395.8333333,
    "min": 456216708
  },
  "retain": {
    "count": 6,
    "max": 489866958,
    "mean": 477003090.1666667,
    "min": 461241416
  }
}
```

## B0_SYNTH comparison

B0_SYNTH preserved each initial representation catalog and recorded the current after-state coverage assessment without semantic adaptation. Its operation is `UNCHANGED_CONFIGURATION`; it is not an official or historical B0. Method P proposals, governance outcomes, candidate validation, and coverage remain separate in `results_v1.json` and the raw traces.
Scenarios with a Method P configuration-change proposal relative to B0_SYNTH: B1, B2, C1, C2

## Reproduction and evidence

Run `execute` from the clean pre-registration commit, then run `score` on the resulting directory. `execute` never reads the reference. Scoring checks the frozen reference digest and every raw record, then writes the descriptive results.

See `execution_manifest.json`, `raw_records_manifest.json`, `results_v1.json`, `raw/`, and `SHA256SUMS` for input, implementation, output and checksum evidence.

## Limitations and next step

All policy, evaluator, and exact-pair trust is synthetic TEST_ONLY evidence. Repeated runs reuse each scenario fixture and do not increase the independent sample count. Author-declared decisions are not independently validated labels. This experiment does not change P readiness, G1/G4, MONO-E1 `NO_GO`, or any DA01 authority.

The next official MONO-E1 step remains resolving and documenting the reference-freeze gate, independent evaluator/source evidence, G1 completeness, and separate G4 authorization before any canonical B0/P execution.
