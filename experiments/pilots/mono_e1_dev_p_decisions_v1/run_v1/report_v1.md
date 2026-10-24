# MONO_E1_DEV_P_DECISIONS_V1 — DEVELOPMENT report

## Status and provenance

The synthetic experiment executed through the existing V3 verified-input path under TEST_ONLY trust. It is independent of official MONO-E1 A0.3→A0.4 execution.

- Scenario-level outcomes: 8; technical Method P repetitions: 24 (three per scenario); B0_SYNTH derived assessments: 8
- Author-declared reference SHA-256: `5dcf0b2784a3fce370d5d3fd097397174025a76b3c8d2396d82423ea0f221bfa`
- Pre-registration source commit: `c7ca08f73fda5473adbe2690ea3dc0a527fee69d`
- Scorer source commit: `d8a157f6fd93585214210aa364e3a86fb0487fde`
- Method version: `P_GOVERNED_ADAPTATION_DEVELOPMENT_V1`
- Reference scope: AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT
- Three technical repetitions per scenario are not independent cases.

## Scoring pipeline correction

The first post-execution scoring attempt failed because it expected an extra nested `result` object that the raw execution records do not contain. This occurred after all 24 Method P calls; it changed no raw records and triggered no Method P rerun. The corrected scorer reverified the raw manifest and all input bundle archives before scoring under commit `d8a157f6fd93585214210aa364e3a86fb0487fde`.

## Scenario-level outcomes

The following table has one row per distinct scenario. Its counts summarize the three technical repetitions and do not increase the scenario count.

| Scenario | Expected operation / governance | P proposed-operation counts | P governance-result counts | Correct / incorrect / not evaluable | Pre-adaptation coverage statuses | Candidate-configuration coverage statuses | B0_SYNTH derived coverage status | Decision stable across repetitions |
|---|---|---|---|---:|---|---|---|---|
| A1 | retain / ACCEPT | retain: 3 | ACCEPT: 3 | 3 / 0 / 0 | COMPLETE: 3 | COMPLETE: 3 | COMPLETE | True |
| A2 | retain / ACCEPT | retain: 3 | ACCEPT: 3 | 3 / 0 / 0 | COMPLETE: 3 | COMPLETE: 3 | COMPLETE | True |
| B1 | add / ACCEPT | add: 3 | ACCEPT: 3 | 3 / 0 / 0 | INCOMPLETE: 3 | COMPLETE: 3 | INCOMPLETE | True |
| B2 | add / ACCEPT | add: 3 | ACCEPT: 3 | 3 / 0 / 0 | INCOMPLETE: 3 | COMPLETE: 3 | INCOMPLETE | True |
| C1 | replace / ACCEPT | replace: 3 | ACCEPT: 3 | 3 / 0 / 0 | INCOMPLETE: 3 | COMPLETE: 3 | INCOMPLETE | True |
| C2 | replace / ACCEPT | replace: 3 | ACCEPT: 3 | 3 / 0 / 0 | INCOMPLETE: 3 | COMPLETE: 3 | INCOMPLETE | True |
| D1 | hold / HOLD | hold: 3 | HOLD: 3 | 3 / 0 / 0 | UNKNOWN: 3 | UNKNOWN: 3 | UNKNOWN | True |
| D2 | hold / HOLD | hold: 3 | REJECT: 3 | 0 / 3 / 0 | INCOMPLETE: 3 | INCOMPLETE: 3 | INCOMPLETE | True |

## Technical repetition records

Each row below is one recorded Method P technical repetition. Proposed operation, candidate validation, governance acceptance, candidate coverage, and actual post-adaptation coverage are reported as separate observations.

| Scenario / repetition | Expected op / gov | Proposed operation | Candidate configuration SHA-256 | Governance result / accepted | Candidate validation | Pre-adaptation coverage | Candidate-configuration coverage | Actual post-adaptation coverage | Sidecar proofs | Method P current / candidate pair assessments | Raw record SHA-256 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 / 1 | retain / ACCEPT | retain | `f5fc180b6dd2e8ea96cd94619400959234b45f445df3d13e624616289ed62553` | ACCEPT / True | valid | COMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=VALID; candidate=VALID | `450fd2b88e666f308a07de278fa23d705e73862a3698f282ee0f7ad3c44d63ca` |
| A1 / 2 | retain / ACCEPT | retain | `f5fc180b6dd2e8ea96cd94619400959234b45f445df3d13e624616289ed62553` | ACCEPT / True | valid | COMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=VALID; candidate=VALID | `88b5401e5cb4cb89544fd3641f5a1f0497942700494be9abb8e255bdb5f4d569` |
| A1 / 3 | retain / ACCEPT | retain | `f5fc180b6dd2e8ea96cd94619400959234b45f445df3d13e624616289ed62553` | ACCEPT / True | valid | COMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=VALID; candidate=VALID | `ca0a58a87fb22b6c95c864d91d20b42f7c446dfeae248b8ea2684f1d58432e88` |
| A2 / 1 | retain / ACCEPT | retain | `3740e598e02f85f4a72c8306eed6550e9c48dfd8198732f47d585073d1cf6dad` | ACCEPT / True | valid | COMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=VALID; candidate=VALID | `a447f7061713a90007ae392b7d28fd3304953ff082bbb1ff2a6801b4c28e75c3` |
| A2 / 2 | retain / ACCEPT | retain | `3740e598e02f85f4a72c8306eed6550e9c48dfd8198732f47d585073d1cf6dad` | ACCEPT / True | valid | COMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=VALID; candidate=VALID | `3c0b4eabb93e0035a44b70bcf1d5b14b4375a4e720288fbce8c09d8d6e85f82a` |
| A2 / 3 | retain / ACCEPT | retain | `3740e598e02f85f4a72c8306eed6550e9c48dfd8198732f47d585073d1cf6dad` | ACCEPT / True | valid | COMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=VALID; candidate=VALID | `adc7f801c69bbd0794ec7ecde18aa1f955557d5ed9945f7f0e219aa6705f4684` |
| B1 / 1 | add / ACCEPT | add | `34e0883ce0ca62720f8d925d986fc613b91d9ac113fa6b3de6df7c1cddcbadfd` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=no records; candidate=VALID | `27435e26044f3fdbb04de694a6440e066922d2e13fd7fce800fb2732110cc6f8` |
| B1 / 2 | add / ACCEPT | add | `34e0883ce0ca62720f8d925d986fc613b91d9ac113fa6b3de6df7c1cddcbadfd` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=no records; candidate=VALID | `ebfc5a6f417c4b88deab50d4801e63b9c166a512ec56d3b90cafa5980bc58ba2` |
| B1 / 3 | add / ACCEPT | add | `34e0883ce0ca62720f8d925d986fc613b91d9ac113fa6b3de6df7c1cddcbadfd` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=no records; candidate=VALID | `4e2135dff81a8431c6187c7a7cfd770232639f4fbb01d0662e246e0138fc55f2` |
| B2 / 1 | add / ACCEPT | add | `56591e08c3e0b313beb09b21a76a01660e824c0ce2884cc55fe7a4c6319f469e` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=no records; candidate=VALID | `6ad8b09ec7188a828b52f6d3e31f15c10586c23ef29a7a53fc657489a391cdfe` |
| B2 / 2 | add / ACCEPT | add | `56591e08c3e0b313beb09b21a76a01660e824c0ce2884cc55fe7a4c6319f469e` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=no records; candidate=VALID | `a2c3f8bc9dc6fb8fcfc367eec37d9144e88f924ded9daa16503ae0925272bc7e` |
| B2 / 3 | add / ACCEPT | add | `56591e08c3e0b313beb09b21a76a01660e824c0ce2884cc55fe7a4c6319f469e` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=no records; candidate=VALID | `024df731429b0b60064e5ada8e42fe196b133b8f445e228d3dc877993fc0bfe7` |
| C1 / 1 | replace / ACCEPT | replace | `3dea2ef4f26da28a1a4e15e77d588211e4cb012eee65af605bd39070941c9511` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=2; proofs=INVALID, VALID | current=INVALID; candidate=VALID | `350da0c218d385c11980f1769b24ba51c85c630b045b5a65158147fec5f4d384` |
| C1 / 2 | replace / ACCEPT | replace | `3dea2ef4f26da28a1a4e15e77d588211e4cb012eee65af605bd39070941c9511` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=2; proofs=INVALID, VALID | current=INVALID; candidate=VALID | `b47cd7189ef4d69e9d4e71eee46e9616c07862eb80f857646ef91be56e991ae9` |
| C1 / 3 | replace / ACCEPT | replace | `3dea2ef4f26da28a1a4e15e77d588211e4cb012eee65af605bd39070941c9511` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=2; proofs=INVALID, VALID | current=INVALID; candidate=VALID | `602f6ecf324429a5742f1af83f70a35404f514d45ab155e17c837154c3f38eae` |
| C2 / 1 | replace / ACCEPT | replace | `100333b4dfb6011c76882037feea4cbb359a2b4e1e7e754251e78009519f823e` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=2; proofs=INVALID, VALID | current=INVALID; candidate=VALID | `2e8872e7a71120611259abbe276a1d0061d25f7f9e968ff89beccad316e24579` |
| C2 / 2 | replace / ACCEPT | replace | `100333b4dfb6011c76882037feea4cbb359a2b4e1e7e754251e78009519f823e` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=2; proofs=INVALID, VALID | current=INVALID; candidate=VALID | `1271e34aac278e37f7b60e043e20643a1b9418787090d2e6e0c2df6bc4c80cda` |
| C2 / 3 | replace / ACCEPT | replace | `100333b4dfb6011c76882037feea4cbb359a2b4e1e7e754251e78009519f823e` | ACCEPT / True | valid | INCOMPLETE | COMPLETE | NOT_MEASURED | sidecar=present; evaluator records=2; proofs=INVALID, VALID | current=INVALID; candidate=VALID | `fb4794e050473361514bd3743f9e83f468858ef31c5269c84dcea1c492aea0e9` |
| D1 / 1 | hold / HOLD | hold | `62f4056eb6e0ec2f0db11681895239101aa8132501a848bdaf98c68d7547ca53` | HOLD / False | failed | UNKNOWN | UNKNOWN | NOT_MEASURED | sidecar=absent; evaluator records=0; proofs=no records | current=UNKNOWN; candidate=UNKNOWN | `a099e7d70bcb9aeba84e8c2fc41d9aad14aa68f9ccfcddffffef304aa582d463` |
| D1 / 2 | hold / HOLD | hold | `62f4056eb6e0ec2f0db11681895239101aa8132501a848bdaf98c68d7547ca53` | HOLD / False | failed | UNKNOWN | UNKNOWN | NOT_MEASURED | sidecar=absent; evaluator records=0; proofs=no records | current=UNKNOWN; candidate=UNKNOWN | `0ed318d808997fba9af91d40c08f27313e5a6a43816108328df5bf0d53f30ccf` |
| D1 / 3 | hold / HOLD | hold | `62f4056eb6e0ec2f0db11681895239101aa8132501a848bdaf98c68d7547ca53` | HOLD / False | failed | UNKNOWN | UNKNOWN | NOT_MEASURED | sidecar=absent; evaluator records=0; proofs=no records | current=UNKNOWN; candidate=UNKNOWN | `d2119c12b18cb1254ceb94153e8b70f2bad3cc98fa4a86ad6e4cb708d002859c` |
| D2 / 1 | hold / HOLD | hold | `efba3eb16686dc837e469cb6ab09e51938d4e0301f98ed2c1018059a978ebd7b` | REJECT / False | valid | INCOMPLETE | INCOMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=INVALID; candidate=INVALID | `59b6e2e187fc22a1cfde5bdefc4a741527b768808900305f39c7acfe4e80d0f6` |
| D2 / 2 | hold / HOLD | hold | `efba3eb16686dc837e469cb6ab09e51938d4e0301f98ed2c1018059a978ebd7b` | REJECT / False | valid | INCOMPLETE | INCOMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=INVALID; candidate=INVALID | `5a8bd6475602a09169523d3b7551a7f1d3d327a1a11e2f13bf8681db936bbf32` |
| D2 / 3 | hold / HOLD | hold | `efba3eb16686dc837e469cb6ab09e51938d4e0301f98ed2c1018059a978ebd7b` | REJECT / False | valid | INCOMPLETE | INCOMPLETE | NOT_MEASURED | sidecar=present; evaluator records=1; proofs=VALID | current=INVALID; candidate=INVALID | `3fe343901893f51e0b5adc851f6cbf51bf4391501b0863169ba2ebc7c0db16f5` |

D2 preserves the preregistered expected HOLD versus observed REJECT mismatch: the expected operation/governance is `hold` / `HOLD`, while all three technical repetitions report operation `hold` with governance `REJECT`. The scorer retains the original classifications and does not recategorize this observation.

## Coverage and evidence reporting

Pre-adaptation coverage is Method P's `current_coverage`; candidate-configuration coverage is Method P's assessment of the proposed candidate. Candidate coverage does not show that a change was applied. No candidate was applied and re-evaluated, so actual post-adaptation coverage is `NOT_MEASURED`.

An evidence-set completeness verdict is not present in the raw records. The machine-readable inventory preserves the actual sidecar digest and metadata, evaluator evidence records and artifact digests, sidecar pair-proof statuses, evaluator execution records, and Method P current/candidate pair assessments. Coverage status is not used as a proxy for evidence validity or completeness.

## Descriptive metrics across technical repetitions

These pooled counts describe the 24 recorded technical repetitions; the three repetitions within each scenario are not independent samples.

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

B0_SYNTH is a derived unchanged-configuration assessment based on the same verified V3 input and Method P's `current_coverage`. It is not an independently executed baseline arm, and it is not an official or historical B0. The scorer verifies the matching input-bundle digest and equality between the B0_SYNTH coverage object and Method P current-coverage assessment across the three technical repetitions.
Scenarios with a Method P configuration-change proposal relative to this derived unchanged-configuration assessment: B1, B2, C1, C2

## Reproduction and evidence

Run `execute` from the clean pre-registration commit, then run `score` on the resulting directory. `execute` never reads the reference. This report update scores the existing retained records only; it did not rerun Method P. Scoring checks the frozen reference digest, raw-record manifest, and input bundle archives.

See `execution_manifest.json`, `raw_records_manifest.json`, `results_v1.json`, `score_manifest.json`, `raw/`, and `SHA256SUMS` for input, scorer, output, and checksum provenance.

## Limitations and next step

All policy, evaluator, and exact-pair trust is synthetic TEST_ONLY evidence. Repeated runs reuse each scenario fixture and do not increase the independent sample count. Author-declared decisions are not independently validated labels. This experiment does not change P readiness, G1/G4, MONO-E1 `NO_GO`, or any DA01 authority.

The next official MONO-E1 step remains resolving and documenting the reference-freeze gate, independent evaluator/source evidence, G1 completeness, and separate G4 authorization before any canonical B0/P execution.
