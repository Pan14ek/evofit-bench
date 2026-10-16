# EvoFitBench — SPEC 03 Completion & Readiness

**ID:** SPEC_03_COMPLETION_AND_READINESS  
**Status:** PROPOSED DEVELOPMENT SPECIFICATION; **not** an approved scientific protocol, G1 sign-off, G4 authorization, or measured result.  
**Observed baseline:** \`main\` at \`197bcf9b12e4723d47b34be2da4bbc6c6c4805ba\` on 2026-10-16, after merge of PR #9. Verify current HEAD before implementation.  
**Parent documents:** \`docs/SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md\`, \`docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md\`.  
**Repository placement:** \`docs/SPEC_03_COMPLETION_AND_READINESS.md\`.

## 1. Scientific purpose, scope, and constraints

SPEC 01 validates versioned inputs, source provenance and authority; SPEC 02 evaluates applicability under three-valued logic; SPEC 03 implements typed impact, exact-pair semantics, coverage, operation planning, materialization and governed decisions. These are **DEVELOPMENT engineering results**, not evidence that P outperforms B0/B1.

The immediate problem is to establish whether method P can safely produce a **positively governed, fully evidence-backed synthetic configuration**, while refusing unauthorized evaluator templates and retaining conservative UNKNOWN/HOLD semantics. Passing such tests is a necessary software-contract condition for later scientific experimentation, **not evidence of effectiveness, superiority, or scientific novelty**.

In scope: full-template authorization binding, trustworthy TEST_ONLY positive end-to-end integration, adversarial regressions, version compatibility and isolation, complete validation records, and a G1 methodological decision register. Out of scope: new optimization methods, automatic α/θ adaptation, runtime/telemetry integration, real policy approvals, real human B1 results, new DA02–DA14 implementations, actual publication transactions, or any measured DA01 B0/B1/P execution.

**Precedence:** follow \`AGENTS.md\`, applicable \`CONTEXT.md\`, verified code/contracts, \`docs/RESEARCH_CONTEXT.md\` and the parent SPEC 03. For experimental semantics follow \`experiments/execution/da01/{PROTOCOL,INPUT_ISOLATION,SCORE_RULES,VALIDITY_RULES,READINESS,B1_CHECKLIST}.md\`. When documents disagree, log a discrepancy; **do not silently rewrite frozen science or infer permissions**.

**Forbidden:** reading/using DA01 private ground truth, oracle, reference scorer, scenario-specific expected operations, reference outputs, other methods' outputs, or engineering acceptance implementation as a solution source; tampering with frozen A0/DA01 inputs, historical tags, workloads/seeds, V1/V2/V3 contracts, scores or sealed predictions; inventing policy authorities, test outcomes, B1 operators, sign-offs or measured advantages. P may not use \`.git\`, network, oracle, scorer, or other methods' results.

## 2. Verified baseline and unresolved requirements

At authoring, \`docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md\` reports **56 PASS and 4 BLOCKED** of 60 traceability rows. This is a recorded earlier outcome, not a new rerun.

| Baseline issue | Evidence | Required disposition |
| --- | --- | --- |
| Template authorization considers artifact SHA-256 but not the full semantics-bearing descriptor | \`tooling/p_operations.py::validate_materializable_template\`, \`p_adaptation.py::_side_evidence_inputs\`, signed sidecar v1 | **Fix** before claiming materializable ADD/REPLACE is authorized. |
| Positive trusted synthetic E2E not demonstrated; current OPEN-authority integration gives HOLD | \`tests/integration/test_p_governed_adaptation_v1.py\`; \`TT-P03-45\`, \`TT-P03-47\` | **Test** actual positive verification chain; preserve negative HOLD. |
| No production-approved mandatory classification, evaluator templates, cost model or trust anchors | \`da01/P_ALGORITHM_STATUS.md\`, SPEC 03 OPEN-04/05/06 | Remain **OPEN/BLOCKED** for real approval. TEST_ONLY must not substitute. |
| Positive authorized V3 production input absent | \`TT-P03-01\` | Remain **BLOCKED** unless independently supplied authentic authority. |
| Frozen historical output byte parity not demonstrated | \`TT-P03-43\` | Remain **BLOCKED** until separately authorized independent comparison; changed-path audit is not byte parity. |
| G1 review incomplete; G4 not authorized; \`p_interface.py\` NOT_READY | \`da01/READINESS.md\`, \`P_ALGORITHM_STATUS.md\` | Do not flip gates in this work. |

## 3. S03R-A: Full-descriptor, version-bound evaluator authorization

### Requirement S03R-01 — exact semantic identity

An evaluator artifact may appear in multiple templates with different \`id\`, \`criterion\`, \`stage\`, \`evaluator\`, \`covers\`, \`applicability_scope\`, \`evidence_contract\`, \`soft_parameters\`, or other semantics-bearing attributes. **Authorization of executable bytes is not authorization of all ways to describe or deploy those bytes.**

Define a stable, documented canonical descriptor projection \`D(T)\` that includes all semantics-bearing representation/template fields, artifact path and hash, and version metadata. Any excluded field must be justified as nonsemantic and forbidden from altering operation decisions. Define:

\`template_digest = SHA256(canonical_json(D(T)))\`

An admissible template must satisfy all of the following: independently verified authorization of this **exact template descriptor**, capability-inventory provenance and digest, source-backed executable artifact bytes, applicable obligation/criterion/stage/scope, and **the exact verified input/policy/architecture context**. Evidence must have a configured external verifier (correct trust scope, signature, digest, source bindings and evaluation context), not a caller-provided boolean, \`authority_status\` string or unprivileged constructor.

### Requirement S03R-02 — no privilege escalation through hash reuse

Two descriptors that share identical executable artifact bytes but differ in \`covers\`, criterion, stage, evaluator, scope, evidence contract or soft parameters **must not share permission** by artifact hash alone. Tampering after verification, reusing evidence from a different bundle/policy/architecture, or substituting a path/bytes mapping must block the relevant ADD/REPLACE.

Audit direct public/semipublic operation-planning entry points. A freely caller-constructed digest set must not be treated as externally verified production authorization when issuing a governed ACCEPT. Preserve testability with explicit TEST_ONLY types/fixtures without granting production trust.

### Requirement S03R-03 — safe schema evolution

The existing \`p_adaptation_evidence_v1.schema.json\` has \`authorized_template_artifact_sha256\`; do not silently change the meaning of a previously signed v1 claim into full descriptor authorization. Prefer **additive, explicitly versioned DEVELOPMENT evidence/schema contracts** (e.g. v2) if necessary. Keep v1 schema and existing frozen V1/V2/V3 outputs unchanged. v1 evidence that cannot authorize a complete descriptor may still support safe diagnostic/no-op behavior, but must **not** cause a newly publishable ADD/REPLACE.

Preserve unknown → HOLD, proven invalid/fraudulent → INPUT_REJECTED or documented validation error, and exact-digest mismatch → reject/hold according to the relevant original contract. Keep reason codes deterministic and specific. Any changes to \`INV-01…INV-12\` should preserve independent invariant checks rather than replacing them with a generic boolean.

### Requirement S03R-04 — current legitimate behavior preserved

Do not require a replacement-template authorization merely to RETAIN an existing valid representation. Preserve exact-pair evidence, independent mandatory coverage, unknown/false-INACTIVE protection, bounded deterministic operation selection, signed governance ACCEPT requirement, output adapters restricted to ACCEPT, safe rollback binding, and publication-disabled status. No new authorization may relax hard constraints or criterion intent.

## 4. S03R-B: Truly positive synthetic V3 end-to-end verification

Build a **fully independent, generic, TEST_ONLY** scenario (no DA01 identifiers, ground-truth decisions, scorer answers or copied acceptance checks). Exercise the real production-shaped verification chain, not a fake object whose \`VALID\` flags were manually assigned:

\`\`\`text
Version-pinned, synthetic V3 method input
  → verify_method_bundle_v3 / verify_v3_p_bundle
  → SPEC 01 source, authority, scoped completeness validation
  → SPEC 02 before/after applicability
  → typed architectural + policy diff and criterion impact
  → exact-pair evaluator/semantic proof with real pinned bytes
  → verified mandatory coverage and required-stage contract where applicable
  → deterministic operation selection and cost bound
  → digest-bound candidate materialization and 12 invariants
  → sealed governance ACCEPT
  → accepted candidate_v1 + prediction_v1
  → deterministic auditable event/provenance
\`\`\`

An isolated synthetic signer/verifier can use a TEST_ONLY test key and independently authored test authority, **provided verification actually validates signature, context and bytes**. A verifier that always returns \`True\`, a manual \`SnapshotValidationResult(VALID,...)\`, or \`_register_test_only_bundle\` **alone** is not sufficient as evidence of a positive integration path. Keep synthetic trust strictly separate from PRODUCTION and never insert test trust keys into real authority configuration.

### Required scenarios

| ID | Scenario | Required assertion |
| --- | --- | --- |
| **SYN-POS-01** | All necessary TEST_ONLY policy/completeness/semantic evidence valid; no relevant change, or provably unaffected current control | Complete verifiable path yields ACCEPT and bound V1 outputs (with explicit retained operations if schema requires), without invented edits. |
| **SYN-POS-02** | Independently chosen architectural/policy change plus full-descriptor-authorized, real hash-pinned TEST_ONLY ADD/REPLACE evaluator | Valid candidate with fully revalidated exact pairs and mandatory coverage yields ACCEPT; if impossible without unresolved scientific choice, record **BLOCKED**, not fabricated success. |
| SYN-NEG-01 | OPEN/DRAFT or absent independent authority | UNKNOWN/HOLD; no legacy publishable candidate/prediction. |
| SYN-NEG-02 | Missing pair, stage, completeness, provenance or cost proof, one at a time | No ACCEPT; exact reason codes. |
| SYN-NEG-03 | Signed evidence replayed across architecture, policy, bundle, evaluation time, scope or verifier | No ACCEPT. |
| SYN-NEG-04 | Two templates use same executable digest but different semantics | Only independently authorized full descriptor selectable. |
| SYN-NEG-05 | Exit code zero but no resolved target/inspected subject, stale pair or absent artifact | No false valid pair or mandatory coverage. |
| SYN-NEG-06 | Policy-only revision with unchanged architecture SHA | Relevant applicability/impact recomputed; unaffected results stay stable where proven. |
| SYN-NEG-07 | Incomplete typed graph/inventory or uncertain seed | No false NOT_AFFECTED_WITH_PROOF or unjustified deactivation. |
| SYN-NEG-08 | Forged ACCEPT, mutated decision, mismatched candidate SHA, HOLD adapter or cross-configuration rollback | No publishable output or rollback authorization. |
| SYN-NEG-09 | Deterministic replay/permutation under equivalent semantic inputs | Equal canonical hashes, ordering, decisions and reason codes. |

The existing OPEN-authority HOLD integration test must continue to pass. Keep diagnostic \`AdaptationResult.candidate\` distinct from \`candidate_v1\` and \`prediction_v1\`: only a sealed, positive governance ACCEPT may expose the latter.

**Failure handling:** if the existing independent synthetic verifier interfaces cannot express the positive scenario without changing frozen contracts, do not bypass safeguards; submit a small, versioned contract proposal, document exact dependency, and leave affected row BLOCKED.

## 5. S03R-C: Regression, reproducibility, protocol preservation

1. Test authorized descriptor identity, signature/digest/source binding, equivalent-artifact substitution, stale revision/scope, stage mismatch, unauthorized criterion/obligation mapping, path traversal, source/sidecar collision, duplicate target and budget exhaustion. Demonstrate that every negative variant blocks ACCEPT and accepted V1 adapters.
2. Verify that missing facts/policies in incomplete sources remain UNKNOWN; a \`covers\` declaration, aggregate fitness score, valid candidate schema or evaluator exit code zero never independently proves mandatory coverage.
3. Test shared representations covering multiple obligations; multiple valid representations of one obligation; mandatory stage evidence when explicitly TEST_ONLY-approved; nonzero compliance violation versus evaluator infrastructure failure without changing frozen reference semantics (**OPEN-07**).
4. Run existing SPEC 01/02/03 tests, schema validation, metamorphic deterministic ordering, migration and isolation checks. The baseline application coverage gate is **not** P requirement coverage or scientific power.
5. Do not read forbidden oracle/ground-truth/scorer test contents to manufacture compatibility evidence. Protected test modules previously excluded from method-authoring verification include \`tests/unit/test_da01_execution.py\` and \`tests/unit/test_research_schema_foundation.py\`. Confirm safe execution paths, and report exclusions. Exact frozen byte-output parity (\`TT-P03-43\`) needs independently authorized verification; until then remain BLOCKED.
6. Never replace the digest-pinned Docker isolation probe with an unisolated subprocess. If image or environment is unavailable, mark SKIP/BLOCKED explicitly.
7. Keep \`PUBLISHING_ENABLED = False\` or equivalent until an actual atomic CAS writer exists. An authorization predicate is not a publication transaction.

### Requirement-to-test matrix (new IDs; do not overwrite prior 60 rows)

Every new row is **PLANNED** at specification time; assign PASS/FAIL/SKIP/BLOCKED from actual execution only.

| ID | Verification obligation | Minimum test type |
| --- | --- | --- |
| S03R-01 | Full canonical descriptor approval, including semantic fields | Unit + adversarial |
| S03R-02 | Same artifact hash / different scope, covers, stage or contract fails | Adversarial + metamorphic |
| S03R-03 | Replay, signature tampering, verifier mismatch, v1 backward-safe denial | Unit + integration |
| S03R-04 | Verified synthetic V3 no-op ACCEPT → accepted V1 outputs | Positive E2E |
| S03R-05 | Verified synthetic real-artifact ADD/REPLACE ACCEPT, or documented BLOCKED | Positive E2E |
| S03R-06 | Missing normative/semantic/cost/stage evidence → HOLD, invalid proof rejected | Negative integration |
| S03R-07 | Nonvacuity, stale exact pair, UNKNOWN and full mandatory denominator | Unit + negative |
| S03R-08 | Graph partiality, policy-only revision, multi-obligation/no-deactivate | Metamorphic + integration |
| S03R-09 | Sealed governance, wrong rollback configuration, unavailable publish | Negative security/regression |
| S03R-10 | V1/V2/V3 compatibility and permitted method-input isolation | Contract + Docker if available |
| S03R-11 | Canonical deterministic bytes/hashes with equivalent inputs | Property/metamorphic |
| S03R-12 | Complete sourced, unapproved G1 register + gate-state integrity | Documentation/test audit |

For each scenario: unique fixture ID, generic independently authored expected behavior, source SHA-256/provenance, trust scope, requirement/invariant link, preconditions, assertions, reason codes, exact command, real status, CI URL, and any unavoidable limitation.

## 6. G1 methodological preparation — document only; do not approve

Create **\`docs/G1_METHOD_DECISION_REGISTER.md\`** with heading **DRAFT — AWAITING INDEPENDENT METHODOLOGICAL REVIEW**. It must list all SPEC 03 OPEN-01…OPEN-10, cross-reference M-01…M-06 from \`docs/RESEARCH_CONTEXT.md\`, link precise authoritative sources, articulate competing options, describe scientific consequences and evidence required, identify proposed approver *roles* but **not invent approver names, decisions or signatures**, and keep all approvals pending.

Required decision entries:

| ID | Unresolved choice | Interim classification |
| --- | --- | --- |
| OPEN-01 | B1 periodic vs post-change, human time budget and exposure | PENDING_INDEPENDENT_REVIEW |
| OPEN-02 | RQ mapping, pre-registered endpoints/hypothesis family | PENDING_INDEPENDENT_REVIEW |
| OPEN-03 | Which obligations require multi-stage lifecycle proof | PENDING_INDEPENDENT_REVIEW |
| OPEN-04 | Real policy authority/trust anchors/completeness signers | PENDING_EXTERNAL_AUTHORITY |
| OPEN-05 | Real executable evaluators/templates and equal B1/P capability inventory | PENDING_EXTERNAL_AUTHORITY |
| OPEN-06 | Legitimate cost limits, per-artifact cost and bounded search | PENDING_INDEPENDENT_REVIEW |
| OPEN-07 | Architecture noncompliance vs semantic-monitoring invalidity | PENDING_INDEPENDENT_REVIEW |
| OPEN-08 | Multi-obligation ADD under frozen single-target V1 scoring | PENDING_INDEPENDENT_REVIEW |
| OPEN-09 | Independent algorithm reviewer/freeze and holdout discipline | PENDING_INDEPENDENT_REVIEW |
| OPEN-10 | Later study of α/θ adaptation, causal design, separate SPEC | DEFERRED_FUTURE_RESEARCH |

Also prepare unapproved **candidate** primary endpoints (DA01 RQ1: affected-target/operation precision, recall and F1; DA01 RQ2: independently evidenced mandatory obligation coverage), denominators, handling of UNKNOWN/HOLD/invalid or vacuous evidence, B0/B1/P comparator fairness, B1 independence and time/capability parity. Explain explicitly that manuscript and executable RQ3/RQ4 meanings differ. Propose—but **do not set as approved**—effect-size/CI/overhead-limit/independent-unit/sample-size/statistical-analysis choices. An architectural transition is the relevant independent research unit, not requests, events or obligation rows. DA01 by itself cannot establish population significance or runtime/cloud performance improvements.

Include a traceable G0–G4 gate checklist. **G1 remains INCOMPLETE; G4 remains NOT AUTHORIZED.** Do not change \`p_interface.py\` away from \`NOT_READY\` as an automatic side effect of synthetic tests. A register is preparation for human/independent review only; do not edit frozen \`da01/PROTOCOL.md\` to reconcile manuscript language.

## 7. Deliverables and implementation phases

| Phase | Deliverables | Exit evidence |
| --- | --- | --- |
| **S03R-A** | Secure full-template authorization and version-safe sidecar handling in \`tooling/p_adaptation_evidence.py\`, \`p_adaptation.py\`, \`p_operations.py\`; additive schemas if necessary | Negative authorization/cross-context tests pass, all source/context identity explicit. |
| **S03R-B** | Independent test-only signer, strict V3 synthetic bundles and real pinned evaluator fixture; positive and negative E2E tests | SYN-POS-01 passes through actual verification; SYN-POS-02 passes or specific BLOCKED documented without bypass. |
| **S03R-C** | Updated \`docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md\`, \`docs/TESTING.md\`, suitable \`CONTEXT.md\`; new \`docs/G1_METHOD_DECISION_REGISTER.md\`; accurate DEVELOPMENT status in \`experiments/execution/P_GOVERNED_ADAPTATION_V1.md\` and \`da01/P_ALGORITHM_STATUS.md\` | New S03R matrix, existing 60 TT cases preserved with actual evidence, truthful gate/readiness statements. |

Do not add a \`docs/CONTEXT.md\` absent an actual repository convention. Follow the existing hierarchical context rules for new test fixture directories. Do not put extra documentation in the exact-allowlisted policy-pilot source directory.

## 8. Validation and execution report

Read actual Makefile/test commands and \`docs/TESTING.md\`; use a disposable PostgreSQL database and permitted temporary artifacts. Candidate validation commands:

\`\`\`bash
uv sync --frozen --extra dev
uv run pytest --no-cov tests/unit/test_context_documents.py
make test-unit
make lint
make typecheck
make security
make architecture-test
make migration-test
make quality
\`\`\`

Run targeted S03R regressions and a real (permitted) digest-pinned Docker negative isolation probe. Never use the oracle/private reference scorer or inspect protected ground truth to achieve a green run. Record checks not run and exclusions separately.

**Required final PR report:** base/head commit SHA, narrow changed-file list, mapping S03R-01…12 to exact test cases and actual PASS/FAIL/SKIP/BLOCKED, old 60 TT status updates with reasons, exact fixture hashes, verifier/trust-scope conditions, canonical descriptor and artifact hashes, proof of E2E accepted V1 output identity, command output and CI URLs, Docker/DB status, frozen changed-path audit versus independent byte parity distinction, unresolved external authorities and named open decisions, G1/G4 gate status and whether P remains NOT_READY.

## 9. Exit / Definition of Done

**Engineering DEVELOPMENT readiness:**
- No artifact-hash-only template privilege escalation; all semantics-bearing descriptor claims bound to signed exact-context evidence.
- A genuine positive, independently authored, TEST_ONLY no-op ACCEPT through the actual V3-shaped verifier and SPEC 01/02/03 integration, with valid gated legacy projections.
- An attempt at real-artifact positive ADD/REPLACE with independently demonstrated TEST_ONLY authority; if impossible without new scientific decision, keep BLOCKED rather than lying.
- Safe negative UNKNOWN/HOLD/INPUT_REJECTED behavior, invariant gates, frozen compatibility and method isolation still hold.
- New S03R traceability and existing SPEC 03 60-row matrix reproducible and truthful; register of unresolved G1 issues prepared.

**Not a Definition of Done:** fully approved policies, production auth, a human B1, a scientifically frozen method, G1/G4 approval or measured DA01. These are separate milestones. Never mark the scientific experiment ready from green CI.

## 10. Agent instructions and references

1. Start from the **latest** \`main\` (merged PR #9), check current SHA, and implement on a dedicated branch/new PR; do not direct-push or merge \`main\`.
2. Read \`AGENTS.md\`, relevant \`CONTEXT.md\`, parent SPEC 03, \`docs/RESEARCH_CONTEXT.md\`, \`docs/TESTING.md\`, \`da01/PROTOCOL.md\`, \`da01/READINESS.md\`, \`da01/INPUT_ISOLATION.md\`, \`da01/B1_CHECKLIST.md\`, input validators, sidecar schema, code and tests.
3. Before code changes, produce a small gap-to-test matrix for S03R-01…12 and flag irreconcilable scientific questions.
4. Work incrementally in order S03R-A → S03R-B → S03R-C, keep DEVELOPMENT contracts versioned and additive.
5. If safe positive coverage is not provable, output HOLD/UNKNOWN or BLOCKED. Do **not** forge policy, evaluator, human or scorer evidence.
6. Push changes to the new PR and provide its evidence-rich report; do not merge without user approval.

**Canonical internal references:**
- \`docs/SPEC_03_IMPACT_ANALYSIS_AND_GOVERNED_ADAPTATION.md\`
- \`docs/SPEC_03_IMPLEMENTATION_TRACEABILITY.md\`
- \`docs/RESEARCH_CONTEXT.md\`, \`docs/TESTING.md\`
- \`experiments/execution/P_GOVERNED_ADAPTATION_V1.md\`
- \`experiments/execution/da01/{PROTOCOL,READINESS,INPUT_ISOLATION,B1_CHECKLIST}.md\`
- \`experiments/execution/tooling/p_{adaptation,adaptation_evidence,operations,semantic,impact,candidate,governance}.py\`

**State at creation:** proposed specification only. No new executable tests or measured experiment were run by writing this document; no independent scientific approval has been granted.
