from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

import alo
import orchestrator
import state_utils
from merge_utils import merge_feedback, merge_profile
from state_utils import append_audit, append_ndjson, file_sha256, load_json, relative_key, save_json
from validators import validate_event, validate_knowledge_map, validate_objectives, validate_path, validate_profile, validate_task


def write_runtime_state(root: Path) -> None:
    save_json(
        root / "state" / "learner" / "knowledge-map.json",
        {
            "vision-services": {"mastery": 0.4, "confidence": 0.2},
            "language-services": {"mastery": 0.7, "confidence": 0.6},
        },
    )
    save_json(root / "state" / "learner" / "habits.json", {"quiz_count": 1, "last_quiz_ts": "2026-01-01T00:00:00Z"})
    save_json(root / "state" / "learner" / "meta.json", {"processed_event_ids": ["e1"]})
    save_json(
        root / "state" / "tasks" / "todo" / "task-vision.json",
        {
            "id": "task-vision",
            "type": "quiz",
            "objective_ids": ["vision-services"],
            "estimated_minutes": 10,
            "created_at": "2026-01-01T00:00:00Z",
            "source": "test",
            "status": "open",
        },
    )


def test_alo_status_prints_known_and_default_concepts(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(alo, "ROOT", tmp_path)
    write_runtime_state(tmp_path)

    alo.cmd_status(argparse.Namespace())

    output = capsys.readouterr().out
    assert "vision-services" in output
    assert "responsible-ai" in output
    assert "task-vision" not in output
    assert "events processed:  1" in output


def test_alo_log_appends_event_and_rejects_invalid_score(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(alo, "ROOT", tmp_path)
    alo.cmd_log(argparse.Namespace(concept="search-services", score=0.75, id="quiz-1"))

    events = [json.loads(line) for line in (tmp_path / "logs" / "events.ndjson").read_text().splitlines()]
    assert events == [
        {
            "concepts": ["search-services"],
            "event_id": "quiz-1",
            "score": 0.75,
            "ts": events[0]["ts"],
            "type": "quiz_completed",
        }
    ]
    assert "Logged:" in capsys.readouterr().out

    with pytest.raises(SystemExit):
        alo.cmd_log(argparse.Namespace(concept="search-services", score=1.5, id="bad-score"))


def test_alo_parser_and_delegating_commands(monkeypatch, capsys):
    called: list[str] = []
    monkeypatch.setattr(orchestrator, "initialize", lambda: called.append("init"))
    monkeypatch.setattr(orchestrator, "main", lambda: called.append("run"))

    parser = alo.build_parser()
    assert parser.parse_args(["status"]).command == "status"

    alo.cmd_init(argparse.Namespace())
    alo.cmd_run(argparse.Namespace())

    assert called == ["init", "run"]
    assert sys.argv == ["orchestrator.py"]
    output = capsys.readouterr().out
    assert "Initialized." in output
    assert "Cycle complete." in output


def test_validators_accept_valid_shapes_and_report_invalid_shapes(tmp_path):
    assert validate_profile({"name": "A", "primary_goal": "Pass", "preferences": {}}) == []
    assert validate_objectives({"vision": {"weight": 0.2}}) == []
    assert validate_knowledge_map({"vision": {"mastery": 0.1, "confidence": 1.0}}) == []
    assert validate_task(
        {
            "id": "task-1",
            "type": "quiz",
            "objective_ids": ["vision"],
            "estimated_minutes": 10,
            "created_at": "2026-01-01T00:00:00Z",
            "source": "test",
            "status": "open",
        }
    ) == []
    assert validate_event({"ts": "2026-01-01T00:00:00Z", "type": "quiz_completed", "event_id": "e1", "score": 1, "concepts": ["vision"]}) == []

    assert "profile.name must be a non-empty string" in validate_profile({"name": "", "primary_goal": "", "preferences": []})
    assert validate_objectives({}) == ["objectives must be a non-empty object"]
    assert "objective ids must be non-empty strings" in validate_objectives({"": {"weight": 1}})
    assert "objective 'bad' must map to an object" in validate_objectives({"bad": []})
    assert "objective 'bad' weight must be a non-negative number" in validate_objectives({"bad": {"weight": -1}})
    assert validate_knowledge_map([]) == ["knowledge map must be an object"]
    assert "knowledge entry 'bad' must be an object" in validate_knowledge_map({"bad": 1})
    assert "knowledge entry 'bad' field 'mastery' must be between 0 and 1" in validate_knowledge_map({"bad": {"mastery": 2, "confidence": False}})
    assert "task missing required field 'id'" in validate_task({"status": "blocked", "objective_ids": "vision", "estimated_minutes": 0})
    assert "quiz_completed.score must be numeric" in validate_event({"type": "quiz_completed"})
    assert "quiz_completed.concepts must be a non-empty list" in validate_event({"type": "quiz_completed", "score": 0.5, "ts": "now", "event_id": "e"})

    assert validate_path(Path("profile.user.json"), {"name": "A", "primary_goal": "Pass"}) == []
    assert validate_path(Path("objectives.ai103.json"), {"vision": {"weight": 0}}) == []
    assert validate_path(Path("knowledge-map.json"), {}) == []
    assert "task missing required field 'id'" in validate_path(tmp_path / "todo" / "x.json", {})
    assert validate_path(tmp_path / "raw" / "x.json", []) == []
    assert validate_path(Path("unknown.json"), {}) == []


def test_state_utils_defaults_hash_relative_key_and_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(state_utils, "ROOT", tmp_path)
    path = tmp_path / "nested" / "data.json"

    assert load_json(path) == {}
    assert load_json(path, default=[]) == []
    save_json(path, {"a": 1})
    assert load_json(path) == {"a": 1}
    path.write_text("{", encoding="utf-8")
    assert load_json(path, default={"fallback": True}) == {"fallback": True}
    path.write_text("hash-me", encoding="utf-8")

    assert file_sha256(path)
    assert relative_key(path, tmp_path) == "nested/data.json"

    append_audit("test", "nested/data.json", "pytest", "ok", {"x": 1})
    audit_rows = [json.loads(line) for line in (tmp_path / "_meta" / "audit.log").read_text().splitlines()]
    assert audit_rows[0]["details"] == {"x": 1}


def test_repository_methods_bootstrap_run_once_and_initialize(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setattr(state_utils, "ROOT", tmp_path)

    orchestrator.initialize()
    repo = orchestrator.StateRepository(tmp_path)
    assert repo.load_profile()["primary_goal"] == "Pass AI-103"
    assert repo.load_objectives()["vision-services"]["weight"] == 0.25
    assert repo.load_habits()["quiz_count"] == 0
    assert repo.load_progress()["percentComplete"] == 0.0
    assert repo.load_meta()["processed_event_ids"] == []

    repo.append_event(
        {
            "ts": "2026-01-02T00:00:00Z",
            "type": "quiz_completed",
            "event_id": "quiz-extra",
            "score": 0.9,
            "concepts": ["language-services"],
        }
    )
    orchestrator.run_once()

    assert repo.load_knowledge_map()["language-services"]["mastery"] == 0.1
    assert repo.load_habits()["quiz_count"] == 2
    assert "quiz-extra" in repo.load_meta()["processed_event_ids"]
    assert repo.list_todo_tasks()
    assert list((tmp_path / "state" / "sessions").glob("*.json"))
    assert (tmp_path / "_meta" / "audit.log").exists()


def test_orchestrator_error_and_branch_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setattr(state_utils, "ROOT", tmp_path)
    repo = orchestrator.StateRepository(tmp_path)

    with pytest.raises(ValueError, match="bad validation failed"):
        orchestrator.require_valid("bad", ["broken"])

    assert repo.list_todo_tasks() == []
    append_ndjson(
        tmp_path / "logs" / "events.ndjson",
        [
            {"ts": "2026-01-01T00:00:00Z", "type": "bad", "event_id": "skip"},
            {"ts": "2026-01-01T00:00:00Z", "type": "quiz_completed", "event_id": "bad-quiz", "score": "x", "concepts": []},
        ],
    )
    knowledge, habits, progress, meta = orchestrator.process_events(repo, {}, {}, {}, {})
    assert knowledge == {}
    assert habits == {}
    assert progress == {}
    assert meta == {}
    assert (tmp_path / "_meta" / "audit.log").exists()

    high_weight_task = orchestrator.build_task("vision services", 0.3)
    low_weight_task = orchestrator.build_task("search", 0.2)
    assert high_weight_task["estimated_minutes"] == 15
    assert low_weight_task["estimated_minutes"] == 10
    orchestrator.write_tasks(repo, [low_weight_task])
    assert repo.load_task(repo.list_todo_tasks()[0])["id"] == low_weight_task["id"]


def test_merge_helpers():
    assert merge_profile({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
    assert merge_feedback([{"id": 1}], [{"id": 2}]) == [{"id": 1}, {"id": 2}]
