# Changelog

All notable project changes are recorded here.

## Unreleased

### Documentation

- Added `docs/releases/v1.0.0-acceptance.md` with T31 offline UAT evidence, offline release gate results, and explicit pending H1/H2/H3/H4 live/release gates.
- Clarified that v1.0.0 is not release-approved until Azure account terms, live deployment, model choice, teardown/accounting, and final user acceptance are complete.
- Reconciled current-facing AI-103 documentation after T29: README, sprint plan, agent guides, testing, configuration, and getting-started docs now identify the implemented curriculum, labs, tutor, evals, and live-cost guardrails.
- Added a sprint-to-artifact matrix linking study blocks to lesson IDs, assessment paths, lab IDs, and runnable offline commands.
- Verified the current Microsoft Learn AI-103 baseline still uses skills measured as of 2026-04-16 and the five official domains/ranges already represented in the repo.
- Added configurable remediation threshold documentation and set passing/remediation to 80%.
- Added the full AI-103 completion Task Manifest with 32 ordered implementation tasks.
- Documented the current working ALO separately from planned study-system functionality.
- Added architecture, getting-started, development, testing, and configuration guides.
- Added root `AGENT.md` as an exact duplicate of the updated `CLAUDE.md` agent guide.
- Added a GitHub pull-request template with ALO compatibility, safety, and Azure checks.
- Reconciled the sprint plan from the retired AI-102 framing to the current AI-103 credential domains.
- Added explicit compatibility requirements preserving local-first state, existing CLI commands, idempotent event processing, audits, snapshots, and safe state migration.
- Documented that general Microsoft Learn Azure sandboxes are retired; live labs require an approved Azure subscription while offline fixtures remain mandatory.

### Current product status

- T31 offline UAT passes from a fresh clone, including sync, offline doctor, session workflow, retrieval prompt, lesson completion, quiz submission, tutor fixture, offline lab, review generation, idempotent replay, and learner-data export.
- Generated `decision_made` audit rows no longer advance learner `processed_event_ids`, keeping repeated `alo run` replay stable for release UAT.
- Current AI-103 domain state, lesson corpus, assessments, tutor prompt, notes hub, offline lab scripts, lab fixtures, and deterministic eval suites are implemented as of T29.
- Live Azure and model execution remain explicit, guarded, and potentially billable; offline mode is the default.
- The following three bullets are retained from the earlier ALO baseline and are superseded by the T29/T30 status bullets above.
- No Azure service calls, model invocation, substantive lesson corpus, or planned lab scripts have been implemented yet.
- The current four legacy concept keys remain unchanged pending the manifest's tested migration.
- Project-scoped pytest, Ruff, CI, and 40 tests are now in place.

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
