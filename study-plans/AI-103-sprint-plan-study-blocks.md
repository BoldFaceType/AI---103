# AI-103 Sprint Plan and Study Blocks

Status: curriculum-aligned plan; lesson and lab implementation pending
Target: Microsoft Certified: Azure AI Apps and Agents Developer Associate
Source baseline: official AI-103 skills measured as of 2026-04-16

Implementation status as of 2026-07-27: the repository now contains the AI-103 domain registry, schema v2 learner state, substantive lessons, deterministic assessments, offline lab scripts, guarded tutor behavior, and offline evaluation suites. Older “pending” notes in this file are historical planning context; this reconciliation block is the current status baseline.

Official Microsoft Learn still lists these AI-103 skill ranges for the current study guide baseline: Plan and manage an Azure AI solution 25–30%, Implement generative AI and agentic solutions 30–35%, Implement computer vision solutions 10–15%, Implement text analysis solutions 10–15%, and Implement information extraction solutions 10–15%.

## Purpose

Build exam readiness through short cycles of substantive instruction, retrieval practice, hands-on work, deterministic assessment, and scheduled review. This plan replaces the repository's historical AI-102 framing.

The working Adaptive Learning Orchestrator remains the learner-state engine. Until its migration is implemented, it continues using the four legacy keys `vision-services`, `language-services`, `search-services`, and `responsible-ai`.

## Current AI-103 domains

| Domain | Official range | Planning weight |
|---|---:|---:|
| Plan and manage an Azure AI solution | 25–30% | 27.5% |
| Implement generative AI and agentic solutions | 30–35% | 32.5% |
| Implement computer vision solutions | 10–15% | 13.3% |
| Implement natural language processing solutions | 10–15% | 13.3% |
| Implement knowledge mining and information extraction solutions | 10–15% | 13.4% |

Planning weights select study time only; the official ranges remain the exam source of truth.

## Sprint-to-artifact matrix

Each sprint block below maps to implemented lesson IDs, assessments, and at least one executable or replayable lab path. “Planned” lesson-local lab paths remain prompts for future expansion, but the executable lab IDs listed here are the current runnable baseline.

| Sprint | Domain focus | Lesson IDs | Executable/replayable lab IDs and scripts |
|---|---|---|---|
| Sprint 0 | Tooling, baseline, safety | PM-01 through PM-08 safety and operations sections | `uv run alo doctor --offline`; `uv run python scripts/run_evals.py --offline` |
| Sprint 1 | Plan and manage Azure AI solutions | PM-01 through PM-08 | `LAB-GOVERNANCE-MONITORING`; `scripts/labs/run_remaining_labs.py --offline` |
| Sprint 2 | Generative AI and agentic solutions | GA-01 through GA-10 | `LAB-AGENT-WORKFLOWS`; `LAB-SEARCH-RAG`; `scripts/labs/run_agent_lab.py --offline` |
| Sprint 3 | Computer vision | CV-01 through CV-07 | `LAB-VISION-ANALYSIS`; `LAB-MEDIA-GENERATION`; `scripts/labs/Create_VisionAnalysis_WSL.py --offline` |
| Sprint 4 | Text analysis solutions | TA-01 through TA-06 | `LAB-MEDICAL-TEXT`; `LAB-SPEECH-TRANSLATION`; `scripts/labs/Extract_MedicalText_Clinical.py --offline` |
| Sprint 5 | Information extraction solutions | IE-01 through IE-06 | `LAB-VECTOR-SEARCH`; `LAB-SEARCH-RAG`; `scripts/labs/Query_VectorSearch_Azure.py --offline` |
| Sprint 6 | Interleaved review and release acceptance | PM, GA, CV, TA, IE mixed review | `uv run pytest -m "not live_azure" -q`; `uv run python scripts/run_evals.py --offline` |

Assessment paths follow `content/assessments/ai103/<domain>/<lesson-id>.json`; lesson paths follow `content/lessons/ai103/<domain>/<lesson-id>.md`.

## Learning loop

Each session follows this sequence:

1. Closed-book retrieval questions.
2. A short substantive lesson with concrete examples and a visual representation.
3. Compare/contrast and “why” elaboration.
4. Guided practice at the learner's current ZPD level.
5. Independent assessment using a deterministic rubric.
6. Plain-language self-explanation.
7. An offline-first lab, with live Azure mode only when explicitly approved.
8. Scheduled review interleaved with another domain.

Spacing stages are 1, 3, 7, 14, 30, and 60 days, shortened after failure. The planner should avoid more than two consecutive items from one domain when due work from another domain exists.

## Sprint sequence

### Sprint 0 — Tooling, baseline, and safety

- Preserve and verify the existing ALO.
- Configure project-scoped Python, `uv`, pytest, linting, and offline CI.
- Add migration backups, dry runs, and compatibility tests.
- Document Azure account options, spending warnings, regions, quotas, and teardown.

Exit gate: all existing commands and offline tests pass; no live resource is required.

### Sprint 1 — Plan and manage Azure AI solutions

Study:

- Requirement and service selection.
- Foundry projects, models, deployments, quotas, and responsible AI.
- Authentication, authorization, networking, secrets, monitoring, and cost.
- Content safety, evaluation, tracing, and lifecycle management.

Practice:

- Design a cost-guarded architecture.
- Compare model and service choices.
- Run deployment preflight and teardown simulations.

### Sprint 2 — Generative AI and agentic solutions

Study:

- Prompting and structured output.
- Model selection, evaluation, safety, and observability.
- Retrieval-augmented generation.
- Tools, memory, orchestration, and multi-agent patterns.
- Groundedness, prompt injection, and bounded execution.

Practice:

- Invoke a configured Microsoft Foundry model.
- Build a grounded tutor that coaches but never grades.
- Run guarded tool and agent exercises with deterministic checks.

### Sprint 3 — Computer vision

Study:

- Image analysis, OCR, multimodal models, video, and responsible use.
- Input preparation, confidence interpretation, and result validation.

Required script: `scripts/labs/Create_VisionAnalysis_WSL.py`

The script must run against checked-in offline fixtures and optionally call the configured Azure service in explicit live mode.

### Sprint 4 — Natural language processing

Study:

- Language detection, sentiment, key phrases, named entities, PII, translation, speech, and conversation analysis.
- Privacy and safe handling of sensitive text.

Required script: `scripts/labs/Extract_MedicalText_Clinical.py`

Use synthetic medical text only. Logs and tutor context must redact source text and identifiers.

### Sprint 5 — Knowledge mining and information extraction

Study:

- Indexes, indexers, skillsets, chunking, embeddings, vector search, semantic ranking, hybrid search, RAG, document extraction, and Content Understanding.

Required script: `scripts/labs/Query_VectorSearch_Azure.py`

The lab must compare keyword, vector, semantic, and hybrid retrieval; emit traceable citations; and grade against deterministic fixtures.

### Sprint 6 — Interleaved review and release acceptance

- Rotate all five domains.
- Complete timed retrieval sets and error-driven reviews.
- Run one complete offline learning cycle.
- With explicit approval, run the guarded Azure smoke suite and verify teardown.
- Demonstrate scaffold fading after repeated independent success.
- Produce a final coverage matrix mapping every official competency to lessons, retrieval items, labs, assessments, and sources.

## Azure account reality

General Microsoft Learn Azure sandboxes are retired. Live work therefore requires an Azure free account, Azure for Students, or an approved existing subscription. Budget alerts are warnings rather than hard caps.

Every live lab must:

- show the expected resources and cost risk;
- require explicit confirmation;
- authenticate through Microsoft Entra ID;
- use a unique resource group;
- support idempotent teardown;
- verify resource deletion;
- retain an offline path.

## Implementation source

The ordered engineering backlog, file ownership, dependencies, acceptance criteria, validation commands, stop conditions, and commit checkpoints are in the [AI-103 Completion Task Manifest](../docs/plans/2026-07-24-ai-103-completion-task-manifest.md).
