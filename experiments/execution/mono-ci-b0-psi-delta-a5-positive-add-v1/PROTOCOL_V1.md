# Controlled positive ADD experiment for ΔA5 — V1

## Purpose

Test whether the existing, unchanged Method Ψ can emit a genuine `ADD` on the fixed A0.4→A0.5 transition when its otherwise unresolved TEST_ONLY inputs are supplied for one author-selected obligation. The control is the archived V2 run `DEV_PSI_TRANSITION_OADEV_V2_DELTA_A5_20261027_MEASURED_01`; it is reused as C0 and is not rerun. The verified release archive SHA-256 is `ef44cf280807e414b4027d846a8db05de74b555c60803500a97d074b666db0d2`; its measured inner transition archive is `76024640bf1a5bfc8771f91a7c9c113c7486f44e28f6290b56dafb32867ae890`, bound to source revision `a349d19fb89b577e6799e9736ed4ce0acc572166`.

This is a research-owner-authorized exploratory DEVELOPMENT study. Its positive declarations are authored and verified inside a TEST_ONLY scope. They are not independent evidence, production policy approval, measured DA01 results, G1 completion, or G4 authorization. The P implementation, operation planner, candidate materializer, governance, frozen V2 evidence, canonical 18-row catalog, official checks, and A0.4/A0.5 source states remain unchanged. The cost source is the V2 release's own `analysis/evaluator-samples.csv` (SHA-256 `2bbff33702491cd0238271fa4c718316378586f5f7eb6af0271cf7baef25e7a7`), not a later checked-in post-run analysis copy.

## Fixed inputs

- Before/after: the exact A0.4 and A0.5 commits, trees, manifests and reconstructed B0 proposal already pinned by the ΔA5 runner.
- B0 controls: `AC_PUBLIC_API` and `AC_MODULE_GRAPH`.
- Added evaluator: existing A1 `AC_DATA_OWNERSHIP`, with its source manifest and `data_ownership_v1.yaml` bytes bound by SHA-256.
- Positive profile: only `AC_DATA_OWNERSHIP` is declared applicable and mandatory in the selected application scope. The author’s rationale is the A0.5 manifest’s declared `persistence_ownership` section. A test-only closure claims are state-specific and obligation-specific. All other canonical obligations remain `UNKNOWN`; the schema-required false values in the mandatory projection mean outside this study’s mandatory scope only.
- Stage: the study label is `CI_TEST`; the unchanged evidence contract’s exact token is `ci_test`.
- Candidate descriptor: one generic evaluator template for `AC_DATA_OWNERSHIP`; Ψ chooses whether to use it. No operation, candidate, oracle label, expected result, or score is injected.
- Evidence: three actual evaluator outputs and exact-pair validity declarations are author-selected TEST_ONLY inputs. Candidate evaluation uses actual evaluator execution and occurs only when Ψ emits a candidate.

## Cost and search bounds

The cost unit is elapsed wall-clock milliseconds per added evaluator invocation. The V2 release's `analysis/evaluator-samples.csv` has SHA-256 `2bbff33702491cd0238271fa4c718316378586f5f7eb6af0271cf7baef25e7a7`. Use the 10 measured clean `AC_DATA_OWNERSHIP` calls on source commit `a349d19fb89b577e6799e9736ed4ce0acc572166` and 10 measured calls on the existing negative probe commit `5ace86095bda794c9576047c80b9267e70cd0f26`; exclude warmups. The release's `probe-replay.json` and execution record bind the negative-probe commit. The observed maximum is 177.215 ms. Apply a fixed 25% margin (221.519 ms), then round upward to the next 25 ms: `max_incremental_cost=225`. Bind the cost to the candidate evaluator source-manifest SHA-256. Use `max_search_nodes=2`, the root and one leaf needed for the single-template search. Freeze both values before C1 and do not tune them after observing a result.

Sensitivity values are rounded upward to the next integer millisecond from the same maximum: no margin = 178 ms, 25% = 222 ms, and 50% = 266 ms. The fixed budget admits the 0% and 25% sensitivity cases, and rejects 50%. This is a bounded TEST_ONLY estimate, not a measured cost model for production.

## Execution plan

1. Run focused contract and negative tests and `make development-quality` on the implementation commit.
2. On the same hosted runner, capture the Docker isolation preflight. Stop before any calibration or transition if it fails.
3. Write a pre-run freeze binding the implementation commit, protocol/profile, V2 receipt and timing CSV, evaluator source/configuration, source states, baseline, exact Docker image/platform, host identity, preflight digest, repetition count, cost model, and search budget.
4. Execute one uncounted warmup and three measured technical repetitions. Every transition uses the existing Docker-isolated Ψ runtime with a read-only method bundle, no network, no credentials, and a single writable output mount.
5. Per C1 repetition, record source-pinned B0 controls, the clean A1 ownership evaluation used as the positive input, the unchanged Ψ result, and—only if Ψ emits a candidate—the materialized candidate plus actual clean and existing negative-probe evaluations. Preserve every raw result, process stream, digest, partial failure and archive.
6. Compare C0 and C1 descriptively. Report raw technical repetitions individually. Do not calculate significance, sensitivity/specificity, a coverage percentage, or a global obligation denominator.
7. Create a deterministic outer archive, verify its SHA-256 sidecar, extract it to a new directory, and replay all member, run, method-input and evaluator bindings before release publication.

## Stop and interpretation rules

Any failed preflight, source binding, evaluator scope readback, input validation, isolation check, archive verification, or time/search budget stops that phase and retains partial raw evidence. Infrastructure failure is not Ψ HOLD. Preserve Ψ HOLD or REJECT exactly. A successful `ADD` is reported only if the unchanged method emits the operation, the candidate configuration is actually materialized and validated, and the candidate evaluator is exercised. No candidate is applied to application code.

Official gates stay `P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, `G4=NOT_AUTHORIZED`, reference `NOT_READY`, scoring `NOT_EXECUTED`, and study `NO_GO`.
