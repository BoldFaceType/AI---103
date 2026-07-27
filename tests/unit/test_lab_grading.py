from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.labs.grading import LabValidationError, grade_lab_output, lab_result_to_event, normalize_lab_output, validate_lab_result
from ai103.labs.registry import get_lab_spec
from ai103.learning.events import validate_learning_event


def test_same_fixture_produces_same_grade():
    spec = get_lab_spec("LAB-SEARCH-RAG", ROOT)
    raw = json.loads(spec.fixture_path.read_text(encoding="utf-8"))

    first = grade_lab_output(spec, normalize_lab_output(raw), mode="offline")
    second = grade_lab_output(spec, normalize_lab_output(raw), mode="offline")

    comparable_first = first | {"started_at": "<time>", "completed_at": "<time>"}
    comparable_second = second | {"started_at": "<time>", "completed_at": "<time>"}
    assert comparable_first == comparable_second
    assert first["score"] == 1.0
    assert all(check["passed"] for check in first["checks"])
    validate_lab_result(first)


def test_live_raw_output_is_normalized_before_grading():
    spec = get_lab_spec("LAB-SEARCH-RAG", ROOT)
    raw = json.loads((ROOT / "fixtures" / "azure-responses" / "LAB-SEARCH-RAG.live-raw.json").read_text(encoding="utf-8"))

    result = grade_lab_output(spec, normalize_lab_output(raw), mode="live")

    assert result["score"] == 1.0
    assert result["mode"] == "live"
    assert result["cost_estimate"] == {"currency": "USD", "estimated": 0.02}
    assert "<redacted-id>" in result["resource_ids"][0]
    assert "00000000-1111-2222-3333-444444444444" not in result["resource_ids"][0]


def test_result_contract_rejects_section_10_shape_errors():
    with pytest.raises(LabValidationError, match="lab result missing fields"):
        validate_lab_result({"schema_version": 1})

    spec = get_lab_spec("LAB-SEARCH-RAG", ROOT)
    raw = json.loads(spec.fixture_path.read_text(encoding="utf-8"))
    result = grade_lab_output(spec, normalize_lab_output(raw), mode="offline")
    result["score"] = 1.5

    with pytest.raises(LabValidationError, match="score must be between 0 and 1"):
        validate_lab_result(result)


def test_missing_response_shape_is_not_gradable():
    spec = get_lab_spec("LAB-SEARCH-RAG", ROOT)
    raw = json.loads(spec.fixture_path.read_text(encoding="utf-8"))
    del raw["responses"]["search"]

    with pytest.raises(LabValidationError, match="missing Azure response shapes: search"):
        grade_lab_output(spec, normalize_lab_output(raw), mode="offline")


def test_passing_lab_result_converts_to_valid_learning_event():
    spec = get_lab_spec("LAB-SEARCH-RAG", ROOT)
    raw = json.loads(spec.fixture_path.read_text(encoding="utf-8"))
    result = grade_lab_output(spec, normalize_lab_output(raw), mode="offline")

    event = lab_result_to_event(result, event_id="lab-event-1")

    assert event["schema_version"] == 2
    assert event["type"] == "lab_completed"
    assert event["score"] == 1.0
    assert event["objective_ids"] == ["GA-02", "IE-02", "IE-04"]
    assert validate_learning_event(event) == []

