# Context — V2 pre-run sandbox preflight evidence

> **Audience:** human developers and AI coding agents. **Type:** descriptive navigation for preserved DEVELOPMENT preflight evidence; not policy approval or method input.

## Responsibility

Preserve the raw inputs, outputs, and process streams from the hosted V2 isolation preflight. The top-level `PRE_RUN_SANDBOX_PREFLIGHT.json` and its checksum sidecar are the canonical repository record; the copied sidecar names that top-level file, while this directory retains the original `sandbox-preflight.json` and its byte-matched raw sidecar with the underlying canary and runner evidence.

## Landmarks and handling

- `canaries/` contains test-only files for required-input access, protected-path denial, and output writability.
- `preflight-container-inspection.json` records the sandbox container configuration.
- `*.stdout.bin`, `*.stderr.bin`, and `network-canary-control.*.bin` preserve raw process and network-control streams.

Keep these files byte-preserved after the pre-run freeze. They do not contain actual scorer references, other-arm observations, or method results. Re-run `make test-mono-ci-psi-owner-authorized-v2` when changing the V2 preflight implementation; a changed preflight requires a new owner-authorized freeze.
