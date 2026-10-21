# Context — `architecture/acceptance/a1`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context; the state-specific YAML files are proposals pending W0 review, not approved experimental policy.

## Responsibility

Provide independent, source-derived evaluators for AC_PUBLIC_API, AC_MODULE_GRAPH, and AC_DATA_OWNERSHIP, with exact source/config digests and readback support. These evaluators do not implement Method P or mutate application code.

## Local landmarks

- `engine.py` — capability discovery, complete source inventory, AST import resolution, revision checks, evidence generation, and digest readback.
- `analyzers.py` — public API, capability graph, and persistence ownership checks.
- `cli.py` — standalone evaluator entry point.
- `public_api_v1.yaml`, `module_graph_v1.yaml`, `data_ownership_v1.yaml` — versioned state and policy proposals pending W0 freeze.
- `evidence.schema.json` — JSON evidence contract consumed by the W3 handoff.
- `W3_HANDOFF.md` — evaluator identities, source/config bindings, and exact-pair evidence boundary.

## Established conventions

Run an evaluator with the exact architecture manifest and expected Git source SHA. A missing module, unresolved scope, mismatched architecture revision, changed subject source, unpinned revision, or changed evaluator/config bytes must remain `NOT_EVALUABLE` or `UNKNOWN`; never infer compliance from an empty graph. CLI exits are 0 for COMPLIANT, 1 for NON_COMPLIANT, 2 for UNKNOWN/NOT_EVALUABLE or execution failure, and 3 for NOT_APPLICABLE. Evaluator exit success, complete scope, compliance, and representation-to-obligation adequacy are separate claims.

## Constraints and known gaps

The public entrypoint convention (`public.py`), allowed dependency graph, shared infrastructure roots, table-owner matrix, and centralized `app.db.model_registry.py` exception are proposals until W0 freezes them. The Reporting → Tasks service query exception applies only to A0.2/A0.3 and cannot make final A1 compliant. Static AST checks do not inspect raw SQL text, dynamic imports, reflection, runtime access, or runtime behavior. The current A0.1 source is not subject to these future obligations and must report `NOT_APPLICABLE` when evaluated as A0.1.

## Verification

```bash
uv run pytest --no-cov -p no:cacheprovider tests/architecture/a1
python -m architecture.acceptance.a1.cli AC_MODULE_GRAPH --repo-root . --state-manifest architecture/states/A0_1_CAPABILITY_MODULES.yaml --architecture-state A0_1_CAPABILITY_MODULES --expected-source-sha <40-character-git-sha>
```

Use the target worktree's own environment and an exact, clean subject source revision for evidence intended for independent readback.
