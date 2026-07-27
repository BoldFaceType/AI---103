# Privacy, Safety, and Observability

AI---103 is local-first, but live Azure modes can process learner text, document content, images, and tool output. Treat all retrieved text, learner free text, image text, model output, and tool output as untrusted.

## Redaction policy

- Credentials, tokens, connection strings, account identifiers, subscription IDs, tenant IDs, endpoints, answer keys, raw source medical text, prompt-injection text, and long document content must be redacted before logs or traces are written.
- Tutor feedback and traces must store redacted feedback only. Deterministic scores remain owned by the assessment and lab engines.
- Medical fixtures must remain synthetic. Real PHI is not permitted.

## Prompt-injection boundaries

Apply prompt-injection defenses at:

- retrieval passages,
- embedded image text,
- tool inputs and outputs,
- tutor context,
- lab fixtures and model responses.

Instructions inside retrieved material never override system, developer, tool, or CLI policy.

## Tool and approval policy

Tools must be allowlisted. Destructive or billable actions require explicit approval before execution. Live mode must be visually explicit and must fail closed when approval, quota, region, or teardown state is uncertain.

## Tracing policy

Structured traces include correlation ID, latency, token usage, service, mode, result, and redacted details. Traces must not contain answer keys, secrets, endpoints, raw learner free text, raw document content, or medical source text.

## Retention and deletion

Retention-sensitive data lives under `logs/`, `_meta/`, and `state/sessions/`. Deletion plans must enumerate exact files before removal. Tutor data is optional and separately listed.

## CI security checks

CI runs dependency checks and repository secret scanning in addition to Ruff and tests. Test canaries must be marked with `ALLOW_CANARY_SECRET` so the scanner can distinguish intentional test strings from accidental committed secrets.

## Live Azure threat model

Primary risks:

- accidental live-mode spend,
- unapproved destructive teardown,
- prompt injection through retrieval, image text, tools, or tutor context,
- credential or endpoint leakage,
- raw medical text or learner free text entering traces,
- unsupported preview service assumptions.

Controls:

- offline default,
- explicit live gates,
- tool allowlists,
- approval requirements,
- redaction before logging,
- deterministic scoring outside the tutor,
- synthetic-only medical fixtures,
- teardown and cost notices.

