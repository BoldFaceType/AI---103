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

Azure integration is not implemented. Future configuration names and required values must be defined by T16–T19 of the completion manifest. Those tasks require:

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
