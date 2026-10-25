# DEVELOPMENT technical validation

This records engineering harness behavior only. The B0 configuration is a prospective, unapproved reconstruction. This was not an authorized B0/Ψ comparison, produced no metric scores, and does not establish scientific evidence or strategy superiority. The official study remains `NO_GO`.

## Execution

- **Status:** PASS for runner/materialization/readback; B0 evaluator probes executed; Ψ NOT EXECUTED; scoring NOT EVALUABLE.
- **Execution ID:** `DEV_MONO_CI_20261025T_DEV01`.
- **Source pair:** A0.3 `26a9bb667da7d0938e38aca15d2bf29fd1de4829` → A0.4 `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`.
- **Run directory:** `/private/tmp/mono-ci-b0-psi-development-20261025`.
- **Result SHA-256:** `d15175899de5063ad5a186adc2d0e69c849988e7bbeb44657a150f0b911fb679`.
- **Run inventory:** 1,154 files sealed and verified by `SHA256SUMS`.
- **Baseline SHA-256:** `9df6f138118bca83c411cceeff7ed8d2b557ec633baedb1f7e044a779a571ada`; identity is `PROSPECTIVE_RECONSTRUCTION_NOT_HISTORICAL`, approval is `NOT_APPROVED`.
- **Input parity:** PASS for four cases. B0 and Ψ bundles have equal common-input identities and separate write-once input/output roots; no scorer or expected-output files were included.
- **Ψ:** `BLOCKED_NOT_EXECUTED`; `P_ALGORITHM_STATUS=NOT_READY`; no prediction, operation, or governance decision was emitted.
- **Scoring:** separate gate returned `NOT_EVALUABLE`, `NOT_ESTABLISHED`, and `{}` numeric results. Assessment is at `/private/tmp/mono-ci-b0-psi-scorer-assessment-20261025/scoring_assessment.json`, SHA-256 `2966cc09cd4d8cdf248a46e10146263b6c8f8d95f62aa3535bea8caf4925c6c6`.
- **Measurement status:** `NOT_EXECUTED`. Controlled-violation and end-to-end comparison metrics remain `NOT_MEASURED`; coverage and representation-validity metrics remain `NOT_EVALUABLE`; no missing value was converted to a score.

The raw DEVELOPMENT evaluator probes were:

| Case | Source commit | `AC_PUBLIC_API` | `AC_MODULE_GRAPH` | Technical duration (ns) |
|---|---|---|---|---:|
| CASE_01 | `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` | COMPLIANT (0) | COMPLIANT (0) | 381812000 |
| CASE_02 | `97ae3947991f58e346620583b53f4ee3646f22e7` | NON_COMPLIANT (1) | COMPLIANT (0) | 268105041 |
| CASE_03 | `c97570fa789515808a5de5f187f0a7416e391f39` | COMPLIANT (0) | NON_COMPLIANT (1) | 391872500 |
| CASE_04 | `0f93897b2d66fd9bc77ffdfad50b21b6a7b07a3d` | NOT_EVALUABLE (2) | NOT_EVALUABLE (2) | 384803416 |

These are raw engineering evaluator outputs from one technical run. They are not independently scored, do not validate the reconstructed baseline, and are not the end-to-end comparison-duration metric. The four selected cases do not establish a positive adaptation need.

## Exact commands

```bash
UV_CACHE_DIR=/private/tmp/evofit-uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/evofit-b0psi-venv PYTHONDONTWRITEBYTECODE=1 make test-mono-ci-b0-psi-execution
UV_CACHE_DIR=/private/tmp/evofit-uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/evofit-b0psi-venv PYTHONDONTWRITEBYTECODE=1 uv run --frozen --extra dev python -m experiments.execution.tooling.mono_ci_b0_psi_execution --development-validation --repository "$PWD" --output /private/tmp/mono-ci-b0-psi-development-20261025 --execution-id DEV_MONO_CI_20261025T_DEV01
UV_CACHE_DIR=/private/tmp/evofit-uv-cache UV_PROJECT_ENVIRONMENT=/private/tmp/evofit-b0psi-venv PYTHONDONTWRITEBYTECODE=1 uv run --frozen --extra dev python -m experiments.execution.tooling.mono_ci_b0_psi_scoring --run /private/tmp/mono-ci-b0-psi-development-20261025 --output /private/tmp/mono-ci-b0-psi-scorer-assessment-20261025
```

All three commands exited 0. Focused tests: **25 passed**. The existing PR #51 preflight returned `integrity_status=PASS`, `source_pair_readback=PASS`, `case_archive_readback=PASS`, and `readiness=NO_GO`; its result still reports both official arms and scoring as `NOT_EXECUTED`.

## Limits and remaining gates

This run only verified the harness and fresh B0 evaluator invocation. Ψ’s implementation path was not exercised because `require_p_algorithm()` correctly failed closed. There is no approved independent scorer reference/custody, complete mandatory applicability denominator, reviewed exact-pair semantic validity, approved reconstructed baseline/protocol amendment, completed G1, authorized G4, or ready ΔA4 reference gate. No official B0/Ψ measurement is authorized.

## Hosted persistent archive from PR #52

This is a **new** DEVELOPMENT run, separate from the local execution above. It was generated from the committed PR head and retrieved from GitHub after the workflow finished.

- **Workflow:** [MONO CI B0/Ψ DEVELOPMENT archive, run 40173042888](https://github.com/Pan14ek/evofit-bench/actions/runs/40173042888) — overall **PASS** on source revision `d9f22e9a5ec7f9166cd8b43d15b01ab0f3cc349b`.
- **Execution ID:** `DEV_MONO_CI_GHA_40173042888_1`.
- **Persistent location:** [private prerelease](https://github.com/Pan14ek/evofit-bench/releases/tag/mono-ci-b0-psi-development-40173042888-1), with [archive ZIP](https://github.com/Pan14ek/evofit-bench/releases/download/mono-ci-b0-psi-development-40173042888-1/mono-ci-b0-psi-development-40173042888-1.zip) and [detached SHA-256 sidecar](https://github.com/Pan14ek/evofit-bench/releases/download/mono-ci-b0-psi-development-40173042888-1/mono-ci-b0-psi-development-40173042888-1.zip.sha256). This private prerelease is available to repository readers and remains until the release is removed.
- **Actions artifact status:** the workflow attempted the configured 90-day Actions artifact upload, but GitHub rejected it because the repository artifact-storage quota was full. The workflow then created the private prerelease, downloaded both assets, checked the sidecar, and ran archive readback successfully. The release fallback is the durable copy for this run; it is not reported as a successfully uploaded Actions artifact.
- **Archive identity:** SHA-256 `6591d5df742c67907d064a45bbb6deab9534ee38cd1c914b507becf4d49bf68b`; 1,155 verified members. The digest was checked again after downloading the release asset locally, then `mono_ci_b0_psi_archive verify` returned `verification_status=PASS`.
- **Hosted checks:** focused execution/archive suite **40 passed**. `make development-quality` exited **PASS**; its broad regression suite reported **512 passed, 1 skipped, 1 warning**. The warning is Starlette's `TestClient` deprecation; Bandit also emitted existing nonfatal B108/B603 `nosec` warnings. The quiet regression summary did not include the skip reason. Fresh B0 evaluator probe, deterministic pack, extracted readback, and remote release-asset readback **PASS**. The run manifest records `measurement_status=NOT_EXECUTED`, `study_readiness=NO_GO`, `P_ALGORITHM_STATUS=NOT_READY`, `G1=INCOMPLETE`, `G4=NOT_AUTHORIZED`, reference gate `NOT_READY`, and Ψ `BLOCKED_NOT_EXECUTED`.
- **Environment:** Python 3.12.15, uv 0.13.5, Linux x86_64; `uv.lock` SHA-256 `c68f485aecbe90f6ce3d2737baf6f297b5498804c7aae6987cdbdf347852363b`.

To retrieve and verify this archive from a checkout with access to the private repository:

```bash
mkdir -p /tmp/mono-ci-b0-psi-release-readback-40173042888
gh release download mono-ci-b0-psi-development-40173042888-1 \
  --repo Pan14ek/evofit-bench \
  --dir /tmp/mono-ci-b0-psi-release-readback-40173042888
(cd /tmp/mono-ci-b0-psi-release-readback-40173042888 && \
  sha256sum --check mono-ci-b0-psi-development-40173042888-1.zip.sha256)
uv run --frozen --extra dev \
  python -m experiments.execution.tooling.mono_ci_b0_psi_archive verify \
  --archive /tmp/mono-ci-b0-psi-release-readback-40173042888/mono-ci-b0-psi-development-40173042888-1.zip \
  --extract-to /tmp/mono-ci-b0-psi-release-readback-40173042888/extracted
```
