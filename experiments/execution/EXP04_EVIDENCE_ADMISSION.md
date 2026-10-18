# EXP-04 verified evaluator evidence admission

EXP-04 is a DEVELOPMENT-only wrapper around the existing EXP-03 bridge and
SPEC 03 Method P verifier. It records validated EXP-02 observations, checks
strict identity bindings to V3 representations, and passes a sidecar to
`run_adaptation()` only after the existing V3 verifier accepts it.

## Run

First collect one unique EXP-01/02 run from a clean source checkout:

```bash
uv run python -m scripts.exp01_evidence \
  --architecture-state A0_1_CAPABILITY_MODULES \
  --fitness-config fitness/configs/a0_1-capability-modules.dev.yaml \
  --base-url http://localhost:8000 \
  --run-id <unique-exp02-run-id>
```

Prepare a verified V3 Method P input with the existing
`package_policy_source_v3()` and `export_method_inputs_v3()` APIs. Bind its
`architecture.after_commit` to the exact source revision recorded by EXP-02.
Keep the prepared input outside the repository. The policy-pilot source is
DRAFT/OPEN and does not establish production policy authority.

Write one new EXP-04 run with explicit paths:

```bash
uv run python -m scripts.exp04_evidence_admission \
  --exp02-run-dir experiments/results/<exp02-run-id> \
  --p-input-dir /private/tmp/<verified-v3-method-input> \
  --output-dir experiments/results/<unique-exp04-run-id>
```

An externally supplied V2 sidecar and verifier config are optional:

```bash
uv run python -m scripts.exp04_evidence_admission \
  --exp02-run-dir experiments/results/<exp02-run-id> \
  --p-input-dir /private/tmp/<verified-v3-method-input> \
  --evidence-sidecar /private/tmp/<external-sidecar-v2.json> \
  --trust-config /private/tmp/<test-only-verifier-config.json> \
  --output-dir experiments/results/<unique-exp04-run-id>
```

The versioned verifier-config schema accepts only `TEST_ONLY` HMAC keys
stored outside the repository; it cannot declare production trust. An
embedding caller may pass an already provisioned trust context through the
existing V3 verifier interface. EXP-04 does not create or approve a trust
anchor. Missing authority remains `authority_missing`; invalid sidecars or
signatures are rejected. Do not use a TEST_ONLY signature as research
authority.

## Output and interpretation

Each run directory is write-once and contains `admission_manifest.json`, its
SHA-256 sidecar, and `method_p_trace.json` when the verified V3 P input
executes. The manifest records:

- validated EXP-02 run and representation evidence references;
- evaluator identity, configuration and raw-output digests, metric values,
  execution verdict, and observed compliance;
- candidate P representations and each strict binding result;
- sidecar verifier identity/scope, semantic-proof status, and whether
  evaluator evidence was consumed by an exact current P pair;
- P execution/governance state and unresolved prerequisites.

`validated_observation` means EXP-01/02 contracts validated the observation.
`mapping_unresolved` means at least one exact V3 identity binding is absent
or different. `authority_missing` means the existing verifier registry did
not verify the sidecar. `admitted_execution_evidence` requires exact mapping,
verified external evidence, and actual evidence use by the existing P pair
calculation. It does not mean semantic pair validity. `rejected` means a
binding, signature, or authorization check failed.

Use `validate_admission_output(output_dir)` to read back a run. It reloads
and validates the referenced EXP-01/02 and V3 inputs, verifies the sidecar
through the same existing trust boundary, and checks manifest, trace, pair
consumption, schema, and artifact digests. Keep all referenced inputs
available for readback.

## Current limitation

The current V3 P catalog contains frozen A0 representations. The A0.1
EXP-02 configuration uses different representation and evaluator identities,
and its metric observations, criterion intent, scope, and source provenance
are not expressible in the current V3 evaluator-evidence contract. Runtime
application source identity also remains unverified without authoritative
source-to-image provenance. Therefore the checked-in configuration produces
`mapping_unresolved`; the verified EXP-02 compliance observation remains
available for inspection while Method P runs without consuming it.

EXP-02 observations never become exact-pair semantic proof. A positive pair
proof, mandatory coverage, candidate acceptance, or publication decision
requires its separate authorized V3 evidence and governance conditions.
EXP-04 never asserts `Coverage_P`, `Coverage_ref`, or measured DA01 results,
and does not change G1, G4, or `P_ALGORITHM_STATUS=NOT_READY`.
