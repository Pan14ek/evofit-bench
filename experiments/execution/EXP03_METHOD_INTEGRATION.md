# EXP-03 DEVELOPMENT integration: EXP-02 evidence and Method P

EXP-03 connects a validated EXP-02 evidence run to the existing SPEC 03 Method
P development pipeline. It keeps the original EXP-02 bundle immutable, retains
its digest-bound references, and serializes the result of the existing V3
verification and adaptation functions. The bridge does not implement another
impact, applicability, semantic-pair, operation, candidate, or governance
engine.

This is an engineering integration path. It does not establish `Coverage_P`,
`Coverage_ref`, scientific effectiveness, a measured B0/B1/P result, or G1/G4
approval. `P_ALGORITHM_STATUS` remains `NOT_READY`.

## Evidence-consumption boundary

The manifest's `evidence_flow` object distinguishes EXP-02 contract
validation, representation mapping, independent V3 input verification,
Method P execution, and evidence admission. The EXP-02 source artifacts are
revalidated with the existing EXP-01/02 contracts; this verifies their
references and derived bundle consistency, not independent semantic validity.
The manifest records `artifact_validation_status` as
`validated_by_exp01_exp02_contracts` and keeps
`independent_semantic_validation_status` at `not_independently_validated`.

The current bridge does **not** pass EXP-02 observations into
`run_adaptation()`. It supplies no adaptation evidence sidecar or trust
context, and the V3 bundle is verified with an empty evidence ledger. The
machine-readable status is `exp02_evidence_admission_status: not_admitted`,
with blocker `EXP02_EVIDENCE_NOT_ADMITTED_TO_METHOD_P`. A
`completed_with_hold` result means that the verified V3 Method P pipeline ran
and governance returned HOLD; it does not mean EXP-02 evidence drove an
adaptation. No semantic proof provider or alternate Method P engine is used.

## Inputs and validation

`--exp02-run-dir` must point to an existing EXP-01 bundle using schema 1.2.0
with EXP-02 representation evidence. The bridge runs the existing
`validate_bundle()` and `validate_representation_evidence()` checks, reloads
the configuration from the run's digest-bound artifacts, and preserves the
source revision, run ID, evaluator record identities, input artifacts, raw
outputs, compliance observations, metrics, scopes, and limitations.

`--p-input-dir` is optional. If provided, it must be an explicitly prepared V3
Method P input directory. The bridge passes it to `verify_v3_p_bundle()` with
an empty evidence ledger and then, when the verified architecture-after SHA
matches the EXP-02 source revision and the before SHA matches the frozen A0
revision in the verified representation catalog, passes the verified bundle to
`run_adaptation()`. EXP-02 evaluator output is never converted into semantic
pair evidence and no adaptation evidence sidecar or trust context is supplied.

The only stage translations are `ci_test → ci` and `runtime → runtime`.
Mappings also compare criterion, obligation, evaluator, metric, scope, and
architecture-after revision. A structural match is labeled `candidate_only`;
the separate mapping-status fields and reason codes preserve unresolved
evaluator, scope, metric, or revision links. Missing and invalid evidence
remains explicit. Unsupported stages and absent Method P representations do
not become eligible mappings.

The V3 policy-pilot source under `policy-pilot/v1/source` is DRAFT and its
registry closure is OPEN. It is used only to exercise the verified V3
execution pathway. It cannot establish normative authority or yield a positive
governance decision. Exact-pair validity and mandatory coverage remain
UNKNOWN when independent proof is absent.

## Prepare a V3 input explicitly

V3 input preparation uses the existing exporter APIs. Run this from the
repository checkout and provide a fresh scratch directory outside it. The
architecture revisions must be actual Git commits, and the evaluation time
must match the policy registry's `as_of` value.

```bash
uv run python - <<'PY'
from pathlib import Path

from experiments.execution.tooling.p_policy_source_v3 import (
    export_method_inputs_v3,
    package_policy_source_v3,
)

repository = Path.cwd()
scratch = Path("/private/tmp/evofit-exp03-unique-run")
policy_source = repository / "experiments/execution/policy-pilot/v1/source"
policy_bundle = scratch / "policy-source"
method_input = scratch / "method-input"

package_policy_source_v3(
    policy_source,
    policy_bundle,
    "EXP03_DRAFT_PILOT_2026-10-14",
)
export_method_inputs_v3(
    repository,
    policy_bundle,
    method_input,
    "P",
    "b78b0967be937634b7762baccf5ac6892b279a73",
    "5bb4354822a390f068c259cc2fe3caa44568b7d1",
    "2026-10-14T00:00:00Z",
)
PY
```

The example binds ΔA1 from the frozen A0 source to the fetched `main` source
revision used for the EXP-02 evidence run. For another run, pass that run's
actual source commit as `architecture_source_sha`; do not infer it from a
directory name. The policy source revision is a label, not an approval.

## Execute the bridge

Use a unique output run ID; both the source run and output are write-once.

```bash
uv run python -m scripts.exp03_method_bridge \
  --exp02-run-dir experiments/results/<existing-exp02-run-id> \
  --p-input-dir /private/tmp/evofit-exp03-unique-run/method-input \
  --output-dir experiments/results/<unique-exp03-run-id>
```

Without `--p-input-dir`, the bridge still writes the validated EXP-02 linkage
and records the machine-readable blocker `P_V3_INPUT_REQUIRED`; it does not
search the repository for a Method P bundle. A rejected or incompatible V3
input records the reason and skips adaptation. Exit code 0 means the existing
pipeline ran, exit code 2 means the integration output is valid but P did not
run, and exit code 1 means the input/output contract was rejected.

Each output directory contains:

- `integration_manifest.json` and its SHA-256 sidecar, with input references,
  mapping statuses, the explicit evidence-flow boundary, P execution state,
  blockers, governance result, and reproducibility metadata.
- `method_p_trace.json` when the verified V3 pipeline ran. It serializes the
  existing applicability, impact, pair, coverage, operation, candidate, and
  governance results with unresolved prerequisite reason codes.

The manifest and trace use schema version 1.1.0 in `schemas/`. Readback
re-runs the existing EXP-01/02 validators and V3 verifier for referenced
inputs, verifies generated digests, and checks that the manifest's derived
fields agree with the exact P trace. Keep the referenced input directories
available when validating an output. Never reuse an existing output directory.

## Current supported result

The EXP-02 run `exp03-exp02-20261018-5bb4354` was created from a clean checkout
at base revision `5bb4354822a390f068c259cc2fe3caa44568b7d1`. It records the
existing Import Linter and module-structure CI evaluators as passing, marks
deployment observation as skipped, and has no runtime record because the
service was stopped. Its bundle is therefore `incomplete`.

The V3 ΔA1 bundle verifies the A0 → A0.1 source revisions and runs through
the actual `verify_v3_p_bundle()` and `run_adaptation()` path. Its DRAFT/OPEN
policy input leaves policy authority and facts unresolved; without exact-pair
proof, applicability, mandatory classification, and cost authority, governance
returns HOLD and coverage remains UNKNOWN. EXP-02 observations remain separate
from semantic pair proof and are not admitted to P calculations. The
`completed_with_hold` status is therefore a verified diagnostic bridge, not
evidence-driven adaptation. No measured prediction or coverage claim is
emitted.

Current mapping limitations are recorded rather than repaired by inference:
the A0.1 module-structure obligation has no corresponding P representation;
the A0 catalog does not provide scopes for the matched candidate
representations; evaluator and metric identities are not fully equivalent;
and runtime application source identity is unverified. These mappings are
traceability candidates only.

## Validation

Run the focused bridge tests:

```bash
uv run python -m pytest -q --no-cov -p no:cacheprovider \
  tests/integration/test_exp03_method_bridge.py
```

The hosted `make development-quality` regression includes this suite and the
existing TEST_ONLY positive V3 integration tests. Those synthetic ACCEPT
scenarios remain separate from the real EXP-02 HOLD path and do not confer
production authority or measured readiness.
