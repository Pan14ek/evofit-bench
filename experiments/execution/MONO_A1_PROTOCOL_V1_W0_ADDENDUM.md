# MONO-A1 protocol v1 — W0 source-identity addendum 1.1

**Date:** 2026-10-23

**Applies to:** MONO-E1 ΔA4 only

**Status:** additive source-identity correction; does not authorize a study arm or reference freeze.

Read this addendum with [`MONO_A1_PROTOCOL_V1.md`](MONO_A1_PROTOCOL_V1.md) and the current [`MONO_A1_REFERENCE_FREEZE_CHECKLIST_V2.md`](MONO_A1_REFERENCE_FREEZE_CHECKLIST_V2.md). The original V1 protocol and V1 checklist remain byte-preserved historical contracts. This addendum supersedes only their E1 `UNASSIGNED` source-identity statements; every other V1 requirement and stop rule remains in force.

## Verified source pair

| Role | State | Commit SHA | Repository tree SHA | Application tree SHA |
| --- | --- | --- | --- | --- |
| Before | `A0_3_GOVERNED_MODULE_GRAPH` | `26a9bb667da7d0938e38aca15d2bf29fd1de4829` | `7b951421395f532ca403dab09d76902ff08a807d` | `b147b8961ea9e76c966663d4832e4c303581151a` |
| After | `A0_4_REPORT_QUERY_PORT` | `d3101c0d3aa9b7b709253b6ec7518416f05f65b9` | `2b436e0aaf09403ea516d73d20a466a122f86592` | `007196f68652bc13f6798805793ffdfae96f95f7` |

The before commit is an ancestor of the after commit. The canonical A0.4 checkpoint is `architecture/acceptance/a1/a0_4_canonical_checkpoint.json`, SHA-256 `7b0b0c7a0c6ac782540466d283c42d7589b8aaeb4af7df62104faa01fd154e8e`. The exact application-source patch is `architecture/acceptance/a1/a0_4_canonical_application_source.diff`, SHA-256 `6538147b9aa4fa5075314aaa54a0e24ea51f33cf0d314342e926d41dabec17ac`. The patch inventory contains two Reporting Python files; CONTEXT updates are descriptive documentation.

Current main after PR #36 is `be8ee7d44bdef343c30fd201c411c3cdff748da4`; its `app/` tree remains `007196f68652bc13f6798805793ffdfae96f95f7`. Later documentation changes therefore do not enter the A0.3→A0.4 application pair.

## Boundary

This identity correction resolves the source revision/tree fields only. It does not complete the mandatory obligation universe, approve policy authority or lifecycle stages, establish representation/evaluator semantic adequacy, freeze a P algorithm, identify E1 bundles or fixtures, authorize scorer custody, or pass `G-A1-C4-REF-FROZEN`. The checkpoint remains `NOT_READY`; no reference was created or read back by this addendum.
