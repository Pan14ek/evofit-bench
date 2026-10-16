# Controlled experiment: questions, controls, provenance and gates

This document summarizes existing protocols; it **does not authorize measured execution**. For the research rationale and formal adaptation model extracted from the working monograph, see [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md). The monograph and executable protocol contain open discrepancies in B1 cadence and RQ labels; those are registered in that document, **not** resolved here. Scientific source: `../experiments/design/ARCHITECTURE_EVOLUTION_SCENARIOS_V1.md`. DA01 procedure and status: `../experiments/execution/da01/PROTOCOL.md` and `READINESS.md`.

## Experimental subject and research questions

The scientific subject is the **method of preserving and adapting the architectural-fitness configuration Φ across architecture changes ΔA**, not business throughput optimization for its own sake. The design proposes 14 controlled deltas (`DA01`–`DA14`) from monolith through modular monolith toward distributed/cloud-native architecture.

| Question | What it measures (design, not established outcome) |
| --- | --- |
| RQ1 — Impact identification | Accuracy of identifying representations/obligations affected by ΔA: precision, recall, F1; operation accuracy |
| RQ2 — Coverage and semantic consistency | Valid coverage of required post-change obligations; invalid/stale representations, semantic-consistency violations |
| RQ3 — Detection quality | Controlled-degradation detection: precision, recall, F1, FPR, FNR, detection time |
| RQ4 — Overhead | Adaptation/CI time, runtime CPU/memory, telemetry volume, active signals/evaluators |

**Unit of analysis:** one controlled architectural delta. Individual HTTP requests, log rows and individual obligations within a single delta are **not independent architecture samples**. DA01 addresses RQ1/RQ2 only; it does not establish RQ3/RQ4 or population-level significance.

## DA01 in particular

`DA01 / ΔA1` changes *horizontal code organization* into `A0_1_CAPABILITY_MODULES` packages. Its public REST contract, shared transaction/database, application-process count, source workload, seed and core observability behavior are preserved. It does not deploy a second service or broker.

Source of the DA01 description: `../experiments/scenarios/DA01/scenario.yaml`. **Do not copy expected answers from scenario/ground truth into an implementation spec, method-input bundle, policy ruleset, documentation supplied to a P/B1 operator, or automated predictions.** The existence of those files in the repo does not grant method access to them.

## Comparison methods

- **B0**: frozen original A0 fitness configuration; no adaptation. Independently evaluate whether representations remain applicable/non-vacuous in the new state.
- **B1**: documented *human* manual procedure using an approved checklist and common normative inputs. No synthetic B1 response may be called a human result.
- **P**: proposed automatic method. Receives the same admissible common inputs as B1 and, per its allowed profile, an A0 traceability artifact. SPEC 01 validated inputs and SPEC 02 applicability are implemented; the complete P algorithm and measured B1/P comparison remain **NOT READY**.

A0 has versioned fitness elements for performance (Locust test and Prometheus runtime), reliability (pytest integration and Prometheus runtime), and architecture compliance (frozen Import Linter CI control). A declaration `representation.covers` is **not** proof of post-change coverage. RQ2 demands an independently valid evaluator execution plus a valid obligation-specific semantic verdict for each `(representation_id, obligation_id)` pair.

## Experiment lifecycle / authorization

| Gate | Meaning | Current recorded DA01 Phase A limitation |
| --- | --- | --- |
| G0 | Architecture source and provenance frozen and reviewed | Documented for recorded A0/DA01 inputs |
| G1 | Protocol, general P algorithm, scoring, missing-data behavior and independent method review frozen | **Incomplete** |
| G2 | Method allowlist/isolation negative probes | Recorded local pass; hosted Docker-specific probe previously skipped — not a hosted pass |
| G3 | Synthetic contracts, sealing, scoring, failure, and evidence rehearsal | Recorded pass for tested synthetic cases |
| G4 | Explicit human authorization for *measured* trials after review | **Not authorized** |

Always reread `READINESS.md` and actual workflows for current gate evidence. A development PR, green `make quality`, or local synthetic fixture **does not confer G4**. External monograph peer review need not block coding; independent methodology/G1 review is a separate condition for official measured DA01.

## Input isolation and policy status

The method runner uses an allowlisted read-only input bundle, separately writable output, no repo checkout, Git history, reference oracle, private scoring scripts, network or other method's output. In a measured run the Docker runtime requires a digest-pinned image and negative probes; missing Docker is an isolation failure, not a reason to downgrade boundaries.

SPEC 01: source/hash/schema integrity and scoped APA/FV/completeness verification. SPEC 02: conditions and obligations assessed as `ACTIVE`, `INACTIVE` or `UNKNOWN` using verified, versioned sources and evidence. SPEC 02's pilot policies are **all DRAFT**; its registry is **OPEN**. Synthetic test trust contexts do not constitute official approval.

New policy V3 inputs are independently bundled/hashed from architecture revisions. Both B1 and P receive equivalent normative facts/policies/conditions; P-only traceability is an approved methodological difference, not a policy-information advantage. Missing trusted approvals or closure must produce uncertainty, not fabricated inactive obligations.

## Execution provenance and raw A0 instrumentation

The benchmark provides deterministic `SEED_ID`, Locust workload profiles, optional process-local fault injection, Prometheus metrics, optional OTel exporter, application-process CPU/RSS sampling and input/output hashes. A0 smoke/baseline material is located under `experiments/evidence/a0-monolith-v1/`.

From the root README, the provisional baseline workload is a 30 s **read-only warm-up** followed by 120 s measurement (20 users, 5 users/s); smoke uses 5 users, 1 user/s, 30 s. The warm-up must not mutate the deterministic seed and there is no app restart between warm-up and measurement. These are **controlled configuration settings**, not validated performance benchmarks.

Generated run files go under ignored `experiments/results/<run-id>/`. Curated evidence carries manifests and checksums. Record pinned architecture/policy revisions, evaluator/fitness/workload configuration and digests, UTC timestamps, seed fingerprints, environment, validation reasons, rejected/uncertain cases, raw counters and failure status. Do not treat unsupported local test output, fabricated policy approval or failed/skipped runs as study results.

## Next scientific milestone

SPEC 03 must define/implement generalizable **Impact Analysis → valid candidate configuration/operation choices → governed accept/reject/rollback**, with explicit handling of blocked/UNKNOWN decisions and a versioned contract. After implementation and synthetic regression, G1/G4 review and independent sealed/scored comparisons are still separate milestones.

