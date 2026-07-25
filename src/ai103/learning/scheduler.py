from __future__ import annotations

from datetime import date, timedelta

from .models import LearningItem


DEFAULT_INTERVALS = (1, 3, 7, 14, 30, 60)


def next_review_on(item: LearningItem, completed_on: date, intervals: tuple[int, ...] = DEFAULT_INTERVALS) -> date:
    if item.consecutive_failures > 0:
        return completed_on + timedelta(days=intervals[0])
    stage = min(max(item.spacing_stage, 0), len(intervals) - 1)
    return completed_on + timedelta(days=intervals[stage])


def is_due_for_review(item: LearningItem, today: date, intervals: tuple[int, ...] = DEFAULT_INTERVALS) -> bool:
    if item.last_reviewed_on is None:
        return True
    return next_review_on(item, item.last_reviewed_on, intervals) <= today


def reschedule_after_result(
    item: LearningItem,
    completed_on: date,
    success: bool,
    independent: bool = True,
    intervals: tuple[int, ...] = DEFAULT_INTERVALS,
) -> LearningItem:
    if success and independent:
        return LearningItem(
            competency_id=item.competency_id,
            domain=item.domain,
            mastery=item.mastery,
            confidence=item.confidence,
            spacing_stage=min(item.spacing_stage + 1, len(intervals) - 1),
            last_reviewed_on=completed_on,
            consecutive_failures=0,
        )
    return LearningItem(
        competency_id=item.competency_id,
        domain=item.domain,
        mastery=item.mastery,
        confidence=item.confidence,
        spacing_stage=max(item.spacing_stage - 1, 0),
        last_reviewed_on=completed_on,
        consecutive_failures=item.consecutive_failures + 1,
    )
