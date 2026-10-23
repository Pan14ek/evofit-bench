# EVAL-01 — controlled validation of architecture fitness evaluators

- **Protocol version:** 1.0.0
- **Track:** W2 evaluator validation
- **Source baseline:** canonical `A0_4_REPORT_QUERY_PORT`, commit `d3101c0d3aa9b7b709253b6ec7518416f05f65b9`, application tree `007196f68652bc13f6798805793ffdfae96f95f7`
- **Evaluators:** `AC_PUBLIC_API` 1.0.0 and `AC_MODULE_GRAPH` 1.0.0

EVAL-01 measures the response of two source-based engineering evaluators to a finite, predeclared set of direct mutations of canonical A0.4. It is independent of MONO-E1/E2, DA01 effectiveness evaluation, B0, Method P, and the scorer. It does not establish scientific representation coverage, production authorization, G1/G4, runtime behavior, or generalization to other architectures.

## Research question and hypotheses

**RQ:** On clean, source-pinned A0.4 checkouts, do `AC_PUBLIC_API` and `AC_MODULE_GRAPH` produce the independently specified outcomes for allowed public imports, private cross-module imports, undeclared capability edges, cycles, unresolved imports, and incomplete module scope? What subprocess wall time is observed for each check?

- **H1 — public API:** an allowed import from a declared public module remains `COMPLIANT`; replacing it with the forbidden private Tasks service import makes `AC_PUBLIC_API` `NON_COMPLIANT` with `CROSS_MODULE_IMPORT_NOT_PUBLIC`.
- **H2 — module graph:** the evaluator accepts the five declared A0.4 capability edges and reports `UNDECLARED_DEPENDENCY`, `DEPENDENCY_CYCLE`, and `UNRESOLVED_LOCAL_IMPORT` for the corresponding injected source conditions.
- **H3 — incomplete scope:** removing an expected capability package produces `NOT_EVALUABLE` for both evaluators with an explicit missing-module scope uncertainty; it is not counted as a detection success.

These are finite mutation-test hypotheses. They are not estimates of evaluator performance over a population of architectures.

## Intervention and controls

The versioned machine-readable mutation catalog is [`EVAL01_MUTATION_CATALOG_V1.json`](EVAL01_MUTATION_CATALOG_V1.json). It defines seven source conditions, the exact intervention recipe, per-evaluator expected compliance, expected finding codes, metric eligibility, and clean-scope expectations. Each mutation starts independently from the exact A0.4 commit. Mutation labels describe the injected source condition and are not scorer-only reference labels or target operations.

The untouched A0.4 revision is the clean control: its graph must contain exactly the five declared edges, with no cycle or unresolved import. A matched public-import control rewrites the Reporting call through the Tasks public module; the paired negative control changes that same boundary to the private service import. Other negative controls are single, type-checking-only source imports, except for deletion of the expected Audit package. Type-checking-only imports are intentionally in scope because the evaluator catalogs conditional imports; they do not claim those imports execute at runtime.

## Execution protocol

1. Commit this protocol, catalog, and runner before the first evaluator invocation. Record the catalog's preregistration commit and SHA-256 in the run manifest. Do not amend expected outcomes after seeing results.
2. Require the exact baseline commit and `app/` tree above. For every mutated condition, create a separate disposable Git clone, check out the A0.4 commit, apply exactly one catalogued mutation, and create a child commit whose sole parent is A0.4. Save the mutation patch and a Git bundle containing the mutation commit with A0.4 as its prerequisite.
3. Before every evaluator call, require `HEAD` to equal the case commit and the complete checkout to be clean. Pass that same SHA as `--expected-source-sha`. Record the evaluator and configuration digests returned by the CLI. A source identity mismatch, dirty checkout, launch/parse error, or unexpected execution failure is an invalid/unknown observation, never a true positive.
4. Run both evaluators three times per condition (7 conditions × 2 evaluators × 3 measured repeats = 42 calls). Use one deterministic pseudorandomized order with seed `20261023`. Repeats estimate invocation timing and reproducibility for the same source condition; they are not independent architecture cases. Do not discard a failed or unexpected run.
5. Capture each exact command, start/end time, monotonic wall duration, return code, stdout JSON, stderr, source and application tree SHA, configuration/evaluator digests, raw diagnostic digest, inspected-file count, finding codes, and failures. Preserve unavailable measurements as unavailable.
6. Analyze only after all calls have been recorded. For each evaluator, collapse repeats to one case-level outcome. A labeled case enters the confusion matrix only when every repeat completed, source/configuration bindings matched, and the case's observed compliance is consistently `COMPLIANT` or `NON_COMPLIANT`. Report `UNKNOWN`/`NOT_EVALUABLE`, incomplete runs, and failures separately. The deliberately incomplete-scope case is excluded from binary metrics by preregistration.
7. Report case-level confusion counts and precision, recall, specificity, accuracy, and F1 where denominators are defined. Do not compute confidence intervals or treat repeats, imports, files, or obligations as independent architecture samples. Report timing as descriptive median/minimum/maximum only.

The measured wall duration is end-to-end evaluator subprocess time, including interpreter startup, source inventory, AST analysis, and JSON emission. It is not application runtime, CI pipeline latency, adaptation overhead, CPU, or memory measurement.

## Evidence and reproduction

[`run_eval01.py`](run_eval01.py) creates the isolated revisions, invokes the exact A0.4 evaluator code/configuration, preserves raw results, and performs the preregistered analysis. Run from a clean checkout with canonical Git history available:

```bash
uv sync --frozen --extra dev
uv run python experiments/pilots/run_eval01.py execute --repo-root . --output-dir experiments/results/eval01-run
uv run python experiments/pilots/run_eval01.py analyze --run-dir experiments/results/eval01-run --package experiments/pilots/EVAL01_RAW_EVIDENCE_V1.zip
```

`experiments/results/` is ignored scratch output. The committed archive and SHA-256 sidecar are the retained evidence package; it contains the run manifest, exact command log, raw evaluator stdout/stderr, mutation patches, source-bound commits, Git bundles, generated analysis, and a package checksum inventory. The run fails closed on a wrong source tree, dirty subject checkout, evaluator/configuration drift, or invalid provenance. The runner uses local source checkouts and does not access the scorer, oracle, ground-truth files, network services, B0, or Method P.

## Scope and validity limits

The evaluators parse configured Python source with AST rules. The public API check covers configured top-level names and the `TaskSummary` fields; it does not validate call signatures, runtime re-exports, or behavior. The graph checker recognizes direct Python imports and configured shared-infrastructure roots. It does not inspect dynamic imports, reflection, runtime dependency injection, raw SQL contents, database permissions, runtime behavior, or deployable topology. Conditional imports are counted as source dependencies regardless of reachability. The missing-package case demonstrates fail-closed scope handling, not successful identification of every absent dependency form.

Mutations and expected labels are authored from the versioned A0.4 policy and the intervention recipes, so author selection and limited mutation diversity remain threats to construct validity. This protocol tests these exact evaluator versions and cases only. A favorable finite confusion matrix is not independent scientific review, evaluator semantic adequacy for a fitness representation, MONO-E1 evidence, Method P effectiveness, or production authorization.
