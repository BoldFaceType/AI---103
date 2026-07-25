# ADR 0002: Deterministic Grading and Mastery

Status: Accepted

## Context

The project will use AI tutoring, but learner scores, mastery, confidence, scheduling, and task transitions are durable state. Letting model output decide correctness would make replay, audit, and regression testing unreliable.

## Decision

All grading and learner-state mutation must be deterministic and code-owned. Models may explain, hint, ask questions, critique self-explanations, and suggest follow-up work, but model text must never directly assign scores, pass/fail decisions, mastery, confidence, or certification readiness.

## Consequences

- Rubrics must be explicit data or code.
- Lab results must contain deterministic checks and redacted evidence.
- Model output is untrusted input and must validate before display or storage.
- A failed or malformed tutor response leaves learner state unchanged.
- Tests must prove replay does not double-apply events or change scores.
