# PILOT-02 Semantic Validation Addendum V1.1 — Scope Graph Clarification

**Status:** prospective DEVELOPMENT / TEST_ONLY clarification
**Frozen before controls:** commit containing this file
**Supersedes:** only the dependency-edge inventory interpretation in V1; all other V1 pins, controls, and decision rules remain unchanged.

The V1 instruction to enumerate direct dependency edges with both endpoints inside configured layer modules could omit intermediate modules on an indirect import path. Import Linter's `layers` contract checks indirect import chains and includes descendants of configured layers. See the [Import Linter layers contract documentation](https://github.com/seddonym/import-linter/blob/main/docs/contract_types/layers.md).

For the AC_LAYERING scope record:

1. Build the complete directed Grimp dependency graph from the pinned A0.1 application source with the lockfile-pinned Grimp 3.17. Record all graph modules and direct module-dependency edges as the graph reference, including its exact full-graph counts.
2. For each Import Linter contract, resolve each configured layer target to its graph module and all graph descendants. Record those subjects by contract and layer index.
3. Derive the contract-relevant direct edge set as the union of edges that lie on at least one directed path between subjects in two different layers of the same contract. Include path intermediates even when they are not descendants of a configured layer target. Include the per-contract source/target layer identities for each derived edge.
4. Run Grimp's pinned `find_illegal_dependencies_for_layers` on each resolved contract and preserve the actual evaluator's positive and negative outputs. The independently derived illegal dependency paths must agree with each Import Linter broken-contract result. If path closure, target resolution, or that agreement cannot be established, keep scope or adequacy unresolved.

The typed `dependency_edge.measured_count` is the number of unique directed edges in this derived contract-relevant edge set, not the count of all edges in the full application graph and not the total dependency count reported for the project. Do not convert the full-graph count into the inspected-scope count. The negative control still expects the PILOT-01 S1 Notifications repository-to-API import to produce a path and one broken Notifications contract.
