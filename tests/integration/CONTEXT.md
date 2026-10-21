# Context — `tests/integration`

> **Audience:** human developers and AI coding agents. **Type:** maintained descriptive context, not executable method input, policy approval, protocol amendment or measured evidence.
> **Navigation:** read root `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, and parent `tests/CONTEXT.md` before this file.

## Responsibility

Business API/DB integration, SPEC02 V3 synthetic pipeline, SPEC03 synthetic
orchestration through impact/candidate/governance, and EXP-03/04 evaluator
evidence bridges.

## Local landmarks

- `conftest.py`
- `test_a1_domain_events.py` — PostgreSQL preparation checks for synchronous
  handler delivery, caller-owned rollback and recovery; final Task REST wiring
  remains pending ΔA6 integration
- `test_api_flows.py`
- `test_p_applicability_v3.py`
- `test_p_governed_adaptation_v1.py`
- `test_exp03_method_bridge.py`
- `test_exp04_evidence_admission.py`
- `test_pilot02_semantic_validation.py` (real pinned evaluator controls and digest-resealed readback attacks)

## Established conventions

Use disposable DB and genuine interfaces instead of only mocked modules.

## Constraints and known gaps

Do not report integration success as G1/G4 or sample-level significance. The
SPEC03 orchestration fixtures use TEST_ONLY keys and do not grant production
trust. V3 no-op and ADD regressions verify a real synthetic evaluator, typed
impact, exact-pair evidence, candidate materialization, and (for ADD)
full-descriptor authorization. Snapshot v1.2 binds the before and after
registry closure claims independently; those two synthetic cases return
ACCEPT with V1 adapters only under TEST_ONLY trust. The separate v1.1
single-claim, incomplete-closure, and mismatched-binding cases remain
UNKNOWN/HOLD or reject before adaptation.
The integration tests also reject caller-claimed VERIFIED_V3 provenance and
detect nested input mutation after the strict V3 verifier returns a bundle;
these checks do not replace a positive approved V3 production-input path.
Coverage regressions also ensure stale or colliding pair evidence cannot
satisfy mandatory obligations. Governance regressions bind publication to an
unchanged decision digest and rollback to the exact revalidated configuration.

`test_exp03_method_bridge.py` binds EXP-02 contract artifacts to an explicit
V3 input exported from the DRAFT/OPEN policy pilot, then calls
`verify_v3_p_bundle()` and `run_adaptation()` without an evidence sidecar.
Its expected HOLD/UNKNOWN results keep this path separate from TEST_ONLY
positive fixtures; the suite also checks revision mismatch, artifact
tampering, incomplete mappings, and output digest readback.
Digest-valid manifest/trace disagreements and false source-reference claims
must fail readback. The evaluator-observation regression intentionally shows
that changing valid EXP-02 observations does not affect Method P governance;
this records the current evidence-consumption limitation, not successful
evidence-driven adaptation.

`test_exp04_evidence_admission.py` adds strict candidate identity checks,
source-revision mismatch cases, signature and missing-authority cases, and
TEST_ONLY V3 sidecar cases. The 1.1.0 cases distinguish eligibility,
authorization scope, and exact-pair consumption, including an authorized but
unconsumed sidecar. Digest-resealed manifest/trace attacks cover unauthorized
ACCEPT and unsupported consumption claims. A conforming and a nonconforming
digest-valid fixture keep observed compliance distinct from P validity; none
of these fixtures is a measured evaluator run or production authority.

## Verification and further reading

Consult the original source files and nearest relevant tests, then `docs/README.md` for repository-wide architecture, experiment, stack and verification references. DEVELOPMENT validation uses `make development-quality` with a **disposable** PostgreSQL database; it excludes the two protected DA01 test modules. When a context summary conflicts with source code, a reviewed manifest or a frozen scientific protocol, **report the conflict**; do not silently reinterpret research rules.
