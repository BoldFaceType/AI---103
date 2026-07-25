from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import date
from typing import Any

from .models import LearningItem, PlannedTask
from .scheduler import DEFAULT_INTERVALS, is_due_for_review, next_review_on

NEW_TASK_TYPES = ("lesson", "lab", "quiz", "self_explanation")


def plan_tasks(
    knowledge: dict[str, Any],
    objectives: dict[str, Any],
    existing_tasks: list[dict[str, Any]],
    today: date,
    seed: int = 0,
    max_tasks: int = 6,
    remediation_threshold: float = 0.8,
    intervals: tuple[int, ...] = DEFAULT_INTERVALS,
) -> list[dict[str, Any]]:
    active = _active_equivalents(existing_tasks)
    items = _learning_items(knowledge, objectives)
    due = _due_review_tasks(items, today, intervals, active)
    new = _new_material_tasks(items, objectives, today, seed, remediation_threshold, active)
    planned = _interleave(due + new, max_tasks)
    return [task.to_task_dict() for task in planned]


def _learning_items(knowledge: dict[str, Any], objectives: dict[str, Any]) -> list[LearningItem]:
    items: list[LearningItem] = []
    for domain, objective in objectives.items():
        domain_state = knowledge.get(domain, {})
        competencies = domain_state.get("competencies", {})
        for competency_id in objective.get("competency_ids", []):
            state = competencies.get(competency_id, domain_state)
            items.append(
                LearningItem(
                    competency_id=competency_id,
                    domain=domain,
                    mastery=float(state.get("mastery", domain_state.get("mastery", 0.0))),
                    confidence=float(state.get("confidence", domain_state.get("confidence", 0.0))),
                    spacing_stage=int(state.get("spacing_stage", domain_state.get("spacing_stage", 0))),
                    last_reviewed_on=_parse_date(state.get("last_reviewed_on", domain_state.get("last_reviewed_on"))),
                    consecutive_failures=int(state.get("consecutive_failures", domain_state.get("consecutive_failures", 0))),
                )
            )
    return items


def _due_review_tasks(
    items: list[LearningItem],
    today: date,
    intervals: tuple[int, ...],
    active: set[tuple[str, str]],
) -> list[PlannedTask]:
    tasks: list[PlannedTask] = []
    for item in items:
        if item.last_reviewed_on is None:
            continue
        if not is_due_for_review(item, today, intervals):
            continue
        if ("review", item.competency_id) in active:
            continue
        due_on = item.last_reviewed_on and next_review_on(item, item.last_reviewed_on, intervals)
        lateness = (today - due_on).days if due_on else 0
        failure_boost = 2000 if item.consecutive_failures else 0
        tasks.append(
            PlannedTask(
                task_type="review",
                competency_id=item.competency_id,
                domain=item.domain,
                reason="due_review",
                due_on=today,
                priority=1000 + failure_boost + max(lateness, 0),
                estimated_minutes=8,
            )
        )
    return sorted(tasks, key=lambda task: (-task.priority, task.domain, task.competency_id))


def _new_material_tasks(
    items: list[LearningItem],
    objectives: dict[str, Any],
    today: date,
    seed: int,
    remediation_threshold: float,
    active: set[tuple[str, str]],
) -> list[PlannedTask]:
    by_domain: dict[str, list[LearningItem]] = defaultdict(list)
    for item in items:
        if item.mastery < remediation_threshold:
            by_domain[item.domain].append(item)

    tasks: list[PlannedTask] = []
    for domain, domain_items in by_domain.items():
        objective_weight = float(objectives.get(domain, {}).get("weight", 0.0))
        weakest = sorted(
            domain_items,
            key=lambda item: (item.mastery, item.confidence, _tie_break(seed, item.competency_id)),
        )[0]
        for index, task_type in enumerate(NEW_TASK_TYPES):
            if (task_type, weakest.competency_id) in active:
                continue
            tasks.append(
                PlannedTask(
                    task_type=task_type,
                    competency_id=weakest.competency_id,
                    domain=domain,
                    reason="new_material",
                    due_on=today,
                    priority=objective_weight * 100 - weakest.mastery * 10 - index,
                    estimated_minutes=_estimated_minutes(task_type, objective_weight),
                )
            )
    return sorted(tasks, key=lambda task: (-task.priority, task.domain, task.task_type, task.competency_id))


def _interleave(tasks: list[PlannedTask], max_tasks: int) -> list[PlannedTask]:
    remaining = sorted(tasks, key=lambda task: (-task.priority, task.domain, task.task_type, task.competency_id))
    selected: list[PlannedTask] = []
    while remaining and len(selected) < max_tasks:
        last_domains = [task.domain for task in selected[-2:]]
        blocked_domain = last_domains[0] if len(last_domains) == 2 and last_domains[0] == last_domains[1] else None
        choice_index = next((index for index, task in enumerate(remaining) if task.domain != blocked_domain), None)
        if choice_index is None:
            break
        selected.append(remaining.pop(choice_index))
    return selected


def _active_equivalents(tasks: list[dict[str, Any]]) -> set[tuple[str, str]]:
    active: set[tuple[str, str]] = set()
    for task in tasks:
        if task.get("status") not in {"open", "in_progress"}:
            continue
        task_type = str(task.get("type", ""))
        for objective_id in task.get("objective_ids", []):
            active.add((task_type, str(objective_id)))
    return active


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    return date.fromisoformat(value[:10])


def _tie_break(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def _estimated_minutes(task_type: str, weight: float) -> int:
    base = {"lesson": 20, "lab": 35, "quiz": 10, "self_explanation": 12}[task_type]
    return base + (5 if weight >= 0.3 and task_type in {"lesson", "lab"} else 0)
