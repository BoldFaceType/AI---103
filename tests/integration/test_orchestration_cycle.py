from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import orchestrator
import state_utils
from orchestrator import StateRepository, baseline_knowledge_map, baseline_objectives, process_events
from state_utils import append_ndjson, load_json, load_ndjson, save_json


def base_event(event_id: str, event_type: str, **overrides):
    data = {
        "schema_version": 2,
        "ts": "2026-07-25T00:00:00Z",
        "type": event_type,
        "event_id": event_id,
    }
    data.update(overrides)
    return data


def seed_repo(tmp_path, monkeypatch) -> StateRepository:
    monkeypatch.setattr(state_utils, "ROOT", tmp_path)
    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    save_json(tmp_path / "state" / "learner" / "knowledge-map.json", baseline_knowledge_map())
    save_json(tmp_path / "state" / "learner" / "habits.json", {"quiz_count": 0})
    save_json(tmp_path / "state" / "learner" / "progress.json", {"percentComplete": 0.0, "events": []})
    save_json(tmp_path / "state" / "learner" / "meta.json", {"processed_event_ids": [], "last_processed_ts": None})
    save_json(tmp_path / "config" / "objectives.ai103.json", baseline_objectives())
    assert load_json(tmp_path / "config" / "objectives.ai103.json")["schema_version"] == 2
    return StateRepository(tmp_path)


def run_process(repo: StateRepository):
    return process_events(
        repo,
        repo.load_knowledge_map(),
        repo.load_habits(),
        repo.load_progress(),
        repo.load_meta(),
        remediation_threshold=0.8,
    )


def test_orchestration_cycle_processes_scoring_events_idempotently(tmp_path, monkeypatch):
    repo = seed_repo(tmp_path, monkeypatch)
    append_ndjson(
        tmp_path / "logs" / "events.ndjson",
        [
            base_event("lesson-1", "lesson_completed", score=0.9, competency_ids=["GA-01"]),
            base_event("feedback-1", "tutor_feedback_received", feedback="coach only"),
            base_event("future-1", "future_event", payload={"retained": True}),
        ],
    )

    knowledge, habits, progress, meta = run_process(repo)
    first_state = json.dumps({"knowledge": knowledge, "habits": habits, "progress": progress, "meta": meta}, sort_keys=True)
    save_json(tmp_path / "state" / "learner" / "knowledge-map.json", knowledge)
    save_json(tmp_path / "state" / "learner" / "habits.json", habits)
    save_json(tmp_path / "state" / "learner" / "progress.json", progress)
    save_json(tmp_path / "state" / "learner" / "meta.json", meta)

    knowledge, habits, progress, meta = run_process(repo)
    second_state = json.dumps({"knowledge": knowledge, "habits": habits, "progress": progress, "meta": meta}, sort_keys=True)

    assert first_state == second_state
    assert knowledge["domains"]["GA"]["mastery"] == 0.1
    assert knowledge["domains"]["GA"]["competencies"]["GA-01"]["mastery"] == 0.1
    assert habits["evidence_event_count"] == 1
    assert sorted(meta["processed_event_ids"]) == ["feedback-1", "future-1", "lesson-1"]
    audit_actions = [row["action"] for row in load_ndjson(tmp_path / "_meta" / "audit.log")]
    assert "audit_only_event" in audit_actions
    assert "skip_unknown_event" in audit_actions


def test_corrupt_and_malformed_events_are_quarantined(tmp_path, monkeypatch):
    repo = seed_repo(tmp_path, monkeypatch)
    events_path = tmp_path / "logs" / "events.ndjson"
    events_path.parent.mkdir(parents=True)
    events_path.write_text(
        "\n".join(
            [
                "NOT_JSON",
                json.dumps(base_event("bad-1", "lab_completed", score="high", competency_ids=["GA-01"]), sort_keys=True),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    knowledge, habits, progress, meta = run_process(repo)

    assert knowledge == repo.load_knowledge_map()
    assert habits == repo.load_habits()
    assert progress == repo.load_progress()
    assert meta == repo.load_meta()
    quarantine = load_ndjson(tmp_path / "_meta" / "quarantine" / "events.ndjson")
    assert len(quarantine) == 2
    assert quarantine[0]["raw"] == "NOT_JSON"
    assert quarantine[1]["event"]["event_id"] == "bad-1"
