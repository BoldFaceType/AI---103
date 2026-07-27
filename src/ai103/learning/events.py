from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = 2

DETERMINISTIC_EVIDENCE_EVENTS = {
    "retrieval_completed",
    "lesson_completed",
    "quiz_completed",
    "lab_completed",
    "self_explanation_completed",
    "review_completed",
}
AUDIT_ONLY_EVENTS = {
    "tutor_feedback_received",
    "resource_created",
    "resource_deleted",
    "decision_made",
}
KNOWN_EVENT_TYPES = DETERMINISTIC_EVIDENCE_EVENTS | AUDIT_ONLY_EVENTS


@dataclass(frozen=True)
class EventSignal:
    event_id: str
    event_type: str
    score: float
    objective_ids: tuple[str, ...]
    timestamp: str


def validate_learning_event(event: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if event.get("schema_version") != SCHEMA_VERSION:
        errors.append("event.schema_version must be 2")
    if not isinstance(event.get("event_id"), str) or not event["event_id"].strip():
        errors.append("event.event_id must be a non-empty string")
    if not isinstance(event.get("type"), str) or not event["type"].strip():
        errors.append("event.type must be a non-empty string")
    if event.get("type") in DETERMINISTIC_EVIDENCE_EVENTS:
        if not _is_number(event.get("score")) or not 0 <= float(event["score"]) <= 1:
            errors.append(f"{event.get('type')}.score must be between 0 and 1")
        if not evidence_objective_ids(event):
            errors.append(f"{event.get('type')} must include concepts, competency_ids, or objective_ids")
    return errors


def is_known_event(event: dict[str, Any]) -> bool:
    return event.get("type") in KNOWN_EVENT_TYPES


def is_deterministic_evidence_event(event: dict[str, Any]) -> bool:
    return event.get("type") in DETERMINISTIC_EVIDENCE_EVENTS


def is_audit_only_event(event: dict[str, Any]) -> bool:
    return event.get("type") in AUDIT_ONLY_EVENTS


def evidence_signal(event: dict[str, Any]) -> EventSignal:
    return EventSignal(
        event_id=str(event["event_id"]),
        event_type=str(event["type"]),
        score=float(event["score"]),
        objective_ids=tuple(evidence_objective_ids(event)),
        timestamp=str(event["ts"]),
    )


def evidence_objective_ids(event: dict[str, Any]) -> list[str]:
    for key in ("competency_ids", "objective_ids", "concepts"):
        values = event.get(key)
        if isinstance(values, list) and values and all(isinstance(value, str) and value.strip() for value in values):
            return [value.strip() for value in values]
    return []


def corrupt_event_record(line_number: int, raw_line: str, error: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "logs/events.ndjson",
        "line_number": line_number,
        "raw": raw_line,
        "error": error,
    }


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
