# Testing

## Current suite

The pytest suite contains 40 tests covering:

Current reconciliation as of 2026-07-27: the offline suite has expanded beyond the original 40-test ALO baseline to cover AI-103 curriculum, lesson contracts, assessment rubrics, tutor safety, lab grading, Azure guardrails, redaction, tracing, and eval regression reporting. Treat the 40-test list below as historical baseline coverage that must remain protected.

- state repository reads and writes;
- event validation and processing;
- score boundaries, remediation thresholds, and mastery updates;
- idempotent event handling;
- task generation;
- session snapshots;
- merge strategies and invalid task transitions.

## Current command

From the repository root:

```powershell
uv run pytest -m "not live_azure" -q
```

T30 verification also uses:

```powershell
uv run python scripts/run_evals.py --offline
uv run pytest tests/evals -q
uv run ruff check .
git diff --check
```

The eval runner prints a JSON report with explicit suite thresholds and exact failed case IDs. It must not use an aggregate “LLM says pass” gate.

The Makefile equivalent is:

```powershell
make test
```

Do not report the suite as passing unless the command actually completes successfully.

## Read-only smoke check

The CLI status command is a safe smoke check:

```powershell
python -B scripts/alo.py status
```

It confirms imports and state reads, but it does not replace the test suite.

## Planned test policy

The default suite must remain offline and exclude `live_azure`. Live tests require explicit credentials, cost approval, preflight checks, and teardown verification.

Target offline command:

```powershell
uv run pytest -m "not live_azure" -q
```

## Documentation validation

Before publishing documentation:

```powershell
git diff --check
rg -n "AI-102|Add lesson notes here|Describe tutoring instructions here" .
```

Intentional historical or migration references must be clearly labeled.
