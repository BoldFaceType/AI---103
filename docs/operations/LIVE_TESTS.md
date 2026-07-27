# Live Azure Test Policy

The default test path is offline. Pull requests and normal pushes must not deploy Azure resources, call Azure services, or require Azure secrets.

## Offline CI

Offline CI runs on Windows and Ubuntu. It performs:

- `uv sync --locked --dev`
- `uv run ruff check .`
- JSON validation for `config/objectives.ai103.json`
- `uv run pytest -m "not live_azure" --cov=scripts --cov=src --cov-fail-under=85`

Uploaded artifacts are limited to files under `reports/`. Do not upload `state/`, `logs/`, `_meta/`, `.env`, Azure CLI caches, learner answers, or generated resource state.

## Live Azure CI

Live Azure tests are opt-in only:

- Trigger: manual `workflow_dispatch`
- Input: `run_live_azure=true`
- Environment: `live-azure`
- Required env flag: `RUN_LIVE_AZURE=1`
- Required environment secrets:
  - `AZURE_TENANT_ID`
  - `AZURE_CLIENT_ID`
  - `AZURE_CLIENT_SECRET`
  - `AZURE_SUBSCRIPTION_ID`

The `live-azure` GitHub environment must require human approval before secrets are released to the job. Live tests must create uniquely named resources, apply cost controls, and tear resources down before exiting.

## Test Marker Rules

- Offline tests must not use `live_azure`.
- Tests that call Azure, deploy resources, or require Azure credentials must use `@pytest.mark.live_azure`.
- A live test must also check `RUN_LIVE_AZURE=1` before calling external services.
- Live test output must redact endpoints, subscription IDs, tokens, keys, prompts with sensitive learner data, and raw service responses that may contain user-provided content.

## Current Status

The repository currently has no live Azure tests. The protected job is present so future labs can add live checks without weakening pull-request safety.

Current reconciliation as of 2026-07-27: the repository now has live-shape fixtures and live metadata evals, but the default test path remains offline and still must not deploy Azure resources or call paid services. Any future test that makes real Azure or model calls must keep the `live_azure` marker and explicit approval gate described above.
