# Development

## Working rules

- Run commands from the repository root.
- Preserve existing learner state and unrelated changes.
- Keep writes atomic through `scripts/state_utils.py`.
- Validate trust-boundary input before applying it.
- Record significant state changes in audit and vmeta.
- Keep scoring, grading, scheduling, and mastery updates deterministic.

## Extending the current orchestrator

For a new state slice:

1. Add load/save methods to `StateRepository`.
2. Add a pure validator to `scripts/validators.py`.
3. Add the merge policy to `scripts/merge_utils.py`.
4. Write audit and vmeta after persistence.
5. Add tests using an isolated `tmp_path` repository.

For a new event:

1. Define required fields and validation.
2. Handle it in `process_events()`.
3. Add its ID only after successful processing.
4. Prove replay does not double-apply it.

For a new task type, update `build_task()`, `generate_tasks()`, validation, and tests together.

## Compatibility

Do not remove or silently redefine `alo init`, `status`, `log`, or `run`. The planned curriculum migration must:

- back up state;
- offer `--dry-run`;
- preserve unknown legacy fields or stop;
- be idempotent;
- leave existing status reporting functional.

## Documentation

When behavior changes, update:

- `README.md` for user-facing status and workflow;
- `docs/ARCHITECTURE.md` for structure and data flow;
- `docs/CONFIGURATION.md` for settings and boundaries;
- `docs/TESTING.md` for validation commands;
- `CLAUDE.md` for agent guidance;
- `CHANGELOG.md` for notable changes;
- the study plan and Task Manifest when scope or sequencing changes.

Never describe planned functionality as implemented.
