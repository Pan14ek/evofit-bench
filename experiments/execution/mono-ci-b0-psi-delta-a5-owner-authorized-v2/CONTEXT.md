# Context — owner-authorized ΔA5 DEVELOPMENT V2

> **Audience:** human developers and AI coding agents. **Type:** local descriptive context; not policy approval, independent validation, or authorization for official measurement.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/CONTEXT.md` before this directory.

## Responsibility

Version the narrow PR #58 execution corrections, freeze a hosted sandbox identity before measurement, and retain complete or partial evidence for the same A0.4→A0.5 DEVELOPMENT transition.

## Local landmarks

- `PROTOCOL_V2.md` / `PROTOCOL_V2.json` — owner-authorized exploratory scope and measurement rules.
- `PRE_RUN_SANDBOX_PREFLIGHT.json` — raw successful pre-run hosted capability check used to prepare the freeze.
- `pre-run-preflight/` — preserved canary inputs, outputs, and raw streams bound into the implementation freeze.
- `PRE_RUN_FREEZE.json` — created only after the hosted preflight and exact V2 implementation are fixed.
- `PREMEASUREMENT_FAILURE_40569757224.json` and `PREMEASUREMENT_PREFLIGHT_ARTIFACT_40569757224.zip` — preserved first V2 run failure; technical preflight stopped before calibration or transitions, and the recorded SHA-256 binds the raw GitHub artifact.
- `POSTEXECUTION_READBACK_FAILURE_40574090499.json` and `PRE_RUN_FREEZE_40574090499.json` — separately preserve the first fully measured V2 attempt, its post-method wrapper readback defect, actual archived Ψ HOLD/candidate observations, and the exact prior freeze.
- `analysis/` — supplemental post-run corrected analysis and Ukrainian insertion map, derived from the byte-verified V2 release without changing its raw archives or original analysis.
- `evidence/` — post-run receipts and checksums; the durable raw bundle is also published as a GitHub release.

## Execution boundaries

`mono_ci_psi_owner_authorized_v2.py` delegates to the existing A0.5 adapter, evaluator, and archive verifier. It reads `development_run.json` after execution because that persisted record contains evaluator observations omitted by the compact adapter return. Its Method Ψ subprocess uses a digest-pinned Python container with `--network none`, read-only input mounts, one dedicated writable output mount, no credentials, no Docker socket, dropped capabilities, and a non-root UID. The V2 preflight proves those properties with a reachable control canary, a denied sandbox canary, protected-file probes, runtime identity, and an output write.

The workflow repeats this freeze-checked preflight on the same hosted runner that executes calibration and transitions; that measurement-runner record is copied into the study bundle.

Partial executions use the separate `PARTIAL_EXECUTION_EVIDENCE` archive contract. Analysis reads that archive's top-level manifest when a raw `partial-execution.json` is absent and recovers actual method and candidate-validation observations from the checksum-verified member set. The full V4 transition archive verifier remains unchanged. V1 protocol, measurements, archives, and post-run readback are historical and immutable.

## Validation

Run `make test-mono-ci-psi-owner-authorized`, `make test-mono-ci-psi-owner-authorized-v2`, and the related transition/evaluator targets before freezing. Run `make development-quality` on the implementation commit. Only the exact freeze commit may launch the V2 measurements; a failed hosted preflight stops before calibration or transition attempts.

## Known limits

The protocol is exploratory DEVELOPMENT. G1 remains INCOMPLETE, G4 remains NOT AUTHORIZED, applicability and semantic validity remain unresolved, and technical repetitions do not represent independent architecture transitions. A digest-verified archive establishes byte integrity, not scientific authority or correctness. The first post-measurement V2 attempt remains a wrapper failure despite genuine archived HOLD results; a new freeze is required for the corrected retry. Its published checksum sidecar used a runner-temporary absolute path; the retry uses a portable archive basename and checks the downloaded bytes.
