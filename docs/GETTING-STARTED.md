# Getting Started

## Prerequisites

- Windows PowerShell or another terminal
- Python 3.10 or newer available as `python`
- A local checkout of this repository

The current orchestrator does not require Azure credentials or network access.

Current implementation note for 2026-07-27: offline study, lessons, deterministic assessments, tutor replay behavior, and lab fixtures do not require Azure credentials or network access. Live Azure labs and model calls remain explicit opt-in paths and can consume Azure credits or paid subscription budget.

## Initialize

From the repository root:

```powershell
python scripts/alo.py init
```

Initialization creates missing baseline folders and state without replacing existing files.

## Inspect learner state

```powershell
python scripts/alo.py status
```

The report shows the remediation threshold, mastery, confidence, open tasks, quiz count, last quiz, and processed-event count.

## Record and process a quiz

```powershell
python scripts/alo.py log vision-services 0.72
python scripts/alo.py run
python scripts/alo.py status
```

Use one of the current concept keys listed in [Configuration](CONFIGURATION.md). Scores must be decimal values from `0.0` to `1.0`.

Supply a stable event ID when importing an externally identified result:

```powershell
python scripts/alo.py log search-services 0.85 --id learn-search-001
```

Reprocessing the same event ID does not apply it twice.

## What to expect

- Scores at or above `0.80` increase mastery and confidence by `0.10`.
- Scores below `0.80` reduce mastery and confidence by `0.05`.
- Concepts below the configured remediation threshold receive generated tasks when no matching open task exists.

The remediation threshold is configured in `config/learning-policy.json`. The current default is `0.80`, so anything below 80% triggers remediation.

## Current AI-103 study workflow

Use the package entry point when the environment has been synced:

```powershell
uv run alo doctor --offline
uv run alo status
uv run alo lab run LAB-VISION-ANALYSIS --offline
uv run alo lab run LAB-MEDICAL-TEXT --offline
uv run alo lab run LAB-VECTOR-SEARCH --offline
uv run alo tutor --objective-id GA-01 --offline
```

Tested command correction: the tutor CLI uses a positional lesson ID and offline replay by default. Use this current command shape:

```powershell
uv run alo tutor GA-01 --json
```

For deterministic regression coverage:

```powershell
uv run python scripts/run_evals.py --offline
uv run pytest -m "not live_azure" -q
```

Offline lab IDs currently include `LAB-VISION-ANALYSIS`, `LAB-MEDICAL-TEXT`, `LAB-VECTOR-SEARCH`, `LAB-AGENT-WORKFLOWS`, `LAB-MEDIA-GENERATION`, `LAB-SPEECH-TRANSLATION`, `LAB-GOVERNANCE-MONITORING`, and `LAB-SEARCH-RAG`.

Live mode is intentionally not shown as a quick-start command. Before live mode, read `docs/setup/AZURE_FREE_ACCOUNT.md`, `docs/operations/COST_AND_TEARDOWN.md`, and `docs/operations/LIVE_TESTS.md`.

The limitation note below is retained from the initial ALO baseline and is superseded by the current AI-103 study workflow above.

## Current limitation

This is presently an orchestration MVP. It does not yet call Azure, invoke a model, teach complete lessons, or execute the planned labs. Follow the [completion Task Manifest](plans/2026-07-24-ai-103-completion-task-manifest.md) for that work.
