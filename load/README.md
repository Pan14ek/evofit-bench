# Load profiles

Versioned profiles are in `profiles/`. The measured baseline uses 20 users and spawn rate 5/s for 120 seconds, after a 30-second read-only warm-up on the same app process. The measured request mix is 25% get task, 20% list tasks, 15% create, 15% assign, 15% change status, and 10% summary. Smoke uses 5 users at 1/s for 30 seconds. These are versioned engineering controls, not scientific findings.

Task IDs are UUIDv5 values generated from the application `SEED_ID`; this variable must match the seed used for reset. Locust's task scheduling and wait times retain stochastic variation, so this profile does not claim exact request-order replay. Runtime process metrics are sampled from `/metrics`; before/after Prometheus snapshots exclude warm-up counters from measured interval deltas. HTTP metric labels use route templates and `traffic_class` values `business`, `operational`, `experiment`, or `unmatched`.
