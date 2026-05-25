# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```powershell
# First-time setup — creates all folders and seeds sample state
python scripts/orchestrator.py --init

# Run one orchestration cycle (process events → update learner model → plan tasks → write snapshot)
python scripts/orchestrator.py
```

All scripts must be run from the repo root. There is no build step, no venv required beyond the standard library, and no test runner yet configured.

## Architecture

**Pattern:** Filesystem-as-State with Vertical Slice Architecture. The folder tree *is* the database.

### Module responsibilities

| Module | Role |
|---|---|
| `scripts/orchestrator.py` | Entry point and loop — loads state, calls processor/planner, writes outputs |
| `scripts/state_utils.py` | All I/O primitives: `load_json`, `save_json` (atomic via `NamedTemporaryFile`), `load_ndjson`, `append_ndjson`, `update_vmeta`, `append_audit` |
| `scripts/validators.py` | Pure validation functions returning `list[str]` of errors — one function per state file type |
| `scripts/merge_utils.py` | Merge strategies per slice: profile (last-writer-wins), progress (append+recompute), tasks (state-machine transitions), feedback (append-only) |

### Data flow (one cycle)

1. `StateRepository` loads all state files from `config/` and `state/learner/`
2. `process_events()` reads `logs/events.ndjson`, skips already-processed `event_id`s (tracked in `state/learner/meta.json`), updates knowledge-map and habits for each `quiz_completed` event, merges into `state/learner/progress.json`
3. `generate_tasks()` finds concepts with `mastery < 0.5` not already in `state/tasks/todo/`, creates up to 3 task files
4. Session snapshot written to `state/sessions/<timestamp>.json`
5. `decision_made` event appended to `logs/events.ndjson`

### Idempotency

Every event must have a unique `event_id`. The orchestrator tracks all processed IDs in `state/learner/meta.json → processed_event_ids`. Re-running never double-applies an event.

### Audit & vmeta

Every `save_json` or `append_ndjson` call should be followed by `update_vmeta(path, actor)`, which writes a SHA-256 hash + timestamp to `_meta/vmeta/<flattened-path>.json`. Significant actions are also appended to `_meta/audit.log` (NDJSON) via `append_audit()`.

### Injecting a new quiz result

Append a line to `logs/events.ndjson`:

```json
{"ts":"2026-05-24T12:00:00Z","type":"quiz_completed","event_id":"quiz-002","score":0.85,"concepts":["language-services"]}
```

Then run `python scripts/orchestrator.py`. Mastery/confidence for `language-services` will increase, and a new task will be skipped for that concept if mastery reaches ≥ 0.5.

### Mastery update rules

| Score | mastery delta | confidence delta |
|---|---|---|
| ≥ 0.8 | +0.1 | +0.1 |
| 0.5–0.8 | +0.02 | — |
| ≤ 0.5 | −0.05 | −0.05 |

### Extending the orchestrator

- **New slice:** add a load/save pair to `StateRepository`, a validator in `validators.py`, and a merge rule in `merge_utils.py`.
- **New event type:** handle it in the `process_events()` loop alongside `quiz_completed`.
- **New task type:** adjust `build_task()` and `generate_tasks()` in `orchestrator.py`.
