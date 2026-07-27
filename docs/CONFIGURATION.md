# Configuration

## Current configuration

The current ALO needs only Python and repository files. Run commands from the repository root.

| Path | Purpose |
|---|---|
| `config/profile.user.json` | Learner profile |
| `config/objectives.ai103.json` | Current objective weights |
| `config/learning-policy.json` | Passing and remediation threshold policy |
| `state/learner/*.json` | Learner state and processed-event metadata |
| `logs/events.ndjson` | Input and decision events |

The current objective keys are:

- `vision-services`
- `language-services`
- `search-services`
- `responsible-ai`

Do not rename these keys manually. Their replacement by the five official AI-103 domains requires the manifest's state migration.

Current reconciliation as of 2026-07-27: the schema v2 learner knowledge map now uses canonical AI-103 domains `PM`, `GA`, `CV`, `TA`, and `IE`; the four legacy concept keys remain as migration evidence and compatibility aliases, not as the curriculum source of truth.

The canonical curriculum configuration is `config/objectives.ai103.json`, backed by `content/sources/ai103-source-registry.json`. The source-precedence rule remains: official Microsoft AI-103 study guide first, then certification/course pages, then repo manifest and study plan.

## Learning policy

`config/learning-policy.json` currently defines:

```json
{
  "remediation_threshold": 0.8
}
```

Scores and mastery below `0.80` are considered remediation. Scores at or above `0.80` are passing.

## Runtime

The source currently uses the Python standard library. Project-scoped test and lint dependencies are managed through `uv`.

## Generated state

`state/sessions/`, `_meta/`, `exports/`, `tmp/`, Python bytecode, and pytest cache are ignored by Git. Learner-state files already tracked by Git should be treated as data, not hand-edited configuration.

## Planned Azure configuration

The older planning note below is retained for baseline history and is superseded by the current reconciliation sentence that follows it.

Azure integration is not implemented. Future configuration names and required values must be defined by T16–T19 of the completion manifest. Those tasks require:

Current reconciliation as of 2026-07-27: guarded Azure configuration scaffolding and offline/live lab boundaries exist. Live execution still requires explicit learner approval, valid Azure setup, and potentially billable resources; offline fixtures remain the default path.

- an approved Azure subscription;
- Microsoft Entra ID authentication;
- no committed keys, tokens, or connection strings;
- explicit offline and live modes;
- cost, quota, region, and teardown preflight checks.

Do not add real values to `.env`, Markdown, fixtures, events, audits, or learner state.

## Precedence

For curriculum claims, use this order:

1. Current official Microsoft AI-103 study guide.
2. Current certification and course pages.
3. Repository completion manifest.
4. Repository study plan.
5. Historical notes.

If an official source changes, stop and update the curriculum registry and documentation together.
