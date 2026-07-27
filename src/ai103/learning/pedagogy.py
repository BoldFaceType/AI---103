from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .models import EvidenceEvent, PedagogyConfig, ScaffoldDecision

REQUIRED_TECHNIQUES = {
    "retrieval_practice",
    "spaced_repetition",
    "interleaving",
    "elaboration",
    "dual_coding",
    "feynman_self_explanation",
    "concrete_examples",
}
REQUIRED_LEVELS = {0, 1, 2, 3, 4}


def load_pedagogy_config(path: Path) -> PedagogyConfig:
    return parse_pedagogy_config(json.loads(path.read_text(encoding="utf-8")))


def parse_pedagogy_config(data: dict[str, Any]) -> PedagogyConfig:
    errors = validate_pedagogy_config(data)
    if errors:
        raise ValueError("pedagogy config validation failed: " + "; ".join(errors))

    return PedagogyConfig(
        techniques=tuple(item["id"] for item in data["techniques"]),
        spacing_intervals_days=tuple(data["spacing_intervals_days"]),
        promotion_independent_successes=int(data["promotion"]["independent_successes_required"]),
        demotion_consecutive_failures=int(data["demotion"]["consecutive_failures_required"]),
        stale_review_days=int(data["demotion"]["stale_review_days"]),
        zpd_levels={item["level"]: item for item in data["zpd_levels"]},
    )


def validate_pedagogy_config(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    techniques = data.get("techniques")
    technique_ids = {item.get("id") for item in techniques} if isinstance(techniques, list) else set()
    if technique_ids != REQUIRED_TECHNIQUES:
        errors.append("techniques must contain exactly the seven required pedagogy techniques")

    intervals = data.get("spacing_intervals_days")
    if not isinstance(intervals, list) or not intervals:
        errors.append("spacing_intervals_days must be a non-empty list")
    elif intervals != sorted(intervals) or any(not isinstance(day, int) or day <= 0 for day in intervals):
        errors.append("spacing_intervals_days must be positive integers in ascending order")

    promotion = data.get("promotion", {})
    if promotion.get("independent_successes_required") != 2:
        errors.append("promotion.independent_successes_required must be 2")

    demotion = data.get("demotion", {})
    if demotion.get("consecutive_failures_required") != 2:
        errors.append("demotion.consecutive_failures_required must be 2")
    if demotion.get("unsafe_live_lab_demotes") is not True:
        errors.append("demotion.unsafe_live_lab_demotes must be true")
    stale_days = demotion.get("stale_review_days")
    if not isinstance(stale_days, int) or stale_days <= 0:
        errors.append("demotion.stale_review_days must be a positive integer")

    levels = data.get("zpd_levels")
    level_ids = {item.get("level") for item in levels} if isinstance(levels, list) else set()
    if level_ids != REQUIRED_LEVELS:
        errors.append("zpd_levels must contain levels 0, 1, 2, 3, and 4")
    elif any(not item.get("scaffolding") or not item.get("hint_level") for item in levels):
        errors.append("each zpd level must define scaffolding and hint_level")

    return errors


def select_scaffold(events: list[EvidenceEvent], config: PedagogyConfig, today: date) -> ScaffoldDecision:
    if not events:
        return _decision(0, config, "no_history", due_review=True)

    ordered = sorted(events, key=lambda event: event.occurred_on)
    latest = ordered[-1]
    current_level = _clamp_level(latest.zpd_level)
    due_review = (today - latest.occurred_on).days >= config.stale_review_days

    if latest.unsafe_live_lab_behavior:
        return _decision(max(0, current_level - 1), config, "unsafe_live_lab_behavior", due_review)

    if _last_n_failures(ordered, current_level, config.demotion_consecutive_failures):
        return _decision(max(0, current_level - 1), config, "consecutive_failures", due_review)

    if due_review:
        return _decision(max(0, current_level - 1), config, "stale_review", due_review)

    if latest.is_hinted_success:
        return _decision(current_level, config, "hinted_success_no_promotion", due_review)

    if _independent_successes_at_level(ordered, current_level) >= config.promotion_independent_successes:
        return _decision(min(4, current_level + 1), config, "independent_success_promotion", due_review)

    return _decision(current_level, config, "continue_current_level", due_review)


def _decision(level: int, config: PedagogyConfig, reason: str, due_review: bool) -> ScaffoldDecision:
    zpd = config.zpd_levels[level]
    return ScaffoldDecision(
        zpd_level=level,
        scaffold=zpd["scaffolding"],
        hint_level=zpd["hint_level"],
        reason=reason,
        due_review=due_review,
    )


def _clamp_level(level: int) -> int:
    return max(0, min(4, int(level)))


def _last_n_failures(events: list[EvidenceEvent], level: int, required: int) -> bool:
    same_level = [event for event in events if event.zpd_level == level]
    if len(same_level) < required:
        return False
    return all(event.is_failure for event in same_level[-required:])


def _independent_successes_at_level(events: list[EvidenceEvent], level: int) -> int:
    count = 0
    for event in reversed(events):
        if event.zpd_level != level:
            break
        if event.is_independent_success:
            count += 1
            continue
        if event.is_failure:
            break
    return count
