# Load profiles

The checked-in `locustfile.py` stores a fixed request mix: 25% get task, 20% list tasks, 15% create, 15% assign, 15% change status, and 10% summary. Smoke profile: 5 users, spawn rate 1/s, 30 seconds. Experiment baseline: 20 users, spawn rate 5/s, 30-second warm-up, then 120-second measurement. These are starting experiment settings, not research findings. Commands are `make load-smoke` and `make load-baseline`.
