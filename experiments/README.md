# Controlled experiments

Start each run from the deterministic `a0-v1` database seed with `make experiment-reset`. Then run a versioned Locust profile, export `/metrics`, and call `scripts/collect_run_metadata.py --run-id <id> --load-profile <profile>`. Outputs belong under `experiments/results/<run-id>/`; generated runs are ignored by Git. Fault settings are process-local, explicit, disabled by default, and should be reset after each run. Later architecture states can reuse this experiment interface; this repository implements A0 only.
