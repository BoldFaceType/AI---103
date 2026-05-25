# Changelog

## 2026-05-25 (session 2)

- feat: ALO CLI (`scripts/alo.py`) — `status`, `log`, `run`, `init` commands
- feat: Makefile `status` and `log-quiz` targets
- docs: complete study session workflow added to README
- fix: `update_vmeta`/`relative_key` accept `root` param — enables pytest isolation with `tmp_path`
- fix: `decision_made` events excluded from `processed_event_ids`
- reset: learner state and bootstrap defaults zeroed for real study use

## 2026-05-25 (session 1)

- feat: initial Adaptive Learning Orchestrator shipped and pushed to GitHub
- Filesystem-as-state orchestrator with idempotent event loop, schema validators, merge strategies, 31-test pytest suite, and Makefile
