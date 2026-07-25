from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.learning.models import LearningItem
from ai103.learning.scheduler import is_due_for_review, next_review_on, reschedule_after_result


def item(**overrides) -> LearningItem:
    data = {
        "competency_id": "PM-01",
        "domain": "PM",
        "mastery": 0.4,
        "confidence": 0.4,
        "spacing_stage": 1,
        "last_reviewed_on": date(2026, 7, 1),
        "consecutive_failures": 0,
    }
    data.update(overrides)
    return LearningItem(**data)


def test_review_intervals_are_deterministic():
    assert next_review_on(item(spacing_stage=0), date(2026, 7, 1)) == date(2026, 7, 2)
    assert next_review_on(item(spacing_stage=2), date(2026, 7, 1)) == date(2026, 7, 8)


def test_due_review_uses_fixed_clock():
    reviewed = item(spacing_stage=0, last_reviewed_on=date(2026, 7, 1))

    assert is_due_for_review(reviewed, date(2026, 7, 2)) is True
    assert is_due_for_review(reviewed, date(2026, 7, 1)) is False


def test_success_advances_spacing_stage():
    updated = reschedule_after_result(item(spacing_stage=1), date(2026, 7, 4), success=True)

    assert updated.spacing_stage == 2
    assert updated.consecutive_failures == 0
    assert updated.last_reviewed_on == date(2026, 7, 4)


def test_failed_items_reschedule_sooner():
    failed = reschedule_after_result(item(spacing_stage=4), date(2026, 7, 4), success=False)

    assert failed.spacing_stage == 3
    assert failed.consecutive_failures == 1
    assert next_review_on(failed, failed.last_reviewed_on) == date(2026, 7, 5)
