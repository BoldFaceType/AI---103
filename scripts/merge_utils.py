from __future__ import annotations

from copy import deepcopy
from typing import Any


def merge_profile(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(current)
    merged.update(incoming)
    return merged


def merge_progress(current: dict[str, Any], incoming_events: list[dict[str, Any]]) -> dict[str, Any]:
    merged = deepcopy(current)
    history = list(merged.get("events", []))
    known_ids = {event.get("event_id") for event in history}
    for event in incoming_events:
        event_id = event.get("event_id")
        if event_id in known_ids:
            continue
        history.append(event)
        known_ids.add(event_id)
    merged["events"] = history
    completed = [event for event in history if event.get("type") == "quiz_completed"]
    merged["percentComplete"] = round(min(1.0, len(completed) / 10), 3)
    return merged


def merge_tasks(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(current)
    current_status = current.get("status", "open")
    next_status = incoming.get("status", current_status)
    allowed = {
        "open": {"open", "in_progress", "done"},
        "in_progress": {"in_progress", "done"},
        "done": {"done"},
    }
    if next_status not in allowed.get(current_status, {current_status}):
        raise ValueError(f"invalid task transition from {current_status} to {next_status}")
    merged.update(incoming)
    return merged


def merge_feedback(current: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = list(current)
    merged.extend(incoming)
    return merged