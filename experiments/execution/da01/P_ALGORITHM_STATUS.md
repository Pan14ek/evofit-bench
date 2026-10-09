# P algorithm status — NOT READY

P's input/output interface is defined in
`experiments/execution/tooling/p_interface.py`; its method input may use the A0
traceability model. No impact-analysis or adaptation algorithm is implemented.

The specification does not yet settle the following decisions:

1. A formal, reusable definition of an architecture change's `Impact` on a
   representation, including edge cases and evidence requirements.
2. General obligation activation/discovery rules and how they are frozen without
   training on the DA01 oracle.
3. Representation-to-obligation semantic mapping and stable ID/version rules
   for replacements and additions.
4. Candidate configuration generation and conflict resolution for multiple
   valid operations.
5. Governance acceptance, rejection, rollback, and failed-candidate semantics.
6. A predeclared time budget and missing-data policy suitable for comparisons.
7. Independent methodological review and a holdout policy for later deltas.

Implementing scenario-specific answers to fill these gaps would invalidate the
method. Until a separately reviewable generalized algorithm specification and
implementation exist, do not label P as implemented, validated, or ready for a
measured run.
