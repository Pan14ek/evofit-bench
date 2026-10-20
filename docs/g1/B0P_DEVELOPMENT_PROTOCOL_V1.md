# B0/P DEVELOPMENT comparative protocol v1 — prospective scope and failure rules

**Study ID:** DEV-B0P-V1
**Status:** AUTHOR-APPROVED DEVELOPMENT DESIGN, NOT YET EXECUTED.
**Research instrument:** EvoFitBench.
**P source freeze candidate:** main squash-merge commit 984f75b11b3153c52275e223ce8ec23b8d0dd0e5 (PILOT-02). The exact method manifest and evaluator digests must be recorded before any run. A changed P requires a new study/version.
**Frozen DA01 measured protocol:** experiments/execution/da01/PROTOCOL.md v1.0.0 — not amended by this file.
**Author decision:** docs/g1/B0P_AUTHOR_DECISIONS_V1.md.

## 1. Purpose and admissible claims

Test whether a version-pinned P proposes and constructs a more semantically adequate fitness-control configuration than immutable B0 after a controlled architectural transition. This is a DEVELOPMENT, descriptive calibration exercise, **not** a G4-authorized measured DA01 B0/B1/P study, independent holdout validation, or a claim of statistical superiority.

The previously examined A0 -> A0.1 transition is **development-exposed**: Method P and A0.1 evaluator templates were repeatedly refined against it during PILOT-02. Its continuation may check reproducibility or characterize a calibration case but cannot serve as a blind efficacy test. A later separately authored, prospectively sealed transition is necessary for out-of-development validation.

## 2. Research arms and baseline fairness

- **B0:** unchanged A0 configuration bytes, no adaptation; empty predicted-change list. Inspect evaluator validity on the same after architecture; a scope mismatch is NOT_EVALUABLE, not a detected architecture defect.
- **P:** run the immutable source-pinned general Method P with allowlisted facts/policies, recorded traceability permissions and shared legitimate evaluator capabilities. Preserve ACCEPT/REJECT/HOLD as separate outputs.
- **B1:** NOT RUN. A human B1 is neither synthesized nor approximated by an LLM. Three-arm DA01 remains separate.
- Both arms refer to the same before/after architecture commits and equivalent target source/evaluator observation conditions. P-only A0 traceability is a declared algorithm capability; document information asymmetry.
- No scenario.yaml, oracle, expected operations, reference scorer rules or post-hoc scoring feedback is supplied to P.
- Do not use an engineering acceptance evaluator as a substitute for frozen B0.

## 3. Questions, endpoints, and comparisons

**DEV RQ1 — affected-target and operation identification.** Scoring identity is (target_type, target_id). Use existing scorer conventions: TP, FP_in, FP_extra, FN, TN; F1=2TP/(2TP+FP_total+FN); report precision/recall where defined; retain complete operation accuracy. A private reference must be independently held outside method inputs and may only be opened after sealed prediction.

**DEV RQ2 — valid mandatory coverage.** For the complete specified post-change obligation set Q(A_after), an obligation counts once only with valid actual evaluator execution AND valid obligation-specific semantic/evidence verdict for the exact (representation_id, obligation_id, architecture_sha) pair. B0 and P use the **same full denominator**. Missing/UNKNOWN evidence does not confer coverage. The PILOT-02 diagnostic 0/2 -> 2/2 does NOT establish full DA01 coverage, whose frozen oracle has six required obligations.

**Candidate and governance diagnostics.** Record candidate structural validation, pair statuses, compliance, invariant verdicts and ACCEPT/REJECT/HOLD separately. A semantically valid but governance-HOLD candidate may be reported as a *diagnostic proposed configuration*, but never as a successfully accepted/published adaptation. Report a separate deployable/accepted configuration outcome (zero automatic accepted adaptation while HOLD). Do not turn HOLD into a successful treatment by selecting only favorable candidate rows.

**Timing/cost diagnostics.** Record method adaptation time, evaluator-execution time, verification/scoring time, CPU/RSS/telemetry when actually available. B0 adaptation time is zero by definition; it is not comparable to B0 evaluator execution duration. No synthetic cost units or lack of thresholds can justify an overhead improvement claim.

## 4. Prospective procedure

1. Freeze before/after Git SHAs, P source, frozen B0 bytes, policy and capability inventories, scoring script version and experiment protocol.
2. Declare the target source transition and contamination/exposure class before execution: CALIBRATION_EXPOSED or PROSPECTIVE_HELD_OUT. The current known DA01 belongs to CALIBRATION_EXPOSED.
3. Establish a complete, nonempty obligation denominator outside method input. Record author-declared DEV policy status separately from independently verified facts. Never infer policy authorization or negative fact completeness from a checksum.
4. Independently recompute before/after Python-module inventories directly from pinned Git trees; compare with exported fact rows before any positive extracted-fact claim. An inconsistency fails closed and retains raw diagnostic evidence.
5. Prepare B0 and P allowlisted input bundles (read-only), exclude oracle/scorer/other-arm outputs, and verify exact bytes and version bindings.
6. Compute each arm's prediction once and seal it (SHA-256, time). Do not open reference before sealing. P algorithm MAY produce HOLD; preserve it.
7. Perform independent-from-P evaluator and exact-pair evidence verification. Separate execution from compliance. Record unresolved original author/instrument authority.
8. Score only against the protected reference after both arm predictions and candidate digests have been sealed. Reuse the established scoring contracts; never change them because a result appears unfavorable.
9. Produce raw/provenance bundle and a single comparative table including incomplete/invalid/HOLD outcomes. Never overwrite previous runs.
10. Report calibrated development findings, alternative explanations, baseline viability and failure cases, without statistical significance claims.

## 5. Failure and abstention rules

- UNKNOWN/HOLD remains visible, not converted to INACTIVE, PASS or ACCEPT.
- Missing source/fact verification: reject positive source-fact admission.
- Missing independent semantic evidence: do not mark that obligation covered.
- A0 evaluator missing A0.1 packages: B0 EVALUATOR_SCOPE_MISMATCH / NOT_EVALUABLE, NOT a true architecture violation.
- Missing metric series is UNKNOWN, not zero; absent performance threshold is NOT_EVALUATED, not PASS.
- Reference-checker/scorer/infrastructure failures are distinct from methodological failures and cannot be silently removed from reports.
- The full obligation denominator must not be reduced to the two pilot pairs.
- A single architecture transition is the unit of analysis. Request count, evaluator invocations and reruns are **not independent samples**.

## 6. Evidence and output contract

Each prospective run must save at minimum: run ID, experiment ID, before and after source SHAs, P algorithm SHA, B0 configuration SHA, tool/evaluator/configuration SHAs, policy authority status, source-fact comparison, method inputs and allowlist inventories, sealed predictions and digests, candidate artifacts, raw evaluator stdout/stderr, execution/pair verdicts, governance statuses and reasons, time measurements, reference source identity and scorer version (in scorer-only custody), report, manifest and SHA-256 list.

The raw artifacts remain in immutable, separately versioned development evidence. No code or manifest may claim that a signed hash proves policy authority or method superiority.

## 7. Readiness and deferred measurements

No DEVELOPMENT B0/P comparison has been executed by creating this protocol. Before a run, implement and test the independent fact/evidence path, freeze the source/evaluator mappings and output schema, and verify that the selected scenario is not unintentionally labeled holdout. Independent reviewer, human B1, G1/G4, production authority and population inference remain outside the initial development claim.

Follow-up genuine evaluation should include new independently designed transitions and negative controls (e.g., a correct RETAIN-only transition) where their expected answers were not used to tune P. Preserve architectural transition dependence when analyzing sequential deltas.
