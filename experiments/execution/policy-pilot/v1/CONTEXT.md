# Context — `experiments/execution/policy-pilot/v1`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `experiments/execution/policy-pilot/CONTEXT.md` before this file.

## Responsibility

Policy pilot v1 for 18 obligation hypotheses.

## Local landmarks

- `policy-design.yaml`

## Established conventions

Separate design matrix from executable condition rules.

## Constraints and known gaps

Rows DRAFT and registry OPEN; not experimental truth.

**Strict source-root exception:** the nested `source/` subtree is a versioned V3 policy input with an exact allowlist. Its five nested directories do not contain their own `CONTEXT.md`: those extra files make the actual V3 export fail. This parent document covers their responsibilities: `source/` is the pinned policy-bundle root; `source/fitness/` is an APA namespace; `source/fitness/policy/` contains draft Charter, Registry and completeness assertions; `source/fitness/policy/evidence/` carries synthetic provenance fixtures; and `source/policy/` contains the AR-DSL ruleset. Never insert context or unrelated files into these directories and never weaken the exporter to accommodate documentation.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
