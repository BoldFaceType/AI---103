from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.learning.events import (
    corrupt_event_record,
    evidence_objective_ids,
    evidence_signal,
    is_audit_only_event,
    is_deterministic_evidence_event,
    is_known_event,
    validate_learning_event,
)


def event(event_type: str = "lesson_completed", **overrides):
    data = {
        "schema_version": 2,
        "ts": "2026-07-25T00:00:00Z",
        "type": event_type,
        "event_id": "event-1",
        "score": 0.9,
        "competency_ids": ["GA-01"],
    }
    data.update(overrides)
    return data


def test_known_event_classes_are_explicit():
    assert is_known_event(event("lesson_completed"))
    assert is_deterministic_evidence_event(event("lab_completed"))
    assert is_audit_only_event(event("tutor_feedback_received", score=None, competency_ids=[]))
    assert not is_known_event(event("future_event"))


def test_learning_event_requires_version_and_deterministic_evidence_fields():
    errors = validate_learning_event({"type": "lesson_completed", "event_id": "e"})

    assert "event.schema_version must be 2" in errors
    assert "lesson_completed.score must be between 0 and 1" in errors
    assert "lesson_completed must include concepts, competency_ids, or objective_ids" in errors


def test_evidence_signal_extracts_score_timestamp_and_objectives():
    signal = evidence_signal(event("review_completed", score=0.75, objective_ids=["PM-01"], competency_ids=[]))

    assert signal.event_id == "event-1"
    assert signal.event_type == "review_completed"
    assert signal.score == 0.75
    assert signal.objective_ids == ("PM-01",)


def test_objective_extraction_prefers_competencies_then_objectives_then_concepts():
    assert evidence_objective_ids(event(competency_ids=["GA-02"], objective_ids=["PM-01"])) == ["GA-02"]
    assert evidence_objective_ids(event(competency_ids=[], objective_ids=["PM-01"], concepts=["legacy"])) == ["PM-01"]
    assert evidence_objective_ids(event(competency_ids=[], objective_ids=[], concepts=["legacy"])) == ["legacy"]


def test_corrupt_event_record_is_diagnostic_not_silent():
    record = corrupt_event_record(3, "NOT_JSON", "decode failed")

    assert record["line_number"] == 3
    assert record["raw"] == "NOT_JSON"
    assert record["error"] == "decode failed"
