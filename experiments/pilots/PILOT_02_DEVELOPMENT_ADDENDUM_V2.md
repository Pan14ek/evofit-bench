# PILOT-02 DEVELOPMENT addendum V2

**Status:** prospective TEST_ONLY development experiment; not a protocol change for DA01.

**Purpose:** correct the V1 A0 applicability assumption, harden candidate-evaluator attribution, and execute one new continuation of the same A0 → A0.1 transition.
**Assumptions:** [PILOT_02_DEVELOPMENT_ASSUMPTIONS_V2.json](PILOT_02_DEVELOPMENT_ASSUMPTIONS_V2.json)

## Correction to V1

The V1 TEST_ONLY assumption classified both `AC_LAYERING` and `AC_MODULE_STRUCTURE` as inactive in A0. The source audit does not support that classification for `AC_LAYERING`: A0 traceability maps the horizontal layered architecture to `AC_LAYERING`; A0's fitness configuration activates architecture compliance; and the frozen A0 Import Linter configuration specifies layer rules. V1 therefore remains a preserved, reproducible planner run but is not used as evidence for the applicability of `AC_LAYERING` in A0.

V2 classifies `AC_LAYERING` as active in both states. This is an explicitly researcher-declared DEVELOPMENT assessment, not independent authority. Evaluator availability, evaluator adequacy, pair validity, and architecture compliance are assessed separately. V2 classifies `AC_MODULE_STRUCTURE` as inactive in A0 and active in A0.1 based on the monolith source state and the A0.1 state manifest's declared capability modules.

The bounded profile reuses these source records by exact digest:

| Source | SHA-256 | Role |
|---|---|---|
| `fitness/traceability/a0-traceability.yaml` | `b89b4279d86b20091a86862d5538539257dd669321d2df66138d51df98c28a08` | A0 architecture-to-obligation traceability |
| `fitness/configs/a0-monolith.yaml` | `5ad60e373463ea459e192bf85d82704ca9aa1c217c4abf4d8caeb66924059ecb` | Frozen A0 criterion and evaluator inventory |
| `fitness/evaluators/a0/importlinter.toml` | `88ff64a4792c6048a6ab0686ddf9326ebbee49f76996933845a6142cc1a2ba27` | Frozen A0 layer-check configuration |
| `architecture/states/A0_1_CAPABILITY_MODULES.yaml` | `e062c8cd0689116240bddcb4feacd5975dcf28c86a88cc11e29ebf03968d0aeb` | A0.1 state and capability-module structure |
| `fitness/catalog/architectural-obligations.yaml` | `8c5bd8fffe3bdb2af8fb85f8d0012bc34673f72866e52daed99fab96f9763011` | Obligation definitions |

## Execution and evidence rules

1. Use the frozen A0 commit and the unchanged A0.1 application tree pinned by the existing pilot profile. Record the exact clean source revision, profile, assumption, EXP-02 bundle, method-input, trace, and candidate digests.
2. Execute the unchanged frozen B0 evaluator against the same A0.1 source. Execute P through the existing V3 verifier and `run_adaptation()` path, passing the digest-validated EXP-02 observations before adaptation in a TEST_ONLY sidecar. The sidecar carries actual outputs but supplies no positive semantic proof for an EXP-02 pair.
3. Run a candidate-profile evaluator only after validating the actual materialized row against the complete pinned template and source revision. If a row or binding differs, record `not_measured` and do not run or attribute that evaluator. Record actual command, evaluator version, status, duration, stdout, stderr, and artifact digests for every run.
4. Keep full candidate validation over all active inherited representations. Missing evaluator artifacts must remain a validation failure; scoped execution of the two architecture-profile evaluators cannot convert that status to valid or authorize governance ACCEPT.
5. Report `Coverage_P`, exact pair states, B0 output, candidate evaluator observations, adaptation time, and evaluator overhead only within their evidence limits. A passing process result does not establish evaluator adequacy, semantic compatibility, coverage, or compliance. Do not derive numeric coverage without an independently established denominator and semantic evidence.
6. Do not include expected operation names, oracle/scorer data, private expected outcomes, or DA01 authorization artifacts in P inputs. Do not read or alter DA01 ground truth or expected-operation data.

No operation plan, candidate operation, evaluator verdict, or positive outcome is specified in advance. The V1 run, V1 assumptions, raw archive, and result text remain unchanged; this addendum creates a prospective V2 record for the same transition.

## Scope and limitations

This experiment measures the declared CI architecture profile. It does not run a new deployment or runtime workload. The A0 fitness inventory has four active inherited performance/reliability representations whose exact evaluator configuration and execution scope are not pinned by the source contract. Candidate validation must report their missing artifacts rather than infer commands from tool names or create substitute evaluator bindings. They remain outside the scoped architecture evaluator execution and block full candidate validation.

The development run does not establish G1, authorize G4, promote `P_ALGORITHM_STATUS`, or produce a measured DA01 result. Any external review occurs after DEVELOPMENT research execution and is outside this addendum.
