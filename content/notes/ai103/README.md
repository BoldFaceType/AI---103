# AI-103 Notes

This hub is for learner-authored notes that sit beside, not inside, the authoritative AI-103 lessons.

Authoritative lesson content lives under `content/lessons/ai103/`. Use this notes area for summaries, mnemonics, personal examples, scratch retrieval answers, and links back to the lesson, lab, assessment, and source that produced the note.

## Official source

- AI-103 study guide: https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-103
- Local source registry: `content/sources/ai103-source-registry.json`
- Curriculum map: `config/curriculum.ai103.json`

## Domain map

| Domain | Lessons | Assessments | Planned labs | Review command |
|---|---|---|---|---|
| Plan and manage (`PM`) | `content/lessons/ai103/pm/PM-01.md` through `PM-08.md` | `content/assessments/ai103/pm/` | `scripts/labs/planned/PM-*` | `uv run python scripts/curriculum_audit.py --domain PM` |
| Generative AI and agents (`GA`) | `content/lessons/ai103/ga/GA-01.md` through `GA-10.md` | `content/assessments/ai103/ga/` | `scripts/labs/planned/GA-*` | `uv run python scripts/curriculum_audit.py --domain GA` |
| Computer vision and multimodal (`CV`) | `content/lessons/ai103/cv/CV-01.md` through `CV-07.md` | `content/assessments/ai103/cv/` | `scripts/labs/planned/CV-*` | `uv run python scripts/curriculum_audit.py --domain CV` |
| Text analysis and speech (`TA`) | `content/lessons/ai103/ta/TA-01.md` through `TA-06.md` | `content/assessments/ai103/ta/` | `scripts/labs/planned/TA-*` | `uv run python scripts/curriculum_audit.py --domain TA` |
| Information extraction and grounding (`IE`) | `content/lessons/ai103/ie/IE-01.md` through `IE-06.md` | `content/assessments/ai103/ie/` | `scripts/labs/planned/IE-*` | `uv run python scripts/curriculum_audit.py --domain IE` |

## Suggested note format

Create notes as separate Markdown files in this directory or a subfolder you create here. Keep the lesson identifier in the filename, for example `GA-04-evaluation-mistakes.md`.

```markdown
# GA-04 evaluation mistakes

Source lesson: `content/lessons/ai103/ga/GA-04.md`
Assessment: `content/assessments/ai103/ga/GA-04.json`

## Retrieval answers

1. ...

## What I missed

- ...

## Remediation

- Re-read section: ...
- Rerun assessment: ...
```

## Glossary

- Agent retrieval tool: A validated tool boundary that lets an agent request grounded context from an approved retrieval pipeline.
- Alt text: Short accessible text describing the purpose or visible evidence of an image.
- Content Understanding analyzer: A Foundry capability pattern that extracts structured or markdown representations from documents and multimodal inputs.
- Deterministic grading: Rubric-based scoring that does not rely on model opinion.
- Grounding: Providing source evidence, citations, or retrieved context for generated or agentic output.
- Hybrid search: Retrieval that combines lexical and vector signals.
- RAG: Retrieval-augmented generation, where retrieved context grounds model output.
- ZPD: Zone of proximal development; the scaffold between what the learner can do with support and what they can do independently.

## Rules for adding notes

- Do not edit authoritative lesson files just to record personal notes.
- Do not copy Microsoft Learn prose into notes; summarize in your own words and link the source.
- Keep real personal, clinical, customer, credential, and secret data out of notes.
- Link each note back to the lesson, assessment, and any lab fixture that produced it.
- If a note identifies an error in authoritative lesson content, open a code/docs change instead of silently correcting only the note.

## Review commands

```powershell
uv run python scripts/curriculum_audit.py
uv run pytest tests/contract/test_lessons.py -q
rg -n "Add[ ]lesson notes here|Describe[ ]tutoring instructions here" content
```
