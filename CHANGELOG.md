# Changelog

All notable project changes are recorded here.

## Unreleased

### Documentation

- Added the full AI-103 completion Task Manifest with 32 ordered implementation tasks.
- Documented the current working ALO separately from planned study-system functionality.
- Added architecture, getting-started, development, testing, and configuration guides.
- Added root `AGENT.md` as an exact duplicate of the updated `CLAUDE.md` agent guide.
- Added a GitHub pull-request template with ALO compatibility, safety, and Azure checks.
- Reconciled the sprint plan from the retired AI-102 framing to the current AI-103 credential domains.
- Added explicit compatibility requirements preserving local-first state, existing CLI commands, idempotent event processing, audits, snapshots, and safe state migration.
- Documented that general Microsoft Learn Azure sandboxes are retired; live labs require an approved Azure subscription while offline fixtures remain mandatory.

### Current product status

- No Azure service calls, model invocation, substantive lesson corpus, or planned lab scripts have been implemented yet.
- The current four legacy concept keys remain unchanged pending the manifest's tested migration.
- Project-scoped pytest installation remains planned; the repository still contains 31 pytest tests.

## 2026-05-25 (session 2)

- Added the ALO CLI (`scripts/alo.py`) with `status`, `log`, `run`, and `init`.
- Added Makefile `status` and `log-quiz` targets.
- Added the complete study-session workflow to the README.
- Updated `update_vmeta` and `relative_key` to accept `root`, enabling pytest isolation with `tmp_path`.
- Excluded `decision_made` events from `processed_event_ids`.
- Reset learner state and bootstrap defaults for real study use.

## 2026-05-25 (session 1)

- Shipped the initial Adaptive Learning Orchestrator.
- Added filesystem-as-state orchestration, an idempotent event loop, schema validators, merge strategies, a 31-test pytest suite, and a Makefile.
