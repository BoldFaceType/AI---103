# Adaptive Learning Orchestrator

A local-first, filesystem-as-state learning engine for AI-103 preparation.

## Quick start

1. Initialize the workspace state:
   `python scripts/orchestrator.py --init`
2. Run one orchestration cycle:
   `python scripts/orchestrator.py`

The orchestrator reads config and state from the repository, processes new assessment events, updates learner state, plans follow-up tasks, and writes a session snapshot.

## Current scope

- Atomic JSON and NDJSON writes
- Manual schema validation for core state files
- Event idempotency via processed event ids
- Basic merge helpers for profile, progress, tasks, and feedback slices
- Sample AI-103 learner state to bootstrap local runs

## Project layout

- `config/` configuration and learner profile
- `state/` learner model, tasks, assessments, sessions
- `logs/` event stream
- `scripts/` orchestrator and support modules
- `_meta/` audit log and file metadata