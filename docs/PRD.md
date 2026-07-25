# Product Requirements Document

## Product Summary

AI---103 is a local-first Adaptive Learning Orchestrator for the Microsoft AI-103 credential, Microsoft Certified: Azure AI Apps and Agents Developer Associate. The current product tracks learner state, quiz events, generated study tasks, snapshots, audits, and file metadata in the repository filesystem.

The target product extends that foundation into a complete AI-103 study system with official curriculum coverage, substantive lessons, deterministic assessment, spaced review, explicit Azure labs, and grounded tutoring through Microsoft Foundry.

## Sources

Curriculum and certification claims must follow this precedence:

1. Official AI-103 study guide: <https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-103>
2. Official certification page: <https://learn.microsoft.com/en-us/credentials/certifications/azure-ai-apps-and-agents-developer-associate/>
3. Official AI-103T00-A course: <https://learn.microsoft.com/en-us/training/courses/ai-103t00>
4. Current Microsoft Learn product documentation.
5. Repository documentation.
6. Historical planning documents.

The official Microsoft Learn pages reviewed for this PRD identify AI-103 as focused on planning and managing Azure AI solutions, generative AI and agentic solutions, computer vision, text analysis, and information extraction. T04 must lock the exact current study guide into the repository registry before curriculum implementation continues.

## Current State

Implemented:

- `alo init`, `alo status`, `alo log`, and `alo run`.
- Filesystem state using JSON, NDJSON, generated tasks, snapshots, audits, and vmeta hashes.
- Idempotent `quiz_completed` event processing.
- Deterministic mastery and confidence updates.
- Low-mastery task generation.
- Project-scoped Python tooling, pytest, Ruff, and CI gates.

Not implemented:

- Current official AI-103 curriculum registry.
- Substantive AI-103 lessons and notes.
- Tutor prompt and Foundry model invocation.
- Azure service adapters.
- Hands-on Vision, medical-text, vector-search, agent, multimodal, and governance labs.
- Spaced repetition, interleaving, ZPD scaffolding, deterministic lab grading, and full learner-evidence model.
- Azure account setup, cost guardrails, live preflight, teardown, and operations docs.

## Goals

- Cover every current official AI-103 competency.
- Teach each competency with lessons, examples, diagrams, retrieval prompts, guided practice, independent practice, labs, and rubrics.
- Preserve offline usability without Azure credentials or network access.
- Support live Azure execution only after explicit user approval.
- Invoke Microsoft Foundry for tutoring and feedback without allowing model output to grade or mutate learner state.
- Use deterministic code for scoring, scheduling, mastery, confidence, ZPD level, and task transitions.
- Protect secrets, learner data, synthetic medical data boundaries, and Azure spend.
- Maintain CI, tests, documentation, and release gates.

## Non-Goals

- No web UI in the completion scope.
- No production multi-tenant service.
- No automated Azure subscription creation.
- No real protected health information.
- No committed API keys, tokens, subscription IDs, or generated Azure resource state.
- No model-determined grading or certification-readiness claims.
- No copying Microsoft Learn prose into repository lessons.

## User Personas

- Learner: studies AI-103 locally, wants adaptive tasks, clear explanations, hands-on labs, and progress tracking.
- Implementing agent: follows the Task Manifest one task at a time and needs explicit file ownership, contracts, and gates.
- Reviewer: verifies curriculum alignment, test coverage, Azure safety, and compatibility with the existing ALO.

## Functional Requirements

### FR1: Preserve Existing ALO

The system must keep the current local-first orchestrator intact.

Acceptance:

- `alo init`, `alo status`, `alo log`, and `alo run` remain available.
- Existing JSON and NDJSON state remains readable until a tested migration completes.
- Event replay remains idempotent.
- Model output cannot directly change mastery, confidence, task status, score, or pass/fail state.

### FR2: Curriculum Registry

The system must store a versioned registry of official AI-103 competencies.

Acceptance:

- Each official skill bullet maps to a stable competency ID.
- Each entry stores source URL, skills-measured date, last verification date, and normalized source hash.
- Registry updates require a diff when Microsoft changes the study guide.
- Historical planning docs cannot override official Microsoft Learn sources.

### FR3: Lessons and Notes

The system must provide substantive AI-103 content for each competency.

Acceptance:

- Each lesson includes official sources, concrete examples, worked examples, guided practice, independent practice, self-explanation prompts, answer rubrics, and at least one diagram with alt text.
- Lessons apply retrieval practice, spaced practice, interleaving, elaboration, dual coding, self-explanation, and concrete examples.
- `content/notes/ai103/README.md` becomes a navigable curriculum hub.

### FR4: Evidence-Based Learning Engine

The system must select tasks within the learner's Zone of Proximal Development.

Acceptance:

- Learner state includes mastery, confidence, ZPD level, independent successes, hinted successes, failures, last seen time, next review time, spacing stage, and evidence event IDs.
- Spacing and interleaving are deterministic and tested.
- Scaffolding fades after repeated independent success and increases after repeated failure.

### FR5: Deterministic Assessment

The system must grade lessons and labs through code-owned rubrics.

Acceptance:

- Assessment events store objective IDs, score, checks, evidence references, and rubric version.
- LLM text is treated as untrusted feedback and cannot assign scores.
- Mastery changes derive from deterministic evidence quality, recency, independence, and competency weight.

### FR6: Tutor

The system must provide grounded tutoring through Microsoft Foundry.

Acceptance:

- `content/prompts/tutor/system.md` defines tutor behavior, safety boundaries, allowed actions, citation requirements, and forbidden grading behavior.
- Tutor output validates against the documented schema.
- Tutor responses cite approved content and avoid answer-key exposure.
- Tutor responses may explain, hint, ask retrieval questions, request self-explanation, and suggest next work.

### FR7: Lab Runner

The system must run hands-on labs in offline and explicit live modes.

Acceptance:

- Offline labs run with fixtures and no network.
- Live labs require `--live`, cost preflight, Azure account verification, and explicit confirmation.
- Vision, medical-text, and vector-search scripts are implemented.
- Lab results include score, checks, objective IDs, mode, resource IDs, cost estimate, and teardown verification.

### FR8: Azure Account and Operations

The system must document and validate Azure setup without creating subscriptions automatically.

Acceptance:

- Account setup docs distinguish Azure free offers, student options, existing subscriptions, Learn exam sandbox, and historical Learn sandboxes.
- Live preflight checks tenant, subscription, region, quota, SKUs, budget alerts, and teardown plan.
- Budget alerts are described as alerts, not hard spending caps.

### FR9: Security and Privacy

The system must prevent sensitive data leakage.

Acceptance:

- No `.env`, API keys, tokens, subscription IDs, Azure CLI caches, raw learner answers, generated resource state, or real PHI are committed.
- Medical examples use synthetic fixtures only.
- Reports and CI artifacts exclude `state/`, `logs/`, `_meta/`, and Azure caches.
- Stored model and service outputs are redacted.

### FR10: Quality Gates

The system must remain testable and releasable.

Acceptance:

- `uv sync --dev` succeeds.
- `uv run pytest -m "not live_azure" -q` succeeds.
- `uv run ruff check .` succeeds.
- Offline coverage for `scripts/` and `src/` is at least 85%.
- Live tests only run through protected manual CI or explicit local `--live` commands.
- Final release requires UAT and user acceptance.

## Release Criteria

The product reaches v1.0 only when the Task Manifest T00-T31 are complete, all offline and approved live gates pass, docs are current, and the user accepts an end-to-end study session.
