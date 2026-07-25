## Summary

Describe what changed and whether it affects implemented behavior, planned functionality, or documentation only.

## Validation

- [ ] Relevant tests or smoke checks were run and their results are reported.
- [ ] `git diff --check` passes.
- [ ] Documentation describes current and planned functionality separately.
- [ ] No credentials, tokens, personal data, real medical records, or generated Azure state are included.

## ALO compatibility

For changes to the CLI, state, events, planner, or assessment:

- [ ] `alo init`, `status`, `log`, and `run` remain available.
- [ ] Existing learner state is preserved or migrated through backup, dry run, and an idempotent migration.
- [ ] Event replay cannot double-apply state.
- [ ] Audits, snapshots, and vmeta remain intact.
- [ ] Grading and mastery updates remain deterministic.
- [ ] Model output does not directly change learner state.

## Azure changes

- [ ] Offline mode remains the default.
- [ ] Live mode is explicit and cost risk is displayed.
- [ ] Authentication uses Microsoft Entra ID without committed secrets.
- [ ] Teardown is idempotent and deletion is verified.
