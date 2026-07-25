from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

REQUIRED_SECTIONS = (
    "Source Links",
    "Prerequisites and Duration",
    "Pre-Lesson Retrieval Questions",
    "Substantive Explanation",
    "Mermaid Diagram",
    "Concrete Azure Example",
    "Worked Example",
    "Guided Exercise with Fading Hints",
    "Independent Transfer Exercise",
    "Elaboration Prompts",
    "Feynman Self-Explanation",
    "Common Misconceptions",
    "Lab Links",
    "Assessment Links",
    "Answer Rubric Data",
)
MICROSOFT_COPY_PATTERNS = (
    "Study guide for Exam AI-103: Developing AI Apps and Agents on Azure",
    "Microsoft Certified: Azure AI Apps and Agents Developer Associate",
)


@dataclass(frozen=True)
class LessonError:
    path: str
    section: str
    message: str

    def format(self) -> str:
        return f"{self.path}::{self.section}: {self.message}"


@dataclass(frozen=True)
class LessonDocument:
    path: Path
    metadata: dict[str, Any]
    sections: dict[str, str]


def parse_lesson(path: Path) -> LessonDocument:
    text = path.read_text(encoding="utf-8")
    metadata, body = _parse_frontmatter(text)
    return LessonDocument(path=path, metadata=metadata, sections=_parse_sections(body))


def validate_lesson_file(path: Path, curriculum_path: Path, source_registry_path: Path, today: date) -> list[LessonError]:
    lesson = parse_lesson(path)
    curriculum = json.loads(curriculum_path.read_text(encoding="utf-8"))
    source_registry = json.loads(source_registry_path.read_text(encoding="utf-8"))
    known_competencies = {item["id"] for item in curriculum.get("competencies", [])}
    errors: list[LessonError] = []
    errors.extend(_validate_metadata(lesson, known_competencies, source_registry, today))
    errors.extend(_validate_sections(lesson))
    errors.extend(_validate_pedagogy_content(lesson))
    return errors


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + 5 :]
    return json.loads(raw), body


def _parse_sections(body: str) -> dict[str, str]:
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[match.group(1).strip()] = body[start:end].strip()
    return sections


def _validate_metadata(
    lesson: LessonDocument,
    known_competencies: set[str],
    source_registry: dict[str, Any],
    today: date,
) -> list[LessonError]:
    errors: list[LessonError] = []
    metadata = lesson.metadata
    required = (
        "schema_version",
        "lesson_id",
        "title",
        "competency_ids",
        "official_source_links",
        "source_verified_at",
        "prerequisites",
        "estimated_minutes",
        "lab_links",
        "assessment_links",
        "paraphrase_statement",
    )
    for field in required:
        if field not in metadata:
            errors.append(_error(lesson, "metadata", f"missing field '{field}'"))
    competency_ids = metadata.get("competency_ids", [])
    if not isinstance(competency_ids, list) or not competency_ids:
        errors.append(_error(lesson, "metadata", "competency_ids must be a non-empty list"))
    else:
        unknown = sorted(set(competency_ids) - known_competencies)
        if unknown:
            errors.append(_error(lesson, "metadata", f"unknown competency_ids: {', '.join(unknown)}"))
    links = metadata.get("official_source_links", [])
    primary_url = source_registry.get("primary_source", {}).get("url")
    if primary_url not in links:
        errors.append(_error(lesson, "metadata", "official_source_links must include the primary source registry URL"))
    verified_at = _parse_date(metadata.get("source_verified_at"))
    registry_verified_at = _parse_date(source_registry.get("primary_source", {}).get("last_verified_at"))
    if verified_at is None:
        errors.append(_error(lesson, "metadata", "source_verified_at must be YYYY-MM-DD"))
    elif registry_verified_at and verified_at < registry_verified_at:
        errors.append(_error(lesson, "metadata", "source_verified_at is older than the source registry"))
    elif (today - verified_at).days > 180:
        errors.append(_error(lesson, "metadata", "source_verified_at is stale"))
    if "original paraphrase" not in str(metadata.get("paraphrase_statement", "")).casefold():
        errors.append(_error(lesson, "metadata", "paraphrase_statement must declare original paraphrase"))
    return errors


def _validate_sections(lesson: LessonDocument) -> list[LessonError]:
    errors: list[LessonError] = []
    for section in REQUIRED_SECTIONS:
        if not lesson.sections.get(section):
            errors.append(_error(lesson, section, "missing required section"))
    return errors


def _validate_pedagogy_content(lesson: LessonDocument) -> list[LessonError]:
    errors: list[LessonError] = []
    retrieval = lesson.sections.get("Pre-Lesson Retrieval Questions", "")
    retrieval_count = len(re.findall(r"^\d+\.\s+", retrieval, flags=re.MULTILINE))
    if retrieval_count < 3 or retrieval_count > 5:
        errors.append(_error(lesson, "Pre-Lesson Retrieval Questions", "must contain 3-5 numbered questions"))
    explanation_words = _word_count(lesson.sections.get("Substantive Explanation", ""))
    if explanation_words < 800 or explanation_words > 1500:
        errors.append(_error(lesson, "Substantive Explanation", "must be 800-1500 words"))
    diagram = lesson.sections.get("Mermaid Diagram", "")
    if "```mermaid" not in diagram:
        errors.append(_error(lesson, "Mermaid Diagram", "must include a Mermaid diagram"))
    if "Alt text:" not in diagram:
        errors.append(_error(lesson, "Mermaid Diagram", "must include accessible alt text"))
    if "Diagram reconstruction prompt:" not in diagram:
        errors.append(_error(lesson, "Mermaid Diagram", "must include a reconstruction prompt"))
    guided = lesson.sections.get("Guided Exercise with Fading Hints", "")
    if not all(label in guided for label in ("Hint 1", "Hint 2", "Hint 3")):
        errors.append(_error(lesson, "Guided Exercise with Fading Hints", "must include three fading hint levels"))
    if "compare" not in lesson.sections.get("Elaboration Prompts", "").casefold():
        errors.append(_error(lesson, "Elaboration Prompts", "must include compare/contrast prompt"))
    feynman = lesson.sections.get("Feynman Self-Explanation", "")
    if "Concept checklist:" not in feynman:
        errors.append(_error(lesson, "Feynman Self-Explanation", "must include concept checklist"))
    rubric = lesson.sections.get("Answer Rubric Data", "")
    if "```json" not in rubric or "answers_are_separate_from_lesson" not in rubric:
        errors.append(_error(lesson, "Answer Rubric Data", "must contain separate JSON answer/rubric data"))
    explanation = lesson.sections.get("Substantive Explanation", "")
    for pattern in MICROSOFT_COPY_PATTERNS:
        if pattern in explanation:
            errors.append(_error(lesson, "Substantive Explanation", "appears to contain copied Microsoft source text"))
    return errors


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _error(lesson: LessonDocument, section: str, message: str) -> LessonError:
    return LessonError(path=lesson.path.as_posix(), section=section, message=message)
