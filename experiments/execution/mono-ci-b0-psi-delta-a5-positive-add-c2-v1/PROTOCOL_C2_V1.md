# C2 protocol V1 — TEST_ONLY bounded retain reassessment with positive ADD

## Purpose and classification

C2 tests the existing A0.4→A0.5 transition under an explicitly author-declared TEST_ONLY applicability condition. It makes the two existing A0.5 controls `AC_PUBLIC_API` and `AC_MODULE_GRAPH` active mandatory rows so the unchanged Method Ψ can emit bounded RETAIN assessments from source-bound pair evidence, while `AC_DATA_OWNERSHIP` remains the single candidate ADD target. This is a diagnostic condition, not an approved policy or independent semantic authority.

## Frozen inputs and method

- Architecture pair: A0.4 `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` → the C2 run's clean implementation commit; the application tree must remain `007196f68652bc13f6798805793ffdfae96f95f7`.
- Method: `P_GOVERNED_ADAPTATION_DEVELOPMENT_V1`, unchanged source and operation/governance code, executed in the existing digest-pinned `python:3.12.15-slim-bookworm` image, `linux/amd64`, with network disabled, read-only method inputs, and one writable output mount.
- The exact C2 profile, this protocol, evaluator source/configuration digests, Method Ψ plus runner and archive-verifier source digests, schema digests, Docker identity, preflight, and cost limits are written to `PRE_RUN_FREEZE_C2.json` before the first transition execution. Each archived run then binds its exact generated method-input bundle and evidence digests before and after the isolated Ψ call.
- The profile's retain basis is the original C1 archive: both exact pairs were `VALID` in TEST_ONLY scope; source observations were `COMPLIANT`, process exit 0, complete inspection, and bound to configuration digests `8853c3a933b23f698c7ba7c5b6e511f292e8d9285dc0de4378741c53e466f7bb` (public API) and `1abae6871a477ff2a07685ad645a70defa2f1ac6745598ae4cdc35aab4e95bf6` (module graph). C2 repeats those evaluators; C1 evidence is historical support and is not reused as a C2 observation.
- The predeclared cost cap is 225 ms per added ownership-evaluator invocation, with two search nodes. It is derived from the pinned V2 evaluator timing source and applies to incremental `AC_DATA_OWNERSHIP` invocations only; already active public API/module graph evaluators are baseline controls.

## Conditions and measurements

One warmup is excluded and three measured technical repetitions are retained. Each repetition records the actual operation plan, final governance decision and reasons, candidate validation and acceptance status, whether an accepted configuration was applied, clean and ownership-negative evaluator outcomes, incremental ownership evaluator cost on both conditions, Method Ψ time, and full transition time. Full transition time is measured from immediately before the existing A0.5 adapter call until it returns, including evaluator execution and candidate validation/exercise but excluding archive packaging and readback.

Candidate evaluator exercise is not governance acceptance. If Ψ returns HOLD or REJECT, retain that result and its reasons; the candidate remains unapplied. If Ψ returns ACCEPT, apply only that accepted configuration in the isolated experimental workspace and record the application result. No source application code is changed by this study.

## Stop rules and interpretation

Stop after a failed preflight or the first failed transition; preserve all partial raw evidence and do not replace a failed repetition. Do not force ACCEPT or alter the method, evaluators, C0/C1 artifacts, official gates, or frozen contracts. Repetitions are technical repeats of one architecture transition, not independent experimental units.

C2 does not establish independent semantic adequacy, policy authority, DA01 readiness, G1/G4, generalized effectiveness, or statistical superiority. Remaining UNKNOWN policy scope or invariant proof must continue to produce the method's actual decision.
