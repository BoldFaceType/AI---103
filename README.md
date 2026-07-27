# AI-103 Adaptive Learning Orchestrator

A local-first, filesystem-as-state learning engine for Microsoft AI-103 preparation.

The repository currently provides a working Adaptive Learning Orchestrator (ALO). JSON state, NDJSON events, generated tasks, session snapshots, audit records, and metadata hashes form its database. The existing engine remains the foundation for the planned full AI-103 study system.

## Reconciled implementation status — 2026-07-27

Use this section as the current-facing status for T30 and later work. Older status notes below are retained as historical context for the first ALO baseline.

Implemented now:

- Canonical AI-103 domain state for `PM`, `GA`, `CV`, `TA`, and `IE`, with recoverable legacy evidence from `vision-services`, `language-services`, `search-services`, and `responsible-ai`.
- Official AI-103 curriculum registry aligned to Microsoft Learn skills measured as of April 16, 2026: planning/management, generative AI and agents, computer vision, text analysis, and information extraction.
- Substantive AI-103 lesson corpus, assessment rubrics, notes hub, grounded tutor prompt, tutor safety cases, and deterministic offline tutor behavior.
- Evidence-based learning design: retrieval practice, spaced repetition, interleaving, elaboration, dual coding, self-explanation/Feynman technique, concrete examples, and ZPD scaffold levels.
- Offline-first hands-on labs and fixtures for vision analysis, synthetic medical text extraction, vector/hybrid search, agent workflows, media generation, speech translation, governance monitoring, and Search/RAG.
- Explicit live-mode guardrails: Azure setup guidance, cost warnings, Entra ID preference, no committed secrets, explicit live opt-in, teardown verification, and offline defaults.
- Deterministic eval suites for curriculum freshness, pedagogy completeness, rubric determinism, tutor grounding and injection resistance, offline/live lab parity, retrieval/RAG groundedness, agent safety, and live fixture metadata.

Current primary commands:

```powershell
uv run alo doctor --offline
uv run alo status
uv run alo lab run LAB-VISION-ANALYSIS --offline
uv run python scripts/run_evals.py --offline
uv run pytest -m "not live_azure" -q
```

Tested command correction: the tutor CLI uses a positional lesson ID. Use this current command shape:

```powershell
uv run alo tutor GA-01 --json
```

Live Azure or model calls are never implied to be free. Live work can spend Azure credits or paid subscription budget and must use the setup, preflight, approval, and teardown guidance in `docs/setup/` and `docs/operations/`.

## Current status

Implemented today:

- `alo status`, `log`, `run`, and `init`
- Mastery and confidence tracking
- Quiz logging for Vision, Language, Search, and Responsible AI
- Idempotent processing of `quiz_completed` events
- Automatic remediation tasks below the configured passing threshold, currently 80% mastery
- Learner snapshots, audit records, and SHA-256 metadata
- 40 pytest tests

Planned, not yet implemented:

- Current AI-103 curriculum and substantive lessons
- Spaced retrieval, interleaving, seven learning techniques, and ZPD scaffolding
- Microsoft Foundry model-assisted tutoring
- Offline-first and live Azure labs
- Vision, synthetic medical-text, and vector/hybrid-search scripts
- Current official AI-103 curriculum registry

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
| `< 0.80` | mastery `-0.05`, confidence `-0.05`, remediation remains due |

Tasks are generated for concepts whose mastery is below the configured remediation threshold in `config/learning-policy.json`. The default is `0.80`, so anything under 80% remains in remediation.

## Project layout

- `config/` — learner profile, objective weights, and learning policy thresholds
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
