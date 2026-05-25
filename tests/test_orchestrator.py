"""
Tests covering StateRepository, EventProcessor, Planner, and SessionSnapshot
as defined in docs/spec.md TDD section.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from merge_utils import merge_progress, merge_tasks
from orchestrator import (
    apply_quiz_event,
    build_snapshot,
    build_task,
    generate_tasks,
    process_events,
    StateRepository,
)
from state_utils import append_ndjson, atomic_write_text, load_json, load_ndjson, save_json, update_vmeta


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def repo(tmp_path):
    return StateRepository(tmp_path)


def make_event(event_id: str, score: float, concepts: list[str], ts: str = "2026-01-01T00:00:00Z") -> dict:
    return {"ts": ts, "type": "quiz_completed", "event_id": event_id, "score": score, "concepts": concepts}


def seed_events(repo: StateRepository, events: list[dict]) -> None:
    append_ndjson(repo.root / "logs" / "events.ndjson", events)


def seed_meta(repo: StateRepository, processed_ids: list[str] | None = None) -> dict:
    meta = {"processed_event_ids": processed_ids or [], "last_processed_ts": None}
    save_json(repo.root / "state" / "learner" / "meta.json", meta)
    return meta


# ---------------------------------------------------------------------------
# StateRepository
# ---------------------------------------------------------------------------

class TestStateRepository:
    def test_load_missing_file_returns_empty_dict(self, repo):
        assert repo.load_knowledge_map() == {}

    def test_load_missing_profile_returns_empty_dict(self, repo):
        assert repo.load_profile() == {}

    def test_save_and_reload_json(self, repo):
        data = {"vision-services": {"mastery": 0.5, "confidence": 0.6}}
        repo.save_knowledge_map(data, "test")
        assert repo.load_knowledge_map() == data

    def test_atomic_write_produces_valid_json(self, tmp_path):
        path = tmp_path / "sub" / "file.json"
        save_json(path, {"key": "value"})
        assert json.loads(path.read_text()) == {"key": "value"}

    def test_append_ndjson_produces_parseable_lines(self, tmp_path):
        path = tmp_path / "events.ndjson"
        append_ndjson(path, [{"a": 1}, {"b": 2}])
        rows = load_ndjson(path)
        assert rows == [{"a": 1}, {"b": 2}]

    def test_append_ndjson_is_additive(self, tmp_path):
        path = tmp_path / "events.ndjson"
        append_ndjson(path, [{"a": 1}])
        append_ndjson(path, [{"b": 2}])
        assert load_ndjson(path) == [{"a": 1}, {"b": 2}]

    def test_load_ndjson_skips_corrupt_lines(self, tmp_path):
        path = tmp_path / "events.ndjson"
        path.write_text('{"ok": 1}\nNOT_JSON\n{"ok": 2}\n', encoding="utf-8")
        rows = load_ndjson(path)
        assert rows == [{"ok": 1}, {"ok": 2}]

    def test_write_task_creates_file(self, repo):
        task = {"id": "t-001", "type": "quiz", "objective_ids": ["vision-services"],
                 "estimated_minutes": 10, "created_at": "2026-01-01T00:00:00Z",
                 "source": "orchestrator", "status": "open"}
        repo.write_task(task, "test")
        paths = repo.list_todo_tasks()
        assert len(paths) == 1
        assert load_json(paths[0])["id"] == "t-001"

    def test_vmeta_written_on_save(self, repo):
        data = {"vision-services": {"mastery": 0.5, "confidence": 0.5}}
        repo.save_knowledge_map(data, "test")
        vmeta_dir = repo.root / "_meta" / "vmeta"
        assert any(vmeta_dir.iterdir())


# ---------------------------------------------------------------------------
# EventProcessor (apply_quiz_event + process_events)
# ---------------------------------------------------------------------------

class TestEventProcessor:
    def test_high_score_increases_mastery(self):
        knowledge = {"vision-services": {"mastery": 0.4, "confidence": 0.5}}
        habits: dict = {}
        apply_quiz_event(knowledge, habits, make_event("e1", 0.9, ["vision-services"]))
        assert knowledge["vision-services"]["mastery"] == pytest.approx(0.5, abs=0.01)

    def test_low_score_decreases_mastery(self):
        knowledge = {"vision-services": {"mastery": 0.4, "confidence": 0.5}}
        habits: dict = {}
        apply_quiz_event(knowledge, habits, make_event("e1", 0.3, ["vision-services"]))
        assert knowledge["vision-services"]["mastery"] == pytest.approx(0.35, abs=0.01)

    def test_mid_score_nudges_mastery(self):
        knowledge = {"vision-services": {"mastery": 0.4, "confidence": 0.5}}
        habits: dict = {}
        apply_quiz_event(knowledge, habits, make_event("e1", 0.65, ["vision-services"]))
        assert knowledge["vision-services"]["mastery"] == pytest.approx(0.42, abs=0.01)

    def test_mastery_capped_at_one(self):
        knowledge = {"vision-services": {"mastery": 0.95, "confidence": 0.95}}
        habits: dict = {}
        apply_quiz_event(knowledge, habits, make_event("e1", 0.9, ["vision-services"]))
        assert knowledge["vision-services"]["mastery"] <= 1.0

    def test_mastery_floored_at_zero(self):
        knowledge = {"vision-services": {"mastery": 0.02, "confidence": 0.02}}
        habits: dict = {}
        apply_quiz_event(knowledge, habits, make_event("e1", 0.2, ["vision-services"]))
        assert knowledge["vision-services"]["mastery"] >= 0.0

    def test_unknown_concept_initialised_at_zero(self):
        knowledge: dict = {}
        habits: dict = {}
        apply_quiz_event(knowledge, habits, make_event("e1", 0.9, ["new-concept"]))
        assert "new-concept" in knowledge

    def test_idempotency_same_event_not_double_applied(self, repo):
        seed_events(repo, [make_event("e1", 0.9, ["vision-services"])])
        knowledge = {"vision-services": {"mastery": 0.4, "confidence": 0.5}}
        habits: dict = {}
        progress: dict = {"percentComplete": 0.0, "events": []}
        meta = seed_meta(repo, processed_ids=["e1"])

        knowledge, habits, progress, meta = process_events(repo, knowledge, habits, progress, meta)
        assert knowledge["vision-services"]["mastery"] == pytest.approx(0.4, abs=0.001)

    def test_decision_made_events_not_tracked(self, repo):
        decision_event = {"ts": "2026-01-01T00:00:00Z", "type": "decision_made",
                          "event_id": "decision-001", "tasks_created": 0}
        append_ndjson(repo.root / "logs" / "events.ndjson", [decision_event])
        knowledge: dict = {}
        habits: dict = {}
        progress: dict = {"percentComplete": 0.0, "events": []}
        meta = seed_meta(repo)

        _, _, _, meta = process_events(repo, knowledge, habits, progress, meta)
        assert "decision-001" not in meta.get("processed_event_ids", [])

    def test_derived_assessment_summary_generated(self, repo):
        seed_events(repo, [make_event("e1", 0.9, ["vision-services"])])
        knowledge: dict = {}
        habits: dict = {}
        progress: dict = {"percentComplete": 0.0, "events": []}
        meta = seed_meta(repo)

        _, _, progress, _ = process_events(repo, knowledge, habits, progress, meta)
        assert len(progress["events"]) == 1


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

OBJECTIVES = {
    "vision-services": {"weight": 0.25},
    "language-services": {"weight": 0.25},
    "search-services": {"weight": 0.25},
    "responsible-ai": {"weight": 0.25},
}


class TestPlanner:
    def test_weak_concept_generates_task(self, repo):
        knowledge = {"vision-services": {"mastery": 0.3, "confidence": 0.4}}
        tasks = generate_tasks(repo, knowledge, OBJECTIVES)
        assert len(tasks) == 1
        assert tasks[0]["objective_ids"] == ["vision-services"]

    def test_strong_concept_generates_no_task(self, repo):
        knowledge = {"vision-services": {"mastery": 0.8, "confidence": 0.9}}
        tasks = generate_tasks(repo, knowledge, OBJECTIVES)
        assert tasks == []

    def test_task_cap_enforced(self, repo):
        knowledge = {
            "vision-services": {"mastery": 0.1, "confidence": 0.1},
            "language-services": {"mastery": 0.1, "confidence": 0.1},
            "search-services": {"mastery": 0.1, "confidence": 0.1},
            "responsible-ai": {"mastery": 0.1, "confidence": 0.1},
        }
        tasks = generate_tasks(repo, knowledge, OBJECTIVES, max_new_tasks=3)
        assert len(tasks) <= 3

    def test_no_duplicate_tasks_for_tracked_concept(self, repo):
        existing = {"id": "task-vision-services-001", "type": "quiz",
                    "objective_ids": ["vision-services"], "estimated_minutes": 10,
                    "created_at": "2026-01-01T00:00:00Z", "source": "orchestrator", "status": "open"}
        repo.write_task(existing, "test")

        knowledge = {"vision-services": {"mastery": 0.2, "confidence": 0.3}}
        tasks = generate_tasks(repo, knowledge, OBJECTIVES)
        assert all("vision-services" not in t["objective_ids"] for t in tasks)

    def test_exam_priority_high_weight_first(self, repo):
        objectives = {
            "vision-services": {"weight": 0.10},
            "responsible-ai": {"weight": 0.40},
        }
        knowledge = {
            "vision-services": {"mastery": 0.1, "confidence": 0.1},
            "responsible-ai": {"mastery": 0.1, "confidence": 0.1},
        }
        tasks = generate_tasks(repo, knowledge, objectives, max_new_tasks=1)
        assert tasks[0]["objective_ids"] == ["responsible-ai"]


# ---------------------------------------------------------------------------
# SessionSnapshot
# ---------------------------------------------------------------------------

class TestSessionSnapshot:
    def test_snapshot_contains_mastery_summary(self, repo):
        knowledge = {"vision-services": {"mastery": 0.5, "confidence": 0.6}}
        habits: dict = {}
        snapshot = build_snapshot(knowledge, habits, repo)
        assert "knowledge" in snapshot
        assert "vision-services" in snapshot["knowledge"]

    def test_snapshot_contains_task_count(self, repo):
        snapshot = build_snapshot({}, {}, repo)
        assert "tasks" in snapshot
        assert "todo" in snapshot["tasks"]

    def test_snapshot_has_timestamp_and_is_written(self, repo):
        snapshot = build_snapshot({}, {}, repo)
        assert "timestamp" in snapshot
        repo.write_session_snapshot(snapshot, "test")
        sessions = list((repo.root / "state" / "sessions").glob("*.json"))
        assert len(sessions) == 1

    def test_snapshot_is_immutable_once_written(self, repo):
        snapshot = build_snapshot({"a": {"mastery": 0.5, "confidence": 0.5}}, {}, repo)
        repo.write_session_snapshot(snapshot, "test")
        sessions = list((repo.root / "state" / "sessions").glob("*.json"))
        on_disk = load_json(sessions[0])
        assert on_disk["knowledge"] == snapshot["knowledge"]


# ---------------------------------------------------------------------------
# merge_utils
# ---------------------------------------------------------------------------

class TestMergeUtils:
    def test_merge_progress_appends_new_events(self):
        current = {"percentComplete": 0.0, "events": []}
        result = merge_progress(current, [make_event("e1", 0.8, ["vision-services"])])
        assert len(result["events"]) == 1

    def test_merge_progress_idempotent(self):
        event = make_event("e1", 0.8, ["vision-services"])
        current = {"percentComplete": 0.1, "events": [event]}
        result = merge_progress(current, [event])
        assert len(result["events"]) == 1

    def test_merge_tasks_valid_transition(self):
        current = {"id": "t1", "status": "open"}
        result = merge_tasks(current, {"status": "in_progress"})
        assert result["status"] == "in_progress"

    def test_merge_tasks_invalid_transition_raises(self):
        current = {"id": "t1", "status": "done"}
        with pytest.raises(ValueError):
            merge_tasks(current, {"status": "open"})
