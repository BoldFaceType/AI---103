from __future__ import annotations

from datetime import date

from .models import AssessmentAttempt, AssessmentResult, MasteryEvidence, QuestionRubric
from .rubrics import score_question

ATTEMPT_MULTIPLIERS = {
    "first": 1.0,
    "hinted": 0.6,
    "corrected": 0.3,
}


def grade_assessment(rubrics: list[QuestionRubric], attempt: AssessmentAttempt) -> AssessmentResult:
    question_scores = tuple(score_question(rubric, attempt.answer) for rubric in rubrics if rubric.question_id == attempt.question_id)
    possible = round(sum(score.possible_points for score in question_scores), 4)
    earned = round(sum(score.earned_points for score in question_scores), 4)
    score = round(earned / possible, 4) if possible else 0.0
    return AssessmentResult(
        attempt_id=attempt.attempt_id,
        attempt_type=attempt.attempt_type,
        earned_points=earned,
        possible_points=possible,
        score=score,
        score_scale="practice",
        question_scores=question_scores,
        coaching=attempt.model_coaching,
        metadata={"model_score_ignored": attempt.model_score is not None},
    )


def mastery_evidence(
    result: AssessmentResult,
    competency_weights: dict[str, float],
    today: date,
    last_seen: dict[str, date] | None = None,
) -> list[MasteryEvidence]:
    last_seen = last_seen or {}
    evidence: list[MasteryEvidence] = []
    for question in result.question_scores:
        competency_id = question.competency_id
        quality = question.score
        independence = ATTEMPT_MULTIPLIERS[result.attempt_type]
        recency = _recency_multiplier(today, last_seen.get(competency_id))
        weight = float(competency_weights.get(competency_id, 1.0))
        delta = round(0.1 * quality * independence * recency * weight, 4)
        evidence.append(
            MasteryEvidence(
                competency_id=competency_id,
                mastery_delta=delta,
                evidence_quality=quality,
                independence_multiplier=independence,
                recency_multiplier=recency,
                competency_weight=weight,
                source_attempt_id=result.attempt_id,
            )
        )
    return evidence


def _recency_multiplier(today: date, last_seen_on: date | None) -> float:
    if last_seen_on is None:
        return 1.0
    age_days = max(0, (today - last_seen_on).days)
    if age_days <= 7:
        return 1.0
    if age_days <= 30:
        return 0.8
    return 0.6
