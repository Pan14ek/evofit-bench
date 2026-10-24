# MONO_E1_DEV_P_DECISIONS_V1

This is a synthetic TEST_ONLY DEVELOPMENT experiment of Method P decision behavior. It is separate from the official MONO-E1 B0/P execution and does not amend DA01, MONO-A1, G1, G4, `P_ALGORITHM_STATUS`, or the MONO-E1 `NO_GO` state.

`scenarios_v1.json` contains eight distinct before/after synthetic transitions, initial representation states, obligation applicability assumptions, evaluator/template availability, and evidence modes. It contains no expected operations. `reference_v1.json` is scorer-side only and declares `AUTHOR_DECLARED / DEVELOPMENT / NON_INDEPENDENT` expectations before the first execution. Its bytes are sealed by `reference_v1.sha256` and the pre-registration commit SHA recorded in the report.

The runner imports the repository's existing SPEC 03 TEST_ONLY integration fixture builder, then independently calls `verify_v3_p_bundle()` and `run_adaptation()` for each technical repetition. It does not create a `VerifiedPBundle` itself. Positive evidence is produced by a synthetic evaluator process and signed under the integration fixture's fixed TEST_ONLY key. The exact verified input bundle is preserved as a deterministic ZIP archive and re-verified during scoring. No P decision logic or authority contracts are weakened.

Each scenario is executed three times with the same synthetic input. These are technical repetitions, not independent architecture-evolution samples. `B0_SYNTH` preserves the initial representation configuration and records the same after-state current-coverage assessment separately from P's candidate decision. It is not historical A0 B0, official MONO-E1 B0, or `B0_DEV_A03`.

The scorer reads the frozen reference only after every raw run record exists. Method P inputs are copied from the verified V3 bundle and contain no scenario ID, reference file, or expected operation. Raw execution output records source and bundle digests, operation plans, candidates, governance and reason codes, current/candidate coverage, elapsed time, and any validation failure. The scorer reports operation accuracy separately from the combined operation/governance/semantic classification, and reports false adaptation and missed adaptation rates using their applicable reference groups as denominators.

Reproduce in two phases:

```bash
uv run python -m experiments.pilots.mono_e1_dev_p_decisions_v1.runner execute --output-dir experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1
uv run python -m experiments.pilots.mono_e1_dev_p_decisions_v1.runner score --output-dir experiments/pilots/mono_e1_dev_p_decisions_v1/run_v1
```

The output directory must not exist for `execute`. Scoring verifies the reference digest and all raw-record digests before writing results. Generated results are committed separately after the pre-registration-only commit.

## Interpretation boundaries

- TEST_ONLY policy and pair proofs are synthetic assumptions, not independent semantic approval.
- Governance ACCEPT, proposed operations, candidate validation, and semantic coverage are reported separately.
- Descriptive rates and timing do not establish statistical significance, generalizable superiority, `Coverage_P`, `Coverage_ref`, DA01 results, or scientific readiness.
- `UNKNOWN`, HOLD, validation failures, and stale evidence remain explicit outcomes.
