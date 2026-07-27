from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.learning.models import EvidenceEvent
from ai103.learning.pedagogy import load_pedagogy_config, parse_pedagogy_config, select_scaffold


CONFIG_PATH = ROOT / "config" / "pedagogy.zpd.json"


def event(
    event_id: str,
    level: int,
    outcome: str,
    mode: str = "independent",
    occurred_on: date = date(2026, 7, 1),
    first_attempt: bool = True,
    unsafe: bool = False,
    model_suggested_zpd_level: int | None = None,
) -> EvidenceEvent:
    return EvidenceEvent(
        event_id=event_id,
        competency_id="PM-01",
        domain="PM",
        zpd_level=level,
        outcome=outcome,
        mode=mode,
        first_attempt=first_attempt,
        occurred_on=occurred_on,
        unsafe_live_lab_behavior=unsafe,
        model_feedback={"comment": "coaching only"},
        model_suggested_zpd_level=model_suggested_zpd_level,
    )


def test_config_loads_seven_techniques_and_five_zpd_levels():
    config = load_pedagogy_config(CONFIG_PATH)

    assert len(config.techniques) == 7
    assert set(config.zpd_levels) == {0, 1, 2, 3, 4}
    assert config.spacing_intervals_days == (1, 3, 7, 14, 30, 60)


def test_no_history_selects_level_zero_worked_example():
    config = load_pedagogy_config(CONFIG_PATH)
    decision = select_scaffold([], config, today=date(2026, 7, 25))

    assert decision.zpd_level == 0
    assert decision.hint_level == "worked_example"
    assert decision.reason == "no_history"
    assert decision.due_review is True


def test_two_independent_first_attempt_successes_promote_one_level():
    config = load_pedagogy_config(CONFIG_PATH)
    decision = select_scaffold(
        [
            event("e1", 1, "success", occurred_on=date(2026, 7, 1)),
            event("e2", 1, "success", occurred_on=date(2026, 7, 2)),
        ],
        config,
        today=date(2026, 7, 3),
    )

    assert decision.zpd_level == 2
    assert decision.reason == "independent_success_promotion"


def test_two_consecutive_failures_demote_one_level():
    config = load_pedagogy_config(CONFIG_PATH)
    decision = select_scaffold(
        [
            event("e1", 2, "failure", occurred_on=date(2026, 7, 1)),
            event("e2", 2, "failure", occurred_on=date(2026, 7, 2)),
        ],
        config,
        today=date(2026, 7, 3),
    )

    assert decision.zpd_level == 1
    assert decision.reason == "consecutive_failures"


def test_hinted_success_does_not_count_as_independent_success():
    config = load_pedagogy_config(CONFIG_PATH)
    decision = select_scaffold(
        [
            event("e1", 2, "success", mode="independent", occurred_on=date(2026, 7, 1)),
            event("e2", 2, "success", mode="hinted", occurred_on=date(2026, 7, 2)),
        ],
        config,
        today=date(2026, 7, 3),
    )

    assert decision.zpd_level == 2
    assert decision.reason == "hinted_success_no_promotion"


def test_stale_review_demotes_one_level_and_marks_due():
    config = load_pedagogy_config(CONFIG_PATH)
    decision = select_scaffold(
        [event("e1", 3, "success", occurred_on=date(2026, 7, 1))],
        config,
        today=date(2026, 7, 25),
    )

    assert decision.zpd_level == 2
    assert decision.reason == "stale_review"
    assert decision.due_review is True


def test_model_feedback_cannot_change_zpd_level_directly():
    config = load_pedagogy_config(CONFIG_PATH)
    decision = select_scaffold(
        [event("e1", 1, "success", occurred_on=date(2026, 7, 1), model_suggested_zpd_level=4)],
        config,
        today=date(2026, 7, 2),
    )

    assert decision.zpd_level == 1
    assert decision.reason == "continue_current_level"


def test_config_errors_fail_clearly():
    data = {
        "schema_version": 1,
        "techniques": [],
        "spacing_intervals_days": [3, 1],
        "promotion": {"independent_successes_required": 1},
        "demotion": {
            "consecutive_failures_required": 1,
            "unsafe_live_lab_demotes": False,
            "stale_review_days": 0,
        },
        "zpd_levels": [],
    }

    with pytest.raises(ValueError) as exc:
        parse_pedagogy_config(data)

    message = str(exc.value)
    assert "seven required pedagogy techniques" in message
    assert "spacing_intervals_days" in message
    assert "zpd_levels must contain levels 0, 1, 2, 3, and 4" in message


def test_unsafe_live_lab_behavior_demotes_without_waiting_for_second_failure():
    config = load_pedagogy_config(CONFIG_PATH)
    decision = select_scaffold(
        [event("e1", 3, "success", unsafe=True, occurred_on=date(2026, 7, 1))],
        config,
        today=date(2026, 7, 2),
    )

    assert decision.zpd_level == 2
    assert decision.reason == "unsafe_live_lab_behavior"
