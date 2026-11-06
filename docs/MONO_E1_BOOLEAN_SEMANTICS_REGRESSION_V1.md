# MONO-E1: Boolean-confirmation regression and EvoFitBench decision parity (DEVELOPMENT)

**Status:** regression contract proposed; CI run and independent methodological approval pending.  
**Scope:** mathematical descriptions of monograph formulas (3), (7), (10) and Method P governance decision precedence.  
**Source:** `Pan14ek/evofit-bench`, branch `test/binary-semantics-equivalence-monograph`.  
**Does not change:** Method P production code, monograph data, source evidence, reference labels, policy authority, frozen experimental artifacts, or the eight-scenario results.

## Research question

Can the monograph express predicate truth with ordinary Boolean conditions and represent insufficient evidence as a separate **evaluation status**, while preserving the observable behavior of the current implementation?

This is a question of **bounded observational equivalence**, not a proof of equivalence of every possible policy, candidate or workflow. The implementation still contains Strong Kleene operators internally. The manuscript's simplified language does not assert they were removed from source code.

## Semantic crosswalk

| Layer | Existing implementation | Manuscript's Boolean-confirmation abstraction |
| --- | --- | --- |
| Condition result | `TruthValue.TRUE/FALSE/UNKNOWN` | Positive and negative Boolean confirmation flags `(t,f)` |
| Confirmed true | `TRUE` | `(1,0)` |
| Confirmed false | `FALSE` | `(0,1)` |
| Insufficient or conflicting evidence | `UNKNOWN` | `(0,0)`, **not** a third predicate truth value |
| Contradictory confirmations | Not a legal single `TruthValue` | `(1,1)` is forbidden by the abstraction |
| Applicability of obligation | `ACTIVE / INACTIVE / UNKNOWN` | Procedural status derived from positive/negative confirmation |
| Candidate governance | `ACCEPT / HOLD / REJECT / INPUT_REJECTED` | Decision protocol separate from mathematical predicates |
| Missing evaluator | No configured representation | `NOT_CONFIGURED`: configuration state, not failure/unknown truth |
| Technically unusable inspection | E.g. `NOT_EVALUABLE` in the A1 acceptance layer | Execution validity, separate from compliant/non-compliant |
| `INACTIVE` obligation | Confirmed normative non-applicability | Not equivalent to `NOT_CONFIGURED` or lack of evidence |

For expression conjunction, the independent Boolean encoding uses `t=AND(t_i)`, `f=OR(f_i)`; for expression disjunction, `t=OR(t_i)`, `f=AND(f_i)`; negation swaps the flags. These definitions coincide with the corresponding existing `tri_and`, `tri_or`, `tri_not` outputs for the three representable statuses.

For monograph rule (10), only the positive conjunction is an **acceptability confirmation**. Its failure does not by itself prove a disqualifying violation. A separate priority-ordered governance rule distinguishes confirmed prohibition, unresolved prerequisites and confirmed admissibility.

## Concrete regression checks

Implementation: [tests/unit/test_monograph_boolean_semantics_regression.py](../tests/unit/test_monograph_boolean_semantics_regression.py).

1. **Expression logic:** all nine two-input combinations for `tri_and` and `tri_or`, plus `tri_not`; and all `3^6 = 729` combinations of six acceptance gates (rule 10).
2. **Formula (3):** complete/incomplete inspection crossed with zero, one, and three violations. The Boolean result is established only with adequate inspection; insufficient evidence remains an assessment status.
3. **Formula (7):** 31 possible-world sets of sizes 0..4. The old textual `1/0/U` applicability rule maps exactly to procedural `ACTIVE/INACTIVE/UNKNOWN` in this finite domain. This does **not** prove the production policy-authority implementation enumerates worlds or is globally equivalent.
4. **Actual applicability evidence:** a missing fact stays unresolved, proven scoped absence becomes a confirmed negative, and conflicting functional facts stay unresolved with a conflict reason.
5. **Governance precedence matrix:** covers authorized and unauthorized ACCEPT, invalid inputs, unresolved inputs, PASS/FAIL/UNKNOWN and missing invariant verdicts, complete/incomplete/unresolved coverage, invalid/unvalidated/absent candidates, cost fail/unknown, hold/reject plans, additional unresolved evidence, and the precedence of proved prohibition over HOLD.
6. **Archived scenarios:** checks all three recorded repetitions of A1, A2, B1, B2, C1, C2, D1, D2 and compares the independent Boolean-decision projection with historical recorded operation and governance outcomes.
7. **Scientific integrity:** explicitly asserts the D2 author-declared reference remains `hold/HOLD` while the recorded implementation returned `hold/REJECT`.

## Historical scenario crosswalk

| Scenario | Recorded operation | Author-declared governance | Recorded governance | Implication |
| --- | --- | --- | --- | --- |
| A1 / A2 | retain | ACCEPT | ACCEPT | Same checks, reassessed candidate accepted |
| B1 / B2 | add | ACCEPT | ACCEPT | Newly justified control proposed |
| C1 / C2 | replace | ACCEPT | ACCEPT | Inadequate pair replaced under exact successor evidence |
| D1 | hold | HOLD | HOLD | Missing/unresolved evidence; no proven rejection |
| D2 | hold | HOLD | REJECT | Proven invariant failures override unresolved evidence |

The 24 repetitions belong to **eight distinct scenarios**; three runs per scenario are technical repeats, not 24 independent cases. Historical agreement remains operations `24/24` and combined operation/governance `21/24`. These figures must not be rewritten or represented as performance improvement.

## Key implementation anchors

- `experiments/execution/tooling/p_applicability.py`: `TruthValue`, `tri_and`, `tri_or`, `tri_not`, fact/closure/conflict evaluation.
- `experiments/execution/tooling/p_semantic.py`: representation validity, evidence and mandatory coverage assessments.
- `experiments/execution/tooling/p_governance.py`: input rejection → proven prohibition → unresolved confirmation → governed ACCEPT.
- `experiments/execution/tooling/p_adaptation.py`: candidate preparation, twelve named `INV-01..12` checks and governance authorization.
- `experiments/pilots/mono_e1_dev_p_decisions_v1/`: frozen author-declared reference and retained `run_v1/raw` records.

## Reproduction

Run from the repository root with the locked DEVELOPMENT dependencies:

```bash
uv sync --frozen --extra dev
uv run --frozen --extra dev pytest -q tests/unit/test_monograph_boolean_semantics_regression.py
uv run --frozen --extra dev ruff check tests/unit/test_monograph_boolean_semantics_regression.py
```

The main CI workflow also runs `make development-quality` on PRs. **No test execution or green CI state is claimed by this document until the corresponding GitHub Actions check completes.**

## Interpretation and limitations

- The Boolean-pair translation is **truth-table equivalent** to the current finite expression operators on their supported states.
- The governance regression tests establish **decision parity for the enumerated gate combinations and archived scenario traces**.
- The tests do **not** establish equivalence for every possible policy graph, authority source, signature, stage contract or candidate representation.
- Formal rule (7) is a conceptual abstraction of applicability; production policy evaluation includes verified registry closure, authority, conflict resolution and precedence that are not fully captured by world enumeration.
- The source code still uses three-way internal results. Their status nature must be explained transparently if the simplified manuscript is presented as an abstraction of that code.
- The implementation's D2 disagreement with the author-declared reference is preserved, not corrected.
- No new experiment, independent baseline or deployment/runtime verification is performed.

## Suggested acceptance criteria

1. Focused tests and repository quality gates pass on the PR branch.
2. A reviewer confirms that all tests compare against preserved historical inputs rather than revised labels.
3. The manuscript describes Boolean truth, evaluation status and governance outcome as different types.
4. Formula (10) never conflates lack of positive evidence with a confirmed rejection.
5. The manuscript's figure 1 is separately redrawn to show HOLD → new evidence → re-evaluation; this regression change does not edit the figure.
6. No assertion of whole-method equivalence, improved performance, or independent validation is made solely from these regression tests.
