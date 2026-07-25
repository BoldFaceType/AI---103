from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.learning.planner import plan_tasks


OBJECTIVES = {
    "PM": {"weight": 0.275, "competency_ids": ["PM-01", "PM-02"]},
    "GA": {"weight": 0.325, "competency_ids": ["GA-01", "GA-02"]},
    "CV": {"weight": 0.133, "competency_ids": ["CV-01"]},
}


def test_fixed_clock_and_seed_produce_identical_plans():
    knowledge = {
        "PM": {"mastery": 0.2, "confidence": 0.2},
        "GA": {"mastery": 0.2, "confidence": 0.2},
    }

    first = plan_tasks(knowledge, OBJECTIVES, [], date(2026, 7, 25), seed=7)
    second = plan_tasks(knowledge, OBJECTIVES, [], date(2026, 7, 25), seed=7)

    assert first == second


def test_due_reviews_are_planned_before_new_material():
    knowledge = {
        "PM": {
            "mastery": 0.9,
            "confidence": 0.8,
            "competencies": {
                "PM-01": {"mastery": 0.9, "confidence": 0.8, "last_reviewed_on": "2026-07-01", "spacing_stage": 1}
            },
        },
        "GA": {"mastery": 0.1, "confidence": 0.1},
    }

    tasks = plan_tasks(knowledge, OBJECTIVES, [], date(2026, 7, 25), seed=1, max_tasks=3)

    assert tasks[0]["type"] == "review"
    assert tasks[0]["objective_ids"] == ["PM-01"]
    assert any(task["reason"] == "new_material" for task in tasks[1:])


def test_failed_items_receive_higher_review_priority():
    knowledge = {
        "PM": {
            "mastery": 0.5,
            "confidence": 0.5,
            "competencies": {
                "PM-01": {
                    "mastery": 0.5,
                    "confidence": 0.5,
                    "last_reviewed_on": "2026-07-23",
                    "spacing_stage": 3,
                    "consecutive_failures": 1,
                },
                "PM-02": {"mastery": 0.5, "confidence": 0.5, "last_reviewed_on": "2026-07-01", "spacing_stage": 1},
            },
        }
    }

    tasks = plan_tasks(knowledge, OBJECTIVES, [], date(2026, 7, 25), seed=1, max_tasks=2)

    assert tasks[0]["type"] == "review"
    assert tasks[0]["objective_ids"] == ["PM-01"]


def test_interleaving_caps_same_domain_streaks_at_two():
    knowledge = {
        "GA": {"mastery": 0.1, "confidence": 0.1},
        "PM": {"mastery": 0.2, "confidence": 0.2},
    }

    tasks = plan_tasks(knowledge, OBJECTIVES, [], date(2026, 7, 25), seed=1, max_tasks=6)
    domains = [task["domain"] for task in tasks]

    assert all(domains[index : index + 3] != [domains[index]] * 3 for index in range(len(domains) - 2))


def test_new_work_uses_official_weight_and_weakest_competency():
    knowledge = {
        "GA": {
            "mastery": 0.6,
            "confidence": 0.5,
            "competencies": {
                "GA-01": {"mastery": 0.7, "confidence": 0.5},
                "GA-02": {"mastery": 0.2, "confidence": 0.5},
            },
        },
        "PM": {
            "mastery": 0.1,
            "confidence": 0.5,
            "competencies": {
                "PM-01": {"mastery": 0.1, "confidence": 0.5},
                "PM-02": {"mastery": 0.0, "confidence": 0.5},
            },
        },
    }

    tasks = plan_tasks(knowledge, OBJECTIVES, [], date(2026, 7, 25), seed=1, max_tasks=4)
    first_new = next(task for task in tasks if task["reason"] == "new_material")

    assert first_new["domain"] == "GA"
    assert "GA-02" in {task["objective_ids"][0] for task in tasks if task["domain"] == "GA"}


def test_generates_lesson_lab_quiz_and_self_explanation_tasks():
    tasks = plan_tasks(
        {"GA": {"mastery": 0.1, "confidence": 0.1}, "PM": {"mastery": 0.1, "confidence": 0.1}},
        OBJECTIVES,
        [],
        date(2026, 7, 25),
        max_tasks=8,
    )

    assert {task["type"] for task in tasks} == {"lesson", "lab", "quiz", "self_explanation"}


def test_active_equivalent_tasks_are_not_duplicated():
    existing = [
        {
            "id": "task-lesson-GA-01-20260725",
            "type": "lesson",
            "objective_ids": ["GA-01"],
            "status": "open",
        }
    ]

    tasks = plan_tasks({"GA": {"mastery": 0.1, "confidence": 0.1}}, OBJECTIVES, existing, date(2026, 7, 25), max_tasks=4)

    assert ("lesson", "GA-01") not in {(task["type"], task["objective_ids"][0]) for task in tasks}
