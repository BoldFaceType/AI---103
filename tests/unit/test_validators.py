from __future__ import annotations

from validators import validate_event, validate_knowledge_map, validate_objectives, validate_task


def test_v2_objectives_require_ai103_domains_weights_and_competencies():
    valid = {
        "schema_version": 2,
        "exam": "AI-103",
        "objectives": {
            "PM": {"weight": 0.275, "competency_ids": ["PM-01"]},
            "GA": {"weight": 0.325, "competency_ids": ["GA-01"]},
            "CV": {"weight": 0.133, "competency_ids": ["CV-01"]},
            "TA": {"weight": 0.133, "competency_ids": ["TA-01"]},
            "IE": {"weight": 0.134, "competency_ids": ["IE-01"]},
        },
    }

    assert validate_objectives(valid) == []

    invalid = {"schema_version": 2, "objectives": {"legacy": {"weight": 1.0, "competency_ids": []}}}
    errors = validate_objectives(invalid)
    assert "objectives.objectives keys must be exactly PM, GA, CV, TA, and IE" in errors
    assert "objective 'legacy' competency_ids must be a non-empty list" in errors


def test_v2_knowledge_map_validates_domains_ranges_and_evidence_refs():
    valid = {
        "schema_version": 2,
        "exam": "AI-103",
        "domains": {
            "PM": {"mastery": 0.0, "confidence": 1.0, "evidence_refs": []},
            "GA": {"mastery": 0.1, "confidence": 0.9, "evidence_refs": ["quiz-1"]},
            "CV": {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []},
            "TA": {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []},
            "IE": {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []},
        },
        "legacy_evidence": {},
    }

    assert validate_knowledge_map(valid) == []

    errors = validate_knowledge_map(
        {"schema_version": 2, "domains": {"bad": {"mastery": 2, "confidence": 0, "evidence_refs": "x"}}}
    )
    assert "knowledge-map.domains keys must be exactly PM, GA, CV, TA, and IE" in errors
    assert "knowledge entry 'bad' field 'mastery' must be between 0 and 1" in errors
    assert "knowledge entry 'bad' evidence_refs must be a list" in errors


def test_legacy_shapes_remain_valid():
    assert validate_objectives({"vision-services": {"weight": 0.25}}) == []
    assert validate_knowledge_map({"vision-services": {"mastery": 0.1, "confidence": 0.2}}) == []


def test_events_and_tasks_validate_schema_and_timestamps():
    assert validate_event(
        {
            "schema_version": 2,
            "ts": "2026-01-01T00:00:00Z",
            "type": "quiz_completed",
            "event_id": "quiz-1",
            "score": 0.8,
            "concepts": ["PM"],
        }
    ) == []
    assert validate_task(
        {
            "schema_version": 2,
            "id": "task-PM-1",
            "type": "quiz",
            "objective_ids": ["PM"],
            "estimated_minutes": 10,
            "created_at": "2026-01-01T00:00:00Z",
            "source": "test",
            "status": "open",
        }
    ) == []

    assert "event.ts must be an ISO timestamp" in validate_event({"ts": "now", "type": "decision_made", "event_id": "e"})
    assert "task.created_at must be an ISO timestamp" in validate_task(
        {
            "schema_version": 2,
            "id": "task-PM-1",
            "type": "quiz",
            "objective_ids": ["PM"],
            "estimated_minutes": 10,
            "created_at": "soon",
            "source": "test",
            "status": "open",
        }
    )
