# EVAL-02 — expanded controlled validation of architecture evaluators

- **Protocol version:** 1.0.0
- **Track:** W2 evaluator validation, continuation of EVAL-01
- **Verified main base:** `cd134063e8c1eae37eb3bafe01ce228f02f49493` (PR #38 merge)
- **Source under test:** canonical `A0_4_REPORT_QUERY_PORT`, commit `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`, `app/` tree `007196f68652bc13f6798805793ffdfae96f95f7`
- **Evaluators:** `AC_PUBLIC_API` 1.0.0 and `AC_MODULE_GRAPH` 1.0.0, with configuration and source digests frozen in the catalog

EVAL-02 extends the finite source-condition study in EVAL-01. It preserves every EVAL-01 protocol, result, raw archive and canonical architecture checkpoint byte-for-byte. The experiment uses the same canonical A0.4 source and source-bound evaluator versions, while adding interventions that probe public-contract definitions, relative and function-local imports, aliased module imports, and a dynamic-import boundary.

This is controlled engineering evidence about two named static evaluators. It is not a MONO-E1 result, a B0 or Method P comparison, a scorer result, a test of fitness-representation coverage, or authorization for measured DA01 work.

## Question and preregistered expectations

**RQ:** On clean, source-pinned A0.4 revisions, how do the two evaluators respond to the new source patterns in the catalog, where do they return a valid result despite an architectural defect, and what evaluator-subprocess times are observed?

- **H1 — public contract definitions:** the public API evaluator reports missing required symbols, missing `TaskSummary` fields and undeclared public exports. The graph evaluator is not applicable to those contract-only conditions.
- **H2 — import forms:** relative and function-local imports of an allowed public contract retain compliance; an aliased import of a private module and a function-local relative dependency on Notifications produce the independently registered API or graph violation.
- **H3 — evaluator boundaries:** a runtime `importlib.import_module` of a private/disallowed module is an architectural violation but lies outside both evaluators' direct-import inventory. A keyword-only signature change breaks the observed positional caller, while the frozen public API configuration does not specify signatures; that API result is reported as a boundary observation, not assigned a binary architectural label.

The case catalog separates (a) architectural validity for each obligation, (b) applicability of each evaluator to the construct, and (c) the expected evaluator output. The architecture labels are grounded in the frozen A0.4 edge/API catalog, source-level caller compatibility, and Python import semantics. The expected evaluator outputs are preregistered from the pinned evaluator implementation/configuration and their documented coverage limits. Evaluator output is never used to assign architectural labels.

## Independently justified case selection

`EVAL02_MUTATION_CATALOG_V1.json` is the complete preregistered case list. It includes an untouched clean-scope control and two positive import controls in source forms not used by EVAL-01. The negative cases remove a frozen public symbol or field, add an undeclared public symbol, import a private module with `ast.Import`, and introduce a function-local relative import that creates a disallowed capability edge. These conditions test different analyzer branches or syntax forms than EVAL-01's private absolute `from` import, type-only edge, cycle, unresolved import and missing-package cases.

Two boundary cases are deliberately excluded from binary confusion metrics. The dynamic-import case has a clear architecture violation but is outside the AST import inventory. The signature case makes the existing Reporting caller incompatible with the Tasks function, but the frozen public-interface configuration records the function name and type/field inventory, not call signatures. Neither evaluator's outcome is accepted as ground truth for those boundaries.

## Source and evaluator identity

The experiment branch is based directly on the verified PR #38 merge commit above. Each source condition is materialized independently from exact canonical A0.4 commit `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`, with that commit as the sole parent for each mutation revision. The preregistration catalog pins the A0.4 `app/` tree, state manifest, both evaluator configuration digests, aggregate evaluator source digest, and identity-only canonical checkpoint/source-manifest digests from the verified main base. EVAL-01 reference artifact digests are recorded for readback only; the old artifacts are not inputs to the evaluators.

Before each evaluator call, the harness requires the case checkout HEAD to equal the registered case SHA and the full checkout to be clean. It passes that SHA as `--expected-source-sha`. A mismatch, dirty checkout, launch/parse error, evaluator/configuration drift, missing output, or unexpected execution status is retained as an invalid/unknown observation and is never counted as a detection.

## Execution and analysis

1. Commit this protocol, catalog, runner and analysis-contract tests before the first evaluator invocation. The protocol runner checks that its preregistration commit is a direct child of the verified main base and that the experiment checkout descends from it.
2. Run the source-only preflight first. It validates every mutation anchor, creates temporary child revisions, parses changed Python files, checks exact parentage and bundle generation, and does not invoke either evaluator.
3. Execute all 10 conditions against both evaluators, three repeats each (60 evaluator calls), in deterministic pseudorandom order using seed `20261024`. Repeats are technical repetitions of one case, not independent architecture samples.
4. Preserve each command, UTC start/end, monotonic wall duration, exit code, raw stdout/stderr, source commit/tree identity, evaluator/configuration digests, finding codes, scope counts, exact mutation patch, and Git bundle. Do not delete failed or unexpected attempts.
5. Analyze only after execution. Re-derive observation fields from raw stdout and verify the preregistration and raw-artifact inventories. Collapse repeats to one evaluator-by-case row. A row enters a confusion matrix only when its architecture status is binary, the evaluator is preregistered applicable to that construct, every repeat is source/configuration-bound, all repeats complete, and outcomes/findings are stable.
6. Report per-evaluator case counts and confusion metrics, each case's architectural status/applicability/expected/observed outcome, execution failures, `NOT_EVALUABLE` outcomes, and timing median/minimum/maximum. Do not calculate confidence intervals or treat repeats, imports, files, modules or findings as independent samples.

The measured time is the end-to-end evaluator subprocess duration, including interpreter startup, source inventory, AST analysis and JSON output. It is not application runtime, CI latency, adaptation overhead, CPU or memory use.

## Exclusions

No mutation or output is made to EVAL-01 files, canonical A0/A0.3/A0.4 checkpoints, architecture policy, evaluator code/configuration, DA01 source/ground truth, scorer-only reference data, Method P, B0/P protocols, or MONO-E1 evidence. No runtime workload, database behavior, deployable topology, dynamic import reflection beyond the named boundary, production approval, G1/G4 claim, or Method P effectiveness claim is in scope.

## Evidence and reproduction

After the preregistration commit, run from a clean checkout with the project's pinned development dependencies:

```bash
uv sync --frozen --extra dev
uv run python experiments/pilots/run_eval02.py preflight --repo-root .
uv run python experiments/pilots/run_eval02.py execute --repo-root . --output-dir experiments/results/eval02-run
uv run python experiments/pilots/run_eval02.py analyze --run-dir experiments/results/eval02-run --summary-dir experiments/pilots --package experiments/pilots/EVAL02_RAW_EVIDENCE_V1.zip
```

`experiments/results/` is ignored scratch output. The committed raw ZIP and external `.sha256` sidecar preserve the preregistration snapshot, exact-source case revisions, mutation patches and Git bundles, raw observations, run manifest, case-level results and `SHA256SUMS`. The report and Ukrainian manuscript subsection are derived from this archived evidence. Verify the sidecar before extraction and verify the internal inventory with `sha256sum -c SHA256SUMS` from the extraction root.

## Threats to validity

**Internal validity:** all mutations are constructed as isolated children of one frozen A0.4 source commit, which limits drift but provides no independent architecture baseline. The fixed local interpreter, operating system, filesystem and cache state can affect timing. Deterministic repetitions reveal invocation stability only; they do not remove machine-level timing noise.

**Construct validity:** the case catalog is finite and author-selected. Architecture status is independently specified from the frozen API/edge contracts and source semantics, but no external reviewer or independent oracle labels these cases. Static import rules do not measure runtime use, behavioral correctness, deployment topology or business outcomes. The signature boundary is deliberately unresolved by the frozen interface policy and is not silently forced into a binary metric.

**External validity:** results apply only to these exact evaluator/configuration versions, Python patterns and canonical A0.4 baseline. They do not estimate population-level accuracy or establish generalization to other repositories, languages, architectures, runtime mechanisms, or future evaluator versions.

## Recommendation boundary

The report must state whether the observed results support using these evaluators as descriptive evidence before MONO-E1, and whether any remaining applicability gap should be resolved before MONO-E1. EVAL-02 is not itself a MONO-E1 gate and cannot authorize or validate Method P.
