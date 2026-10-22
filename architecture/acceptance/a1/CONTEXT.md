# Context — `architecture/acceptance/a1`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context; evaluator policy reflects W0's 2026-10-21 integration approval.

## Responsibility

Provide independent, source-derived evaluators for AC_PUBLIC_API, AC_MODULE_GRAPH, and AC_DATA_OWNERSHIP, with exact source/config digests and readback support. These evaluators do not implement Method P or mutate application code.

## Local landmarks

- `engine.py` — capability discovery, complete source inventory, AST import resolution, revision checks, evidence generation, and digest readback.
- `analyzers.py` — public API, capability graph, and persistence ownership checks.
- `cli.py` — standalone evaluator entry point.
- `public_api_v1.yaml` — W0-approved ΔA2 export names, `tasks.public.TaskSummary` fields, state applicability, and the A0.2/A0.3 Reporting exception.
- `module_graph_v1.yaml` — W0-approved state-specific capability edges, cycle rule, final Tasks → Notifications prohibition, and shared infrastructure roots.
- `data_ownership_v1.yaml` — W0-approved table-owner map and exact model-registry exception.
- `evidence.schema.json` — JSON evidence contract consumed by the W3 handoff.
- `a0_1_*_observation.json` — source-bound A0.1 diagnostics; each is explicitly `NOT_APPLICABLE` to A1 policy.
- `a0_2_public_api_evidence_input.yaml` — evaluator-only binding to the W0-provided ΔA2 SHA/tree; not a registered architecture-state manifest.
- `a0_2_public_api_observation.json` — schema-validated AC_PUBLIC_API output for the exact ΔA2 checkpoint.
- `a0_3_public_api_observation.json` and `a0_3_module_graph_observation.json` — source-bound candidate ΔA3 evaluator outputs; each names its exact source SHA, evaluator/configuration digests, inspection counts, raw-output digest, and coverage limits.
- `a0_3_evidence_readback.json` — independent file-byte sidecar for the two ΔA3 outputs, including the evaluated application tree SHA and exact output-file SHA-256 values.
- `W3_HANDOFF.md` — evaluator identities, source/config bindings, and exact-pair evidence boundary.

## Established conventions

Run an evaluator with the exact architecture manifest and expected Git source SHA. For a manifest outside the subject checkout, pass `--evidence-root`; evidence stores `manifest_path` relative to that root and marks `manifest_root: evidence`. `verify_evidence()` keeps the subject checkout root separate from the evidence root and rechecks the exact manifest bytes. It rejects absolute references and relative paths escaping their declared root. A missing module, unresolved scope, mismatched architecture revision, changed subject source, unpinned revision, or changed manifest/evaluator/config bytes must remain `NOT_EVALUABLE` or `UNKNOWN`; never infer compliance from an empty graph. CLI exits are 0 for COMPLIANT, 1 for NON_COMPLIANT, 2 for UNKNOWN/NOT_EVALUABLE or execution failure, and 3 for NOT_APPLICABLE. Evaluator exit success, complete scope, compliance, and representation-to-obligation adequacy are separate claims.

## Constraints and known gaps

The W0-approved ΔA2 `public.py` exports and `tasks.public.TaskSummary` field names are recorded in `public_api_v1.yaml`; callable signatures, `__all__`, runtime re-exports and runtime behavior are not inspected. The approved state-specific graph, `app.events` shared-infrastructure treatment, table-owner matrix and exact `app.db.model_registry.py` exception are recorded in their versioned configs and summarized in `W3_HANDOFF.md`. The Reporting → Tasks service query exception applies only to A0.2/A0.3 and cannot make final A1 compliant. The registry exception accepts only declared model symbols from each inspected capability `model.py`; it does not authorize capability code to import the registry.

The A0.3 stage gate requires both AC_PUBLIC_API and AC_MODULE_GRAPH, checks the exact candidate HEAD and complete scope, then validates evidence schema and re-reads the manifest, evaluator/configuration bytes, source files, and raw diagnostics digest. These static checks exclude dynamic imports, reflection, raw SQL contents, runtime behavior, and database permissions; they are engineering acceptance evidence, not semantic coverage or research authority. The historical A0.1 observations remain digest-bound diagnostics and are not evidence for A0.3.

## Verification

```bash
uv run pytest --no-cov -p no:cacheprovider tests/architecture/a1
python -m architecture.acceptance.a1.cli AC_MODULE_GRAPH --repo-root . --state-manifest architecture/states/A0_1_CAPABILITY_MODULES.yaml --architecture-state A0_1_CAPABILITY_MODULES --expected-source-sha <40-character-git-sha>
python -m architecture.acceptance.a1.cli AC_PUBLIC_API --repo-root <clean-checkout-at-934f5e0> --state-manifest <W2-evidence-bundle>/a0_2_public_api_evidence_input.yaml --evidence-root architecture/acceptance/a1 --architecture-state A0_2_PUBLIC_MODULE_APIS --expected-source-sha 934f5e045af473acdb197604c761597ba39b026c
```

Use the target worktree's own environment and an exact, clean subject source revision for evidence intended for independent readback.
