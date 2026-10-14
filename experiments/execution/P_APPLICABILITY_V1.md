# P Applicability Ruleset v1.0

**Status:** development candidate; synthetic/local validation only. **Implementation base:** SPEC 01 merge `850ffb78dcf2a8d925db0d060fb0b73bba4528b8`. **P algorithm:** `NOT_READY`.

## Canonical AR-DSL

The canonical AST follows the final extended “AGENT IMPLEMENTATION SPEC 02” section. A ruleset has `ruleset_version`, `snapshot_contract_id`, `fact_vocabulary_version`, `obligation_catalog_sha256`, and sorted `conditions`. Each condition has a stable `id`, per-condition `version`, `description`, sorted `fact_dependencies`, and `expression`.

The expression variants are exactly `all`, `any`, `not`, `compare`, `set_size`, and `exists`. Selectors name an FV predicate, exact `before`/`after` state and scope, and an optional exact subject. Comparisons use `comparator` plus `expected`. The earlier alternative using `fact_eq`, `fact_gt`, `fact_gte`, and `fact_in`, and its `expr` field, is not accepted. No aliases, `const`, code templates, callbacks, regular expressions, or dynamic references are supported.

This chooses the final section's `expression` field and selector AST, and adds required `version: "1.0"` and `fact_dependencies` fields to each condition to satisfy that section's rule-version/dependency requirement. `fact_dependencies` must equal the statically derived predicate set. The catalog digest is SHA-256 of the exact public `fitness/catalog/architectural-obligations.yaml` bytes. The interpreter uses JSON Schema Draft 2020-12 plus semantic type checks against the loaded FV_CORE_V1 descriptor.

The compiler caps the ruleset at 1 MiB, 128 conditions, 128 AST nodes per condition, depth 12, 256-character descriptions/selector strings, and 4,096 fact/policy/claim rows at evaluation. It rejects duplicate or unsorted condition IDs, unknown keys, unsupported FV types, invalid predicate/scope/state combinations, bool-as-number, and non-integer numeric comparisons. `compare` and `set_size` can omit `subject` only when the selected rows resolve to one subject; multiple subjects are `UNKNOWN` with a conflict/scope trace. `exists` is existential over its exact predicate/state/scope selector.

## Semantics and evidence

`TruthValue` implements Strong Kleene NOT/AND/OR. Evaluation visits all children so a decisive truth value does not discard evidence and reason traces. A conflict in an input fact forces the affected condition to `UNKNOWN`, including where ordinary Strong Kleene short-circuit algebra could otherwise yield a decisive value.

`evaluate_obligations` requires the SPEC 01 `SnapshotValidationResult`. Invalid schema or source integrity is a hard input rejection. Per-object trust is provided through immutable `EvidenceLedger` entries; they carry a verifier status, a digest of the exact fact/policy/claim, source ID-to-digest bindings, stable references, and verifier identity. No `verified: true` field is accepted from the Snapshot. Missing or mismatched proof remains undetermined.

The FV rulebook reads only the 12 activation-grade FV_CORE_V1 predicates. A known value proves comparisons only over that typed declared/extracted/observed predicate. For example, FV07 `deployment.unit_count_declared = 1` can make `>= 2` false for that declared count; it does not establish that runtime calls or services are absent. FV15–FV21 remain unavailable/reserved. `exists` returns false only when a valid exact predicate/scope/state/revision completeness claim proves absence. `not exists` inherits that evidence requirement.

For an obligation, only approved policies with valid external authority and approval proof can contribute. DRAFT is non-normative. Conditional mandates resolve a pinned condition ID. Independent mandates combine by three-valued OR. Exceptions and retirements must target explicit policy IDs, be valid for exact scope/time/state, and have a verifier proof for the specific override pair. Opposite-polarity mandates conflict unless the external ledger supplies a digest-bound precedence proof; timestamps never create precedence. Expiry uses a half-open interval: `effective_from <= as_of < effective_until`.

This v1 implementation matches policy scope exactly. It does not infer parent/child scope relationships from path strings; mismatched scopes remain `UNKNOWN`. A claimed registry closure is usable only with a verified `AUTHORITATIVE_POLICY_REGISTRY` claim for the exact obligation, its catalog criterion family, or all obligations. The all-obligations form must include the exact compiled obligation-catalog SHA-256 in its assumptions. Every form also binds exact scope, target architecture revision, registry version, and the same `as_of`. An OPEN registry or unverified closure cannot produce `INACTIVE`; absent override closure also prevents `ACTIVE`.

The result is a separate diagnostic `applicability_assessment_v1` artifact. It emits one row for every catalog obligation, sorted by ID, with ACTIVE/INACTIVE/UNKNOWN, stable reasons, policy/condition/evidence references, common semantic projection digest, ruleset digest, and optional policy bundle digest. It has no confidence score and does not modify the frozen prediction schema or choose operations.

## Separately pinned policy source candidate

`p_policy_source_v3.py` adds a strict policy-only bundle with an independent revision label and bundle SHA-256. `export_method_inputs_v3` combines it with architecture inputs pinned to their original commits. It reuses SPEC 01 typed Snapshot construction, validation, source references, and architecture inventory helpers. The existing V1 and V2 schemas/exporters and outputs are unchanged. A policy-only update changes the policy bundle digest; it cannot change either architecture source SHA or Git tree inventory.

The candidate bundle gives B1 and P the same Charter, Registry, condition catalog, completeness claims, approval/evidence bytes, and ruleset digest. B1 sees the same declarative content P evaluates. P retains only the pre-existing P-only traceability input; no oracle or expected operation enters either bundle. The policy-only bundle is built outside the architecture checkout and accepts a closed file allowlist, hashes every file, rejects symlinks and answer/oracle markers, and is verified before method use.

`experiments/execution/policy-pilot/v1/` contains **draft candidates**, not production approvals. Its Charter has no configured trust anchor, Registry is `OPEN`, and all 18 policy rows are `DRAFT`; its evidence file is a fixture provenance label only. Missing FV16–FV21 conditions are named in the separate design matrix and deliberately absent from executable AR-DSL. No policy is treated as approved and no DA01 applicability result is asserted. Test-only `EvidenceLedger` construction is synthetic and must not be used as run evidence.

## Limits and SPEC 03 boundary

With production trust anchors, per-fact verifiers, and scoped completeness verifiers absent, real decisions remain `UNKNOWN`. FV_CORE_V1 cannot establish remote synchronous calls, async channels, transaction boundaries, data ownership, actual replicas, or runtime topology. The engine never infers compliance or representation coverage from applicability.

SPEC 03 should consume `ApplicabilityAssessment` with the traceability graph, evaluator capability catalog, and current fitness state; define impact propagation, evidence-gated retain/add/replace/deactivate/adjust selection, candidate generation, HOLD/rollback behavior, and a protocol-safe adapter for UNKNOWN. It must preserve oracle separation and keep measured DA01 gated until independent policy approvals, completeness evidence, and the authorized experiment protocol exist.
