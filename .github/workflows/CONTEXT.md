# Context — `.github/workflows`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `.github/CONTEXT.md` before this file.

## Responsibility

CI workflow YAML: uv, Python and disposable PostgreSQL.

## Local landmarks

- `ci.yml`
- `mono-ci-b0-psi-development.yml` — branch-scoped DEVELOPMENT quality, fresh B0 evaluator probe, deterministic archive readback, and 90-day Actions artifact upload; no official method execution.

## Established conventions

Keep actions aligned with Makefile and pyproject.toml.

The B0/Ψ archive workflow runs only for the existing corrective branch's
relevant source, schema, dependency, or workflow changes, plus manual
dispatch. It provisions the same disposable PostgreSQL service as `ci.yml`,
runs both the focused harness and `make development-quality`, then creates a
fresh run ID and uploads a verified ZIP plus SHA-256 sidecar. Keep it separate
from the default quality workflow and preserve the NO_GO/NOT_EXECUTED boundary.

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
checking, and pytest discovery. Do not skip other tests to get a green run;
unavailable Docker isolation probes remain unresolved.

The workflow fetches complete Git history because the verified V3 exporter
binds architecture snapshots to historical source commits, including frozen
A0. A shallow checkout prevents those source-bound integration tests from
running and is not equivalent evidence.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Reproduce the safe CI job with `make development-quality` and a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
