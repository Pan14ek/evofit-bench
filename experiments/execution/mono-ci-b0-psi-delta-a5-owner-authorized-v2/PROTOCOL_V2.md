# Owner-authorized ΔA5 DEVELOPMENT protocol V2

## Purpose and classification

Study `MONO_CI_B0_PSI_DELTA_A5_OWNER_AUTHORIZED_DEV_V2` is a narrowly scoped continuation of the research-owner-authorized exploratory DEVELOPMENT work recorded in V1. Direct user instruction authorizes this execution in this conversation. It does not establish independent identity verification, independent review, normative policy approval, G1 completion, G4 authorization, or permission to use the protected official measured-study entrypoint.

The only architecture-level unit remains the exact transition `A0_4_REPORT_QUERY_PORT` → `A0_5_MODULE_DATA_OWNERSHIP`. The reconstructed B0 controls and Method Ψ algorithm, evaluator configurations, source states, operation rules, and acceptance thresholds are unchanged. The known PR #56 negative probe remains the same historical probe, not a new holdout and never a Method Ψ input.

## Corrections from V1

1. **Source binding:** evaluator configuration and application execution continue to use the verified subject checkout. Git source identity and inspection-scope readback use the exact checkout that produced the source commit, including the reconstructed negative-probe checkout. A row is `MEASURED` only after exact source commit/tree, complete inspection, and zero missing, altered, and unexpected scope counts pass. A mismatch is a failure, not a warning.
2. **Sandbox:** Method Ψ runs in a digest-pinned `python:3.12.15-slim-bookworm` container for `linux/amd64`. The method receives only the runtime, method input bundle, TEST_ONLY adaptation evidence/key, and one writable raw-output directory. The container uses `--network none`, a read-only root filesystem, explicit read-only input mounts, dropped capabilities, `no-new-privileges`, resource limits, and the runner UID/GID. It receives no repository checkout, `.git`, scorer/expected outputs, other-arm observations, host credentials, Docker socket, or privileged resources. The workflow runs on `ubuntu-24.04` and pins the exact observed hosted-runner/Docker identity in the pre-run freeze.
3. **Mandatory preflight:** a bridge-network control container must reach a test-only host canary. The constrained sandbox must then start the pinned interpreter, read its required input, write only its permitted output, fail to read protected canaries and repository history, and fail to reach both the test canary and an external test target. The host identity, inspect record, stdout/stderr, results, and checksums are preserved. A failed preflight ends the run before any calibration or transition measurement.
4. **Partial retention:** every attempted transition retains its raw run tree. A successful transition uses the unchanged complete V4 archive validator. An incomplete run uses the new, strictly typed `PARTIAL_EXECUTION_EVIDENCE` archive and validator. The partial manifest reports source identity verification, each phase, method-process status, any parseable raw method observation, errors, and checksums. Archive failure leaves the raw tree available for the outer evidence bundle. Infrastructure failures are never recorded as Method Ψ HOLD.

## Frozen measurement plan

The source pair, application trees, reconstructed B0 bytes, evaluator set, historical negative-probe patch, and Method Ψ inputs are pinned in `PRE_RUN_FREEZE.json`. The freeze also pins all implementation/protocol/schema/workflow digests, exact hosted runner and Docker identity, sandbox image digest/platform, pre-run capability-preflight digest, budgets, repetition counts, and analysis version before measurement.

Calibration uses one warmup and ten measured process repetitions per evaluator for the existing negative probe. The three evaluators are `AC_PUBLIC_API`, `AC_MODULE_GRAPH`, and `AC_DATA_OWNERSHIP`. The 33 existing V1 clean-source calls remain a separate dataset and are not rerun merely to recreate them. The pre-registered identity rule in `PROTOCOL_V2.json` adds the same one-plus-ten clean-source control calls per evaluator only when a frozen evaluator runner field differs from the V1 run (`runner_image_os`, `runner_image_version`, host OS, Python implementation/version, architecture, CPU count, or uv version). V1 and V2 samples are never pooled.

The transition schedule is one warmup and three measured technical repetitions, with actual unchanged B0 evaluator controls followed by the existing Method Ψ pipeline. No expected operation, synthetic ground truth, or scorer outcome is injected. Actual outcomes may include HOLD, ACCEPT, REJECT, INPUT_REJECTED, or a separately classified execution/infrastructure failure. An observed HOLD is preserved as a genuine method output. Candidate validation and evaluator execution occur only if the actual method output proposes a candidate.

Timing boundaries remain: evaluator subprocess duration from the existing evaluator runner; source/scope verification interval around the bound evaluator; Method Ψ process duration from the transition record or measured process boundary; and full transition elapsed time around the adapter. CPU deltas are host self+child process accounting; per-process RSS and monetary cost are unavailable. Four technical transition attempts are not four independent architecture transitions. Statistics are descriptive only; no inferential significance is computed and no coverage percentage is reported.

## V1 treatment and scientific boundary

V1 remains frozen historical evidence. Its 30 clean-source measured records and their observed means remain separate. The 33 original negative-probe records remain FAILED even though their preserved outputs passed post-run scope readback. The four bubblewrap failures remain infrastructure failures with Method Ψ decision, plan, and candidate `NOT_OBSERVED`; they are not converted to HOLD. V2 corrects the execution path and provides new raw observations without rewriting V1.

Neither a successful sandbox nor a method decision establishes independent semantic validity, normative applicability, mandatory coverage, adaptation quality, runtime architectural quality, or scientific superiority. G1=`INCOMPLETE`, G4=`NOT_AUTHORIZED`, P algorithm=`NOT_READY`, reference gate=`NOT_READY`, scoring=`NOT_EXECUTED`, and coverage=`UNKNOWN` remain fixed.

## Stop and archive rules

Preflight, source identity, baseline identity, probe replay, inspection-scope capability, archive writing/readback, and output permission checks are mandatory. Stop before measurements if any fail. Preserve all diagnostic bytes. Each transition attempt is archived immediately after it returns or fails. The outer bundle includes calibration records, complete/partial transition archives and raw folders, protocol/freeze snapshots, the actual preflight, result manifest, generated analyses, verification report, and SHA-256 inventory. A release is created against the frozen commit and its downloaded bytes are checked against the published SHA-256 and re-verified.

## Reproduction and interpretation

Use the exact workflow run, frozen commit, release archive, V2 analysis files, and included input snapshots. Re-run only from the frozen commit and the frozen hosted runner identity. A digest/readback PASS confirms byte integrity. It does not independently validate the measurement semantics or advance a research gate.
