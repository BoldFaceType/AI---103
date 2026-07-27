from __future__ import annotations

import json
import re
from typing import Any

from .models import QuestionRubric, QuestionScore


def score_question(rubric: QuestionRubric, answer: Any) -> QuestionScore:
    try:
        score = _score_by_kind(rubric, answer)
    except (TypeError, ValueError, AttributeError, KeyError):
        score = 0.0
    earned = round(rubric.points * score, 4)
    return QuestionScore(
        question_id=rubric.question_id,
        competency_id=rubric.competency_id,
        earned_points=earned,
        possible_points=rubric.points,
        score=round(score, 4),
        passed=score >= 0.8,
        feedback="deterministic rubric",
    )


def _score_by_kind(rubric: QuestionRubric, answer: Any) -> float:
    if rubric.points <= 0:
        raise ValueError("rubric points must be positive")
    if rubric.kind == "multiple_choice":
        return 1.0 if _text(answer) == _text(rubric.answer_key) else 0.0
    if rubric.kind == "multiple_select":
        return 1.0 if set(_list_text(answer)) == set(_list_text(rubric.answer_key)) else 0.0
    if rubric.kind == "ordering":
        return 1.0 if _list_text(answer) == _list_text(rubric.answer_key) else 0.0
    if rubric.kind == "matching":
        return 1.0 if _mapping_text(answer) == _mapping_text(rubric.answer_key) else 0.0
    if rubric.kind == "structured_output":
        return 1.0 if _canonical(answer) == _canonical(rubric.answer_key) else 0.0
    if rubric.kind == "code_check":
        return _score_code(answer, rubric.required_substrings, rubric.forbidden_substrings)
    if rubric.kind == "concept_checklist":
        return _score_concepts(answer, rubric.required_concepts)
    raise ValueError(f"unsupported rubric kind: {rubric.kind}")


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().casefold())


def _list_text(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise TypeError("answer must be a list")
    return [_text(item) for item in value]


def _mapping_text(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise TypeError("answer must be an object")
    return {_text(key): _text(item) for key, item in value.items()}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _score_code(answer: Any, required: tuple[str, ...], forbidden: tuple[str, ...]) -> float:
    code = str(answer)
    if any(fragment not in code for fragment in required):
        return 0.0
    if any(fragment in code for fragment in forbidden):
        return 0.0
    return 1.0


def _score_concepts(answer: Any, required: tuple[str, ...]) -> float:
    if not required:
        return 1.0
    text = _text(answer)
    matched = sum(1 for concept in required if _text(concept) in text)
    return matched / len(required)
