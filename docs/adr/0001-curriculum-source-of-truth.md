# ADR 0001: Curriculum Source of Truth

Status: Accepted

## Context

AI---103 content changes as Microsoft updates the certification, study guide, course, and product documentation. The repository also contains historical AI-102-oriented planning material. Without a source-precedence rule, generated lessons and tasks can drift toward outdated objectives.

## Decision

Use current official Microsoft Learn material as the curriculum authority in this order:

1. Official AI-103 study guide.
2. Official Azure AI Apps and Agents Developer Associate certification page.
3. Official AI-103T00-A course.
4. Current Microsoft Learn product documentation.
5. Repository documentation.
6. Historical planning documents.

The curriculum registry must store source URL, skills-measured date, last verification date, normalized source hash, and stable competency IDs. If the official study guide changes, curriculum work stops until the registry and docs are updated with a reviewed diff.

## Consequences

- Historical AI-102 material can inform migration notes but cannot define AI-103 coverage.
- Lessons must paraphrase and cite Microsoft sources instead of copying Microsoft Learn prose.
- T04 must lock the current official curriculum into repository data before lesson implementation.
- Future docs must state the verification date for curriculum claims.
