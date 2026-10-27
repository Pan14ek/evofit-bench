# Context — V2 sandbox canaries

> **Audience:** human developers and AI coding agents. **Type:** descriptive navigation for test-only isolation canaries; not protocol authority or experimental observations.

## Responsibility

Group the controlled files used to verify what the isolated V2 method runtime can read and write.

## Landmarks

- `input/` contains the benign required-input canary.
- `protected/` contains synthetic sentinels standing in for other-arm and scorer paths; these are not actual observations or reference data.
- `writable-output/` contains the permitted destination and the preflight write-probe result.

Do not add credentials, real scorer material, real other-arm data, or expected operations here. Preserve raw preflight files byte-for-byte after the freeze.
