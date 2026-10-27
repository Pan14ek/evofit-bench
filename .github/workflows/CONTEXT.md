# Context — `.github/workflows`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `.github/CONTEXT.md` before this file.

## Responsibility

CI workflow YAML: uv, Python and disposable PostgreSQL.

## Local landmarks

- `ci.yml` — default development quality workflow pins prospective A0.5 and runs all three source-based architecture evaluators after historical checks.
- `mono-ci-b0-psi-development.yml` — branch-scoped DEVELOPMENT quality, fresh B0 evaluator probe, deterministic archive readback, and 90-day Actions artifact upload with a private prerelease fallback when artifact storage is unavailable; no official method execution.
- `mono-ci-psi-transition-development.yml` — separate exact-pair Method P DEVELOPMENT execution, shared archive-module readback, 90-day Actions artifact, and verified private-prerelease fallback; official research gates remain unchanged.
- `mono-ci-psi-a05-development.yml` — separate canonical A0.4→committed A0.5 Method Ψ DEVELOPMENT run with focused/historical regressions, archive readback, and artifact/private-prerelease retention.


- `mono-ci-psi-owner-authorized.yml` — reusable, freeze-checked run called by `ci.yml` only after development-quality passes on the dedicated branch; executes preregistered DEVELOPMENT calibration and full A0.5 adapter repetitions, verifies readback, and publishes a 90-day Actions artifact plus a persistent prerelease archive. This repository is public, so both evidence URLs are public. The workflow preserves official NO_GO/NOT_READY/G1/G4/reference/scoring/coverage states and is separate from the G4 measured-study path.

The owner-authorized ΔA5 reusable workflow requires the commit to change only PRE_RUN_FREEZE.json after the implementation commit. The existing CI workflow calls it only on a push to the dedicated branch and waits for development-quality. It uses the existing isolated A0.5 DEVELOPMENT adapter, writes raw run archives and calibration data, derives tables from those archives, then verifies both Actions artifact inputs and release readback. Its runner verifies the exact freeze commit before study execution. The durable release is explicitly a researcher-authorized DEVELOPMENT archive, not an approval or official result.

## Established conventions

Keep actions aligned with Makefile and pyproject.toml.

The B0/Ψ archive workflow runs only for the existing corrective branch's
relevant source, schema, dependency, or workflow changes, plus manual
dispatch. It provisions the same disposable PostgreSQL service as `ci.yml`,
runs both the focused harness and `make development-quality`, then creates a
fresh run ID and verifies a ZIP plus SHA-256 sidecar. It first uploads a
90-day Actions artifact; if repository artifact storage is unavailable, it
stores and downloads the same files from a private DEVELOPMENT prerelease and
repeats verification. Keep it separate from the default quality workflow and
preserve the NO_GO/NOT_EXECUTED boundary.

The transition workflow is additive and branch-scoped. It runs the actual P
DEVELOPMENT API after the focused regressions and `make development-quality`,
then uses the transition archive contract in the shared B0/Ψ archive module.
Keep the existing B0 workflow and its archive contract unchanged.

The ΔA5 workflow is a separate branch-scoped V4 transition identity. It runs
the focused A0.5 ownership tests, the prior A0.3→A0.4 transition regression,
and development quality before executing Ψ against the canonical A0.4 source
and committed A0.5 source. It verifies the raw archive before artifact upload
with the source checkout available for negative-probe replay; its private
prerelease fallback repeats checksum and extracted-run readback. V4 preserves
patch/source bytes and recomputes outcome-neutral detection, while V3 archives
retain their original verifier behavior.
The workflow preserves NO_GO, NOT_READY, INCOMPLETE, and NOT_AUTHORIZED gates.

CI installs the optional research dashboard and figure extras so their reader, visualization, and export checks run under the frozen lockfile.

## Constraints and known gaps

The default push and pull-request workflow runs `make development-quality`.
That target runs the explicit SPEC 01/02/03 regression set, one synthetic
Docker isolation probe, static/security/architecture checks, and migration
validation against the disposable PostgreSQL service. Its stage-aware
architecture check pins historical A0.1 tests and, at A0.3, requires current
source-bound AC_PUBLIC_API and AC_MODULE_GRAPH passes with evidence readback. It excludes
`tests/unit/test_da01_execution.py` and
`tests/unit/test_research_schema_foundation.py` from lint, formatting, type
checking, and pytest discovery. The current stage gate requires all three
source-bound A0.5 evaluators after verifying historical state evidence. Do not
skip other tests to get a green run;
unavailable Docker isolation probes remain unresolved.

The workflow fetches complete Git history because the verified V3 exporter
binds architecture snapshots to historical source commits, including frozen
A0. A shallow checkout prevents those source-bound integration tests from
running and is not equivalent evidence.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Reproduce the safe CI job with `make development-quality` and a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
