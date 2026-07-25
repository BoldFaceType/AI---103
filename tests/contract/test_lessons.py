from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.curriculum.lesson import parse_lesson, validate_lesson_file

TEMPLATE = ROOT / "content" / "lessons" / "ai103" / "TEMPLATE.md"
CURRICULUM = ROOT / "config" / "curriculum.ai103.json"
SOURCE_REGISTRY = ROOT / "content" / "sources" / "ai103-source-registry.json"


def validate(path: Path, today: date = date(2026, 7, 25)):
    return validate_lesson_file(path, CURRICULUM, SOURCE_REGISTRY, today=today)


def pm_lessons() -> list[Path]:
    return sorted((ROOT / "content" / "lessons" / "ai103" / "pm").glob("PM-*.md"))


def test_template_satisfies_lesson_contract():
    errors = validate(TEMPLATE)

    assert errors == []


def test_parser_extracts_metadata_and_sections():
    lesson = parse_lesson(TEMPLATE)

    assert lesson.metadata["schema_version"] == 1
    assert lesson.metadata["competency_ids"] == ["GA-01"]
    assert "Substantive Explanation" in lesson.sections
    assert "Answer Rubric Data" in lesson.sections


def test_missing_pedagogy_section_reports_exact_file_and_section(tmp_path):
    broken = tmp_path / "broken.md"
    text = TEMPLATE.read_text(encoding="utf-8").replace("## Mermaid Diagram", "## Missing Diagram", 1)
    broken.write_text(text, encoding="utf-8")

    errors = validate(broken)

    formatted = [error.format() for error in errors]
    assert f"{broken.as_posix()}::Mermaid Diagram: missing required section" in formatted


def test_stale_source_metadata_is_rejected(tmp_path):
    broken = tmp_path / "stale.md"
    text = TEMPLATE.read_text(encoding="utf-8").replace('"source_verified_at": "2026-07-25"', '"source_verified_at": "2025-01-01"', 1)
    broken.write_text(text, encoding="utf-8")

    errors = validate(broken)

    assert any(error.section == "metadata" and "source_verified_at" in error.message for error in errors)


def test_unknown_competency_is_rejected(tmp_path):
    broken = tmp_path / "unknown.md"
    text = TEMPLATE.read_text(encoding="utf-8").replace('"competency_ids": ["GA-01"]', '"competency_ids": ["NO-404"]', 1)
    broken.write_text(text, encoding="utf-8")

    errors = validate(broken)

    assert any(error.section == "metadata" and "unknown competency_ids: NO-404" in error.message for error in errors)


def test_copied_source_text_in_explanation_is_rejected(tmp_path):
    broken = tmp_path / "copied.md"
    text = TEMPLATE.read_text(encoding="utf-8").replace(
        "This section is the main teaching body.",
        "Study guide for Exam AI-103: Developing AI Apps and Agents on Azure. This section is the main teaching body.",
        1,
    )
    broken.write_text(text, encoding="utf-8")

    errors = validate(broken)

    assert any(error.section == "Substantive Explanation" and "copied Microsoft source text" in error.message for error in errors)


def test_answer_rubric_data_must_be_separate_json(tmp_path):
    broken = tmp_path / "rubric.md"
    text = TEMPLATE.read_text(encoding="utf-8").replace("```json", "```text", 1)
    broken.write_text(text, encoding="utf-8")

    errors = validate(broken)

    assert any(error.section == "Answer Rubric Data" and "separate JSON" in error.message for error in errors)


def test_pm_lessons_cover_all_pm_competencies_and_pass_contract():
    expected = {f"PM-{index:02d}" for index in range(1, 17)}
    covered: set[str] = set()
    lessons = pm_lessons()

    assert [path.stem for path in lessons] == [f"PM-{index:02d}" for index in range(1, 9)]
    for path in lessons:
        errors = validate(path)
        assert [error.format() for error in errors] == []
        covered.update(parse_lesson(path).metadata["competency_ids"])

    assert covered == expected


def test_pm_lessons_have_matching_assessment_files():
    for path in pm_lessons():
        lesson = parse_lesson(path)
        for link in lesson.metadata["assessment_links"]:
            assessment_path = ROOT / link
            assert assessment_path.exists(), f"missing assessment for {path.name}: {link}"
            assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
            assert assessment["lesson_id"] == lesson.metadata["lesson_id"]
            assert set(assessment["competency_ids"]) == set(lesson.metadata["competency_ids"])
            assert assessment["score_scale"] == "practice"


def test_pm_lessons_include_required_t11_scenarios():
    text = "\n".join(path.read_text(encoding="utf-8") for path in pm_lessons()).casefold()

    assert "reject" in text and "unsuitable" in text
    assert "without creating live azure resources" in text or "before any provisioning" in text
    assert "least-privilege" in text
    assert "budget" in text
