from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

QuestionKind = Literal[
    "multiple_choice",
    "multiple_select",
    "ordering",
    "matching",
    "structured_output",
    "code_check",
    "concept_checklist",
]
AttemptType = Literal["first", "hinted", "corrected"]


@dataclass(frozen=True)
class QuestionRubric:
    question_id: str
    kind: QuestionKind
    competency_id: str
    points: float
    answer_key: Any = None
    required_concepts: tuple[str, ...] = ()
    required_substrings: tuple[str, ...] = ()
    forbidden_substrings: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssessmentAttempt:
    attempt_id: str
    question_id: str
    answer: Any
    attempt_type: AttemptType
    submitted_on: date
    model_coaching: str = ""
    model_score: float | None = None


@dataclass(frozen=True)
class QuestionScore:
    question_id: str
    competency_id: str
    earned_points: float
    possible_points: float
    score: float
    passed: bool
    feedback: str


@dataclass(frozen=True)
class AssessmentResult:
    attempt_id: str
    attempt_type: AttemptType
    earned_points: float
    possible_points: float
    score: float
    score_scale: str
    question_scores: tuple[QuestionScore, ...]
    coaching: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MasteryEvidence:
    competency_id: str
    mastery_delta: float
    evidence_quality: float
    independence_multiplier: float
    recency_multiplier: float
    competency_weight: float
    source_attempt_id: str
