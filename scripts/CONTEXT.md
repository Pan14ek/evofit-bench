# Context — `scripts`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `CONTEXT.md` before this file.

## Responsibility

Seed/reset, metrics capture, workload runners, method prep and reproducibility tooling.

## Local landmarks

- `__init__.py`
- `check_architecture_stages.py` — W0 pinned historical A0.1/A0.2/A0.3 checks and explicit A0.1/A0.2/A0.3/A0.4 recognition; development CI pins A0.4, requires source-bound AC_PUBLIC_API and AC_MODULE_GRAPH evidence, and rejects stage downgrade or deletion of an established A0.4 manifest.
- `collect_run_metadata.py`
- `da01_contracts.py`
- `da01_execution.py`
- `export_metrics.py`
- `exp01_evidence.py`
- `exp01_evidence_contract.py`
- `exp01_evidence_runtime.py`
- `exp02_fitness_evidence.py`
- `exp03_method_bridge.py`
- `exp04_evidence_admission.py`
- `prepare_b0p_development_comparison.py`
- `verify_b0p_development_comparison.py`
- `run_b0p_development_execution.py` — continues one verified preparation with isolated B0/P arms, fresh evaluators, and a separate ZIP plus SHA-256 sidecar; direct runs require evaluator development dependencies in the host environment
- `execute_b0p_e1.py` — runs the evidence-sufficient calibration with a run-bound TEST_ONLY P input, presealed reference exclusion, independent pair readback, RQ1 gating, and clean-extraction archive verification
- `finalize_b0p_development_execution.py` — append-only recovery for the specifically bound historical a02 post-arm aggregation failure; do not use for a new direct verification
- `verify_b0p_development_execution.py` — verifies execution inputs, sealed/withheld predictions, evaluator outputs, runtime contexts, and archive inventory
- `verify_b0p_git_inventory.py`
- `../experiments/pilots/run_pilot02_method_p.py`
- `finalize_run.py`
- `prometheus_snapshot.py`

This is a selected list, not a complete source inventory.

## Established conventions

Run on disposable databases; fail clearly if required telemetry/provenance missing.

The architecture stage gate recognizes A0.4 as active while preserving the A0.3 manifest and canonical checkpoint. It runs A0.1, declared A0.2, and canonical A0.3 acceptance at their pinned revisions before accepting current A0.4 source. The A0.4 gate requires both active evaluators to be complete, source-bound, compliant, and read back successfully; AC_DATA_OWNERSHIP remains NOT_APPLICABLE.

The B0/P preparation CLI accepts full commit SHAs and writes a new, write-once
package under `experiments/results/<run-id>/`. The readback CLI independently
checks the pinned source inventories, bundles, source facts and checksum
inventory. Preparation does not run B0 or P and does not access the scorer.
The separate execution CLI consumes a verified preparation, keeps the method
containers offline, and records fresh evaluators only after both arms complete.
It does not invoke the scorer when no admissible reference was sealed before
the predictions; its archive is verified after clean extraction. The regression
forwards candidate validation from both persisted isolated-arm outputs through
manifest construction. Configure the direct-run host with its required evaluator
dependencies before starting a write-once run; a missing host tool is preserved
as an unsuccessful evaluator observation, not silently recovered.

`execute_b0p_e1.py` uses the additive E1 contract without changing the legacy
continuation. It keeps the reference outside B0/P mounts, rejects cross-run
sidecars, binds the public six-obligation denominator, and leaves RQ2 UNKNOWN
without a percentage when full independent coverage is unavailable. Its ZIP
is checked by checksum and verified after clean extraction.

## Constraints and known gaps

EXP-01/02 are A0.1 DEVELOPMENT-only. EXP-01 records the selected manual fitness reference, existing Import Linter/runtime results, and the existing module-structure test; EXP-02 binds exact result artifacts to configured representations and recomputes packaged evidence from the selected configuration and validated evaluator records. HTTP collection is bounded to loopback and missing/reset telemetry stays explicit. Runtime `source_revision` identifies the collector; the separate source-binding record captures read-only Docker endpoint/container/image identity when available. A binding mismatch invalidates the runtime record; unverified binding can preserve observations but cannot establish revision-bound semantic coverage. OCI revision labels are unauthenticated, so the current collector cannot emit verified source-revision binding. Never map execution to positive coverage, fabricate logs, ignore invalid samples or run destructive commands on real data.

EXP-03 validates the original EXP-01/02 bundle, retains its exact artifact
references, and calls the verified V3 Method P path only for an explicitly
supplied bundle. It never passes EXP-02 observations as semantic pair proof or
supplies an adaptation sidecar. HOLD, UNKNOWN, or an explicit blocker is an
expected DEVELOPMENT result. Readback re-runs the EXP-01/02 and V3 validators
for referenced inputs and checks manifest-derived fields against the exact P
trace. `EXP02_EVIDENCE_NOT_ADMITTED_TO_METHOD_P` is an explicit blocker;
`completed_with_hold` does not mean EXP-02 evidence drove adaptation. Do not
promote this diagnostic bridge to measured evidence or P readiness.

EXP-04 adds a versioned strict-mapping admission manifest and wraps the same
V3 verifier and P execution path. Its 1.1.0 DEVELOPMENT schema records
eligibility, authorization scope, and actual exact-pair consumption separately;
admission is complete only when the current P trace consumes the matching
sidecar evidence digest. A TEST_ONLY verifier can exercise this development
path but adds a research-authority blocker. The current A0.1-to-V3 canonical
mapping is unresolved, so actual EXP-02 observations remain diagnostic and P
runs without them. Readback revalidates source, sidecar, trace and generated
output references and rejects resealed cross-artifact contradictions.

## PILOT-02 execution

The PILOT-02 runner is a narrow pilot tool, not a replacement P entrypoint. It
uses the existing V3 exporter/verifier and `run_adaptation()`. The original
run keeps EXP-02 observations diagnostic. Separate TEST_ONLY continuations may
pass digest-validated execution records and raw artifacts to P before
adaptation, but they supply no positive semantic pair proof and do not establish
coverage. Candidate-profile evaluators run only after the materialized row,
source revision, artifact digests, scope, stage, covered obligation, and full
evidence contract match the pinned source profile. Scoped profile execution
does not change a failed full-candidate validation status.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. Implementation work uses `make quality` with a **disposable** PostgreSQL database. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
