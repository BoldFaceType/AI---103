# Technical Design Document

## Baseline

Manifest baseline commit: `023d91c2d3946d0cb7c90a67eccb3fdb8ccc21c0`.

Current implementation commits after baseline:

- `47e0343`: froze the manifest implementation baseline.
- `35135e1`: configured project-scoped Python, pytest, Ruff, and lockfile.
- `8bdbe9b`: added offline CI, protected live test policy, and coverage tests.

The system remains a local-first filesystem application. Future work must extend the existing ALO instead of replacing it.

## Architecture

```text
alo CLI
  |
  +-- curriculum registry
  +-- learning engine
  +-- assessment engine
  +-- lab runner
  |     +-- offline fixtures
  |     +-- explicit Azure adapters
  +-- tutor
  |     +-- explicit Microsoft Foundry adapter
  +-- operations
  |     +-- doctor, cost preflight, teardown
  +-- state repository
        +-- JSON, NDJSON, snapshots, audit, vmeta
```

Deterministic code owns validation, grading, scheduling, task transitions, state persistence, mastery, and confidence. Models only explain, coach, hint, critique self-explanations, and propose follow-up practice.

## File Ownership

| Area | Files | Owner |
|---|---|---|
| CLI | `scripts/alo.py` | user workflow, command routing, offline/live flags |
| Current orchestrator | `scripts/orchestrator.py` | legacy event loop, repository methods, compatibility |
| State utilities | `scripts/state_utils.py` | atomic writes, NDJSON, audit, vmeta |
| Validation | `scripts/validators.py` | schema and trust-boundary validation |
| Merge rules | `scripts/merge_utils.py` | deterministic merge behavior |
| Curriculum | `config/curriculum.ai103.json`, `content/sources/ai103-source-registry.json`, `src/ai103/curriculum/` | official competency registry and coverage |
| Learning | `config/pedagogy.zpd.json`, `src/ai103/learning/` | spacing, interleaving, ZPD |
| Assessment | `content/assessments/`, `src/ai103/assessment/` | deterministic rubrics and grading |
| Lessons | `content/lessons/`, `content/notes/ai103/README.md` | AI-103 lesson content |
| Labs | `scripts/labs/`, `src/ai103/labs/`, `fixtures/` | offline and live lab execution |
| Azure services | `src/ai103/services/`, `infra/`, `config/services.example.json` | live adapters and infrastructure |
| Tutor | `content/prompts/tutor/system.md`, `src/ai103/tutor/` | Foundry tutoring contract |
| Operations | `src/ai103/operations/`, `docs/setup/`, `docs/operations/` | doctor, cost, teardown, live policy |
| Tests | `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/evals/`, `tests/live/` | quality gates |

## Data Flow

### Offline Study Flow

1. CLI loads curriculum, learner state, and pending events.
2. Validators check input shape and value ranges.
3. Learning engine selects due review, interleaved concepts, and ZPD scaffold level.
4. Lesson or lab runs from local content and fixtures.
5. Assessment engine grades with deterministic rubric.
6. Orchestrator writes evidence events, updates learner state, writes tasks, snapshot, audit, and vmeta.

### Live Lab Flow

1. User passes explicit `--live`.
2. Doctor verifies Azure CLI auth, tenant, subscription, region, quota, cost estimate, and required secrets.
3. CLI presents services, SKUs, estimated cost, tags, and teardown plan.
4. User confirms.
5. Lab runner creates tagged resources or uses approved existing resources.
6. Service adapter calls Azure.
7. Deterministic grader evaluates expected checks.
8. Teardown runs and verifies resource cleanup.
9. Redacted lab result is persisted.

### Tutor Flow

1. CLI selects lesson context, learner evidence summary, ZPD level, and allowed hint level.
2. Tutor adapter calls Microsoft Foundry only in approved configured mode.
3. Returned output is validated against the tutor schema.
4. Unsafe, uncited, grading, answer-key, or malformed output is rejected.
5. Accepted output is shown or stored as non-scoring feedback.

## Core Contracts

### Curriculum Entry

```json
{
  "id": "GA-04",
  "domain": "GA",
  "title": "Retrieval-augmented generation",
  "official_skill_refs": ["GA.BUILD-GEN.RAG"],
  "prerequisites": ["GA-01"],
  "lesson_path": "content/lessons/ai103/ga/GA-04.md",
  "assessment_path": "content/assessments/ai103/ga/GA-04.json",
  "lab_ids": ["LAB-SEARCH-RAG"],
  "estimated_minutes": 60,
  "source_urls": [],
  "last_verified_at": "YYYY-MM-DD"
}
```

### Learner Competency State

```json
{
  "mastery": 0.0,
  "confidence": 0.0,
  "zpd_level": 0,
  "independent_successes": 0,
  "hinted_successes": 0,
  "consecutive_failures": 0,
  "last_seen_at": null,
  "next_review_at": null,
  "spacing_stage": 0,
  "evidence_event_ids": []
}
```

### Lab Result

```json
{
  "schema_version": 1,
  "lab_id": "LAB-SEARCH-RAG",
  "mode": "offline",
  "started_at": "ISO-8601",
  "completed_at": "ISO-8601",
  "checks": [{"id": "index-created", "passed": true, "evidence": "redacted"}],
  "score": 0.0,
  "objective_ids": ["GA.BUILD-GEN.RAG", "IE.RETRIEVAL.VECTOR"],
  "resource_ids": [],
  "cost_estimate": null,
  "teardown_verified": true
}
```

### Tutor Output

```json
{
  "lesson_id": "GA-04",
  "zpd_level": 2,
  "response_markdown": "...",
  "citations": [{"title": "...", "url": "..."}],
  "hint_level": 1,
  "suggested_follow_up": "retrieval|example|self_explanation|lab",
  "safety_flags": []
}
```

## Error Handling

- Invalid local state: stop before mutation and report path plus validation errors.
- Corrupt NDJSON event: skip row, append audit entry, and continue only if deterministic state is preserved.
- Unknown legacy field during migration: stop unless a migration explicitly preserves the field.
- Missing offline fixture: fail the lab before scoring.
- Missing Azure auth: report required login or role; do not fall back to committed keys.
- Region, model, or quota unavailable: stop with exact availability error.
- Cost preflight unavailable: block live provisioning.
- Teardown failure: persist redacted failure result and report resource IDs for manual cleanup.
- Malformed tutor output: reject it and keep learner state unchanged.

## Retry Policy

- Local file writes use atomic replace and should not be retried unless the error is transient and path-scoped.
- Azure read operations may retry transient network, throttle, and 5xx errors with bounded exponential backoff.
- Azure create/update/delete operations must be idempotent by resource name and tags before retry.
- Model calls may retry transient transport and throttling errors, but not validation, safety, or policy failures.
- Grading and state updates must not retry by reprocessing the same event ID.

## Redaction Policy

Do not persist or upload:

- `.env` values, API keys, tokens, secrets, connection strings, or Azure CLI caches.
- Subscription IDs, tenant IDs, full resource IDs, or endpoint URLs unless explicitly redacted.
- Real PHI or learner answers containing sensitive data.
- Raw model prompts or completions that contain sensitive context.
- Generated Azure state outside approved redacted lab results.

CI artifacts are limited to `reports/` and must not include `state/`, `logs/`, `_meta/`, `exports/`, or Azure cache directories.

## Migration Design

State migration from the four legacy concept keys to five AI-103 domains must:

- create a timestamped backup before writing;
- support `--dry-run`;
- be idempotent;
- preserve unknown legacy fields or stop;
- keep legacy keys readable until migration succeeds;
- avoid increasing mastery from renaming alone;
- write audit and vmeta records;
- include compatibility tests before state schema changes.

## Test Boundaries

| Marker | Scope | External calls |
|---|---|---|
| `unit` | Pure functions and isolated repository fixtures | No |
| `integration` | Multi-module offline flows | No |
| `contract` | schemas, curriculum registry, lesson format, tutor output | No |
| `eval` | lesson, tutor, and lab quality checks with local fixtures | No |
| `live_azure` | real Azure and Foundry calls | Yes, manual only |

Default test execution excludes `live_azure`. Pull requests must not require Azure credentials.

## Verification Commands

```powershell
uv sync --locked --dev
uv run ruff check .
uv run pytest -m "not live_azure" --cov=scripts --cov=src --cov-fail-under=85
git diff --check
```

Live verification must use the protected workflow or an explicit local `--live` command after account, cost, and teardown preflight.
