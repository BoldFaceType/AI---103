from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import alo


def setup_runtime_root(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "state" / "learner").mkdir(parents=True)
    (tmp_path / "state" / "tasks" / "todo").mkdir(parents=True)
    (tmp_path / "content" / "lessons" / "ai103" / "ga").mkdir(parents=True)
    (tmp_path / "fixtures" / "azure-responses").mkdir(parents=True)
    (tmp_path / "config" / "learning-policy.json").write_text('{"remediation_threshold":0.8}', encoding="utf-8")
    (tmp_path / "state" / "learner" / "knowledge-map.json").write_text(
        '{"schema_version":2,"domains":{"GA":{"mastery":0.2,"confidence":0.3}}}', encoding="utf-8"
    )
    (tmp_path / "state" / "learner" / "habits.json").write_text('{"quiz_count":0}', encoding="utf-8")
    (tmp_path / "state" / "learner" / "meta.json").write_text('{"processed_event_ids":[]}', encoding="utf-8")
    (tmp_path / "content" / "lessons" / "ai103" / "ga" / "GA-01.md").write_text("# GA-01\n\nRetrieval practice.", encoding="utf-8")
    shutil.copyfile(
        ROOT / "fixtures" / "azure-responses" / "LAB-MEDIA-GENERATION.offline.json",
        tmp_path / "fixtures" / "azure-responses" / "LAB-MEDIA-GENERATION.offline.json",
    )


def events(root: Path) -> list[dict[str, object]]:
    path = root / "logs" / "events.ndjson"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_parser_includes_complete_t27_workflow_commands():
    parser = alo.build_parser()

    commands = (
        ["status", "--json"],
        ["doctor", "--offline"],
        ["curriculum", "audit", "--json"],
        ["lesson", "next", "--json"],
        ["lesson", "show", "GA-01"],
        ["lesson", "complete", "GA-01", "--json"],
        ["quiz", "start", "GA-01", "--json"],
        ["quiz", "submit", "GA-01", "0.9", "--json"],
        ["quiz", "review", "--json"],
        ["lab", "list", "--json"],
        ["lab", "run", "LAB-MEDIA-GENERATION", "--offline", "--json"],
        ["lab", "teardown", "LAB-MEDIA-GENERATION", "--json"],
        ["tutor", "GA-01", "--json"],
        ["review", "due", "--json"],
        ["session", "start", "--json"],
        ["session", "resume", "--json"],
        ["session", "finish", "--json"],
        ["migrate", "--dry-run", "--json"],
    )
    for argv in commands:
        assert parser.parse_args(argv).command == argv[0]


def test_complete_offline_session_runs_from_retrieval_through_snapshot(tmp_path, monkeypatch, capsys):
    setup_runtime_root(tmp_path)
    monkeypatch.setattr(alo, "ROOT", tmp_path)

    alo.cmd_session(argparse.Namespace(session_command="start", id="session-1", json=True))
    alo.cmd_lesson(argparse.Namespace(lesson_command="complete", lesson_id="GA-01", score=1.0, id="lesson-1", json=True))
    alo.cmd_quiz(argparse.Namespace(quiz_command="submit", objective_id="GA-01", score=0.9, id="quiz-1", json=True))
    alo.cmd_lab(argparse.Namespace(lab_command="run", lab_id="LAB-MEDIA-GENERATION", offline=True, live=False, id="lab-1", json=True))
    alo.cmd_session(argparse.Namespace(session_command="finish", json=True))

    rows = events(tmp_path)
    assert [row["event_id"] for row in rows] == ["lesson-1", "quiz-1", "lab-1"]
    assert {row["type"] for row in rows} == {"lesson_completed", "quiz_completed", "lab_completed"}
    assert (tmp_path / "_meta" / "cli-audit.ndjson").exists()
    assert json.loads((tmp_path / "state" / "sessions" / "current.json").read_text(encoding="utf-8"))["status"] == "finished"
    assert capsys.readouterr().out


def test_interrupted_session_resumes_safely_and_events_are_idempotent(tmp_path, monkeypatch):
    setup_runtime_root(tmp_path)
    monkeypatch.setattr(alo, "ROOT", tmp_path)

    alo.cmd_session(argparse.Namespace(session_command="start", id="session-1", json=True))
    alo.cmd_session(argparse.Namespace(session_command="resume", json=True))
    alo.cmd_quiz(argparse.Namespace(quiz_command="submit", objective_id="GA-01", score=0.8, id="quiz-same", json=True))
    alo.cmd_quiz(argparse.Namespace(quiz_command="submit", objective_id="GA-01", score=0.8, id="quiz-same", json=True))

    assert [row["event_id"] for row in events(tmp_path)] == ["quiz-same"]


def test_invalid_input_never_partially_updates_state(tmp_path, monkeypatch):
    setup_runtime_root(tmp_path)
    monkeypatch.setattr(alo, "ROOT", tmp_path)

    with pytest.raises(SystemExit, match="score"):
        alo.cmd_quiz(argparse.Namespace(quiz_command="submit", objective_id="GA-01", score=1.5, id="bad", json=True))
    with pytest.raises(SystemExit, match="unknown lab"):
        alo.cmd_lab(argparse.Namespace(lab_command="run", lab_id="NOT-A-LAB", offline=True, live=False, id="bad-lab", json=True))

    assert events(tmp_path) == []


def test_live_lab_mode_is_visually_explicit_and_refuses_implicit_adapter(tmp_path, monkeypatch):
    setup_runtime_root(tmp_path)
    monkeypatch.setattr(alo, "ROOT", tmp_path)

    with pytest.raises(SystemExit, match="refusing implicit live mode"):
        alo.cmd_lab(argparse.Namespace(lab_command="run", lab_id="LAB-MEDIA-GENERATION", offline=False, live=True, id="", json=True))


def test_json_status_and_lab_list_are_machine_readable(tmp_path, monkeypatch, capsys):
    setup_runtime_root(tmp_path)
    monkeypatch.setattr(alo, "ROOT", tmp_path)

    alo.cmd_status(argparse.Namespace(json=True))
    status = json.loads(capsys.readouterr().out)
    assert status["remediation_threshold"] == 0.8

    alo.cmd_lab(argparse.Namespace(lab_command="list", json=True))
    labs = json.loads(capsys.readouterr().out)["labs"]
    assert "LAB-MEDIA-GENERATION" in labs

