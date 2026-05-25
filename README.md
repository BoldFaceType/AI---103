# Adaptive Learning Orchestrator

A local-first, filesystem-as-state learning engine for AI-103 preparation.

## Complete Study Session Workflow

### One-time setup
```powershell
python scripts/alo.py init
```

### Every study session

**1. Check where you stand**
```powershell
python scripts/alo.py status
```

**2. After a quiz or Microsoft Learn lab — log your result**
```powershell
python scripts/alo.py log vision-services 0.72
python scripts/alo.py log search-services 0.85
```

Score is a decimal between 0.0 and 1.0 (e.g. 72% → `0.72`).

Available concepts:
- `vision-services`
- `language-services`
- `search-services`
- `responsible-ai`

**3. Process and update your learner model**
```powershell
python scripts/alo.py run
```

**4. See updated mastery and what to study next**
```powershell
python scripts/alo.py status
```

### Mastery score guide

| Score | Effect |
|---|---|
| ≥ 80% | mastery +10%, confidence +10% |
| 50–79% | mastery +2% |
| < 50% | mastery −5%, confidence −5% |

Tasks are generated automatically for any concept with mastery below 50%.

## Project layout

- `config/` learner profile and AI-103 objectives with weights
- `state/` learner model, tasks, assessments, and session snapshots
- `logs/` event stream (append-only NDJSON)
- `scripts/` orchestrator, CLI (`alo.py`), validators, merge utils
- `_meta/` audit log and per-file hash metadata (gitignored)

## Architecture

See `CLAUDE.md` for the full technical reference.