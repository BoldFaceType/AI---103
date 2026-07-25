# Architecture

## System boundary

AI---103 currently runs entirely from the repository filesystem. It has no database server, web service, Azure dependency, or model dependency.

```text
alo CLI
  |
  v
orchestrator
  |-- validates events and state
  |-- applies unprocessed quiz events
  |-- updates mastery, confidence, habits, and progress
  |-- creates low-mastery tasks
  |-- writes a session snapshot
  `-- appends audit and metadata records
        |
        v
JSON + NDJSON repository state
```

## Modules

| Module | Responsibility |
|---|---|
| `scripts/alo.py` | User-facing `init`, `status`, `log`, and `run` commands |
| `scripts/orchestrator.py` | Repository adapter and one-cycle orchestration |
| `scripts/state_utils.py` | Atomic JSON writes, NDJSON append/load, timestamps, audits, and hashes |
| `scripts/validators.py` | Pure schema and value validation |
| `scripts/merge_utils.py` | Profile, progress, task-state, and feedback merge rules |

## State model

- `config/objectives.ai103.json` contains the current four objective weights.
- `state/learner/knowledge-map.json` stores mastery and confidence.
- `state/learner/habits.json` stores quiz history summaries.
- `state/learner/progress.json` stores event-derived progress.
- `state/learner/meta.json` stores processed event IDs.
- `state/tasks/todo/*.json` stores generated tasks.
- `logs/events.ndjson` is the append-only event stream.
- `state/sessions/*.json` stores session snapshots.
- `_meta/audit.log` and `_meta/vmeta/*.json` provide audit and integrity metadata.

## One orchestration cycle

1. Load and validate configuration and learner state.
2. Read `logs/events.ndjson`.
3. Ignore event IDs already present in `processed_event_ids`.
4. Apply valid `quiz_completed` events.
5. Merge progress and persist learner state.
6. Generate at most three tasks for concepts below `0.50` mastery when no matching open task exists.
7. Write a timestamped session snapshot.
8. Append a `decision_made` event and audit metadata.

## Non-regression boundary

The [completion manifest](plans/2026-07-24-ai-103-completion-task-manifest.md) extends this architecture. It must preserve:

- local-first operation and offline usability;
- `alo init`, `status`, `log`, and `run`;
- idempotent event processing;
- filesystem state, snapshots, audits, and hashes;
- deterministic grading and mastery updates.

Future Azure adapters, labs, scheduling, lesson content, and tutoring sit above these foundations. Legacy concept keys transition through a backed-up, dry-run-capable, idempotent migration.

## Planned target

```text
CLI
 |-- learning engine: retrieval, spacing, interleaving, ZPD
 |-- deterministic assessment engine
 |-- lesson and curriculum registry
 |-- offline-first lab runner
 |     `-- optional explicit Azure adapters
 `-- tutor
       `-- optional explicit Microsoft Foundry model call
             |
             v
      existing filesystem state and audit layer
```

Live Azure execution is always explicit. Model feedback can coach, explain, and ask questions, but it cannot decide correctness or directly modify learner mastery.
