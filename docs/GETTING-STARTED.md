# Getting Started

## Prerequisites

- Windows PowerShell or another terminal
- Python 3.10 or newer available as `python`
- A local checkout of this repository

The current orchestrator does not require Azure credentials or network access.

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

## Current limitation

This is presently an orchestration MVP. It does not yet call Azure, invoke a model, teach complete lessons, or execute the planned labs. Follow the [completion Task Manifest](plans/2026-07-24-ai-103-completion-task-manifest.md) for that work.
