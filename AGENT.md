# Repository Agent Guide

This repository contains a working local-first Adaptive Learning Orchestrator (ALO) and a documented plan to expand it into a full Microsoft AI-103 study system.

## Product status

Implemented:

- `scripts/alo.py` commands: `init`, `status`, `log`, `run`
- Filesystem-as-state JSON and NDJSON persistence
- Idempotent `quiz_completed` processing
- Deterministic mastery and confidence updates
- Automatic remediation tasks below 80% mastery by default
- Session snapshots, audit records, and SHA-256 vmeta

Planned but not implemented:

- Current AI-103 lesson corpus and assessments
- Spacing, interleaving, the seven learning techniques, and ZPD scaffolding
- Azure service calls and cost-guarded infrastructure
- Microsoft Foundry tutor invocation
- Vision, synthetic medical-text, and vector-search labs
- Project-scoped pytest configuration

Never describe planned functionality as present.

## Commands

```powershell
python scripts/alo.py init
python scripts/alo.py status
python scripts/alo.py log vision-services 0.72
python scripts/alo.py run
```

Direct orchestrator commands:

```powershell
python scripts/orchestrator.py --init
python scripts/orchestrator.py
```

Run scripts from the repository root.

## Current architecture

The folder tree is the database.

| Module | Responsibility |
|---|---|
| `scripts/alo.py` | User-facing CLI |
| `scripts/orchestrator.py` | State repository and orchestration cycle |
| `scripts/state_utils.py` | Atomic JSON, NDJSON, timestamps, audit, and vmeta |
| `scripts/validators.py` | Pure validation functions returning `list[str]` |
| `scripts/merge_utils.py` | Profile, progress, task, and feedback merge rules |

One cycle:

1. Load and validate state.
2. Read `logs/events.ndjson`.
3. Skip event IDs already in `state/learner/meta.json`.
4. Apply valid `quiz_completed` events.
5. Persist learner state and progress.
6. Generate at most three tasks for concepts below the configured remediation threshold, currently `0.80` mastery.
7. Write a timestamped session snapshot.
8. Append a `decision_made` event, audit records, and file hashes.

## Invariants

- Event processing remains idempotent.
- Writes use `state_utils.py` and remain atomic.
- Significant writes receive audit and vmeta records.
- Model output never grades correctness or directly changes mastery.
- Live Azure mode is explicit; offline mode is the default.
- Never commit credentials, real medical records, or sensitive learner data.
- Synthetic fixtures only for medical-text work.

## Compatibility contract

Completion work extends ALO; it does not replace it.

- Preserve `alo init`, `status`, `log`, and `run`.
- Back up state before migration.
- Provide migration dry runs.
- Make migrations idempotent.
- Stop rather than discard unknown legacy fields.
- Keep existing status reporting functional after migration.
- Preserve snapshots, audits, hashes, and deterministic state transitions.

## Extending ALO

- New state slice: add repository methods, validation, merge policy, audit/vmeta, and tests.
- New event type: validate it, process it once, and prove replay safety.
- New task type: update task construction, planning, validation, and tests together.
- New Azure adapter: provide offline fixtures, explicit live mode, Entra ID authentication, cost preflight, and teardown.
- New tutor behavior: ground it in approved curriculum; keep grading deterministic.

## Documentation map

- `README.md` — user-facing overview and current status
- `docs/ARCHITECTURE.md` — system structure and data flow
- `docs/GETTING-STARTED.md` — local usage
- `docs/DEVELOPMENT.md` — contribution and compatibility rules
- `docs/TESTING.md` — current and target validation
- `docs/CONFIGURATION.md` — current and planned settings
- `study-plans/AI-103-sprint-plan-study-blocks.md` — current curriculum sequence
- `docs/plans/2026-07-24-ai-103-completion-task-manifest.md` — authoritative implementation backlog

Update related documentation and `CHANGELOG.md` whenever behavior, scope, or status changes.
