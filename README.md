# AI-103 Adaptive Learning Orchestrator

A local-first, filesystem-as-state learning engine for Microsoft AI-103 preparation.

The repository currently provides a working Adaptive Learning Orchestrator (ALO). JSON state, NDJSON events, generated tasks, session snapshots, audit records, and metadata hashes form its database. The existing engine remains the foundation for the planned full AI-103 study system.

## Current status

Implemented today:

- `alo status`, `log`, `run`, and `init`
- Mastery and confidence tracking
- Quiz logging for Vision, Language, Search, and Responsible AI
- Idempotent processing of `quiz_completed` events
- Automatic study tasks below 50% mastery
- Learner snapshots, audit records, and SHA-256 metadata
- 31 pytest tests in `tests/test_orchestrator.py`

Planned, not yet implemented:

- Current AI-103 curriculum and substantive lessons
- Spaced retrieval, interleaving, seven learning techniques, and ZPD scaffolding
- Microsoft Foundry model-assisted tutoring
- Offline-first and live Azure labs
- Vision, synthetic medical-text, and vector/hybrid-search scripts
- Project-scoped Python and pytest configuration

See the [completion Task Manifest](docs/plans/2026-07-24-ai-103-completion-task-manifest.md) for the ordered implementation plan.

## Quick start

Run commands from the repository root.

```powershell
python scripts/alo.py init
python scripts/alo.py status
```

After a quiz or Microsoft Learn exercise:

```powershell
python scripts/alo.py log vision-services 0.72
python scripts/alo.py run
python scripts/alo.py status
```

Scores are decimals from `0.0` to `1.0`.

Current concept keys:

- `vision-services`
- `language-services`
- `search-services`
- `responsible-ai`

These legacy keys remain supported until the manifest's tested, idempotent migration to the five official AI-103 domains is implemented.

## Mastery rules

| Score | Effect |
|---|---|
| `>= 0.80` | mastery `+0.10`, confidence `+0.10` |
| `> 0.50` and `< 0.80` | mastery `+0.02` |
| `<= 0.50` | mastery `-0.05`, confidence `-0.05` |

Tasks are generated for concepts whose mastery is below `0.50`.

## Project layout

- `config/` — learner profile and objective weights
- `content/` — notes, prompts, and future lessons
- `docs/` — architecture, setup, development, testing, and implementation plans
- `logs/` — append-only NDJSON event stream
- `scripts/` — CLI, orchestrator, validators, merge strategies, and state utilities
- `state/` — learner model, tasks, assessments, and session snapshots
- `study-plans/` — current AI-103 study sequence
- `tests/` — orchestrator test suite
- `_meta/` — generated audit log and per-file hashes; ignored by Git

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Getting started](docs/GETTING-STARTED.md)
- [Development](docs/DEVELOPMENT.md)
- [Testing](docs/TESTING.md)
- [Configuration](docs/CONFIGURATION.md)
- [AI-103 study plan](study-plans/AI-103-sprint-plan-study-blocks.md)
- [Completion Task Manifest](docs/plans/2026-07-24-ai-103-completion-task-manifest.md)
- [Agent guidance](AGENT.md) (`CLAUDE.md` is kept as an identical compatibility copy)

## Compatibility promise

Completion work must extend, not replace, ALO. Existing state is backed up before migration; migrations must support dry runs and be idempotent; existing commands remain available; and model output never directly changes mastery or determines correctness.
