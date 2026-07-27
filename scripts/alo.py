"""ALO CLI — Adaptive Learning Orchestrator interface."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "src"))

SCHEMA_VERSION = 2
LEGACY_CONCEPTS = ["vision-services", "language-services", "search-services", "responsible-ai"]
AI103_CONCEPTS = ["PM", "GA", "CV", "TA", "IE"]
CONCEPTS = LEGACY_CONCEPTS + AI103_CONCEPTS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def append_audit(action: str, target: str, status: str, details: dict[str, Any] | None = None) -> None:
    path = ROOT / "_meta" / "cli-audit.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"schema_version": SCHEMA_VERSION, "ts": utc_now(), "action": action, "target": target, "status": status, "details": details or {}}
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing + json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")


def existing_event_ids() -> set[str]:
    path = ROOT / "logs" / "events.ndjson"
    if not path.exists():
        return set()
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event.get("event_id"), str):
            ids.add(event["event_id"])
    return ids


def append_event_once(event: dict[str, Any]) -> bool:
    if event["event_id"] in existing_event_ids():
        append_audit("event.skip_duplicate", event["event_id"], "ok", {"type": event["type"]})
        return False
    log_path = ROOT / "logs/events.ndjson"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    log_path.write_text(existing + json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")
    append_audit("event.append", event["event_id"], "ok", {"type": event["type"]})
    return True


def make_event(event_type: str, event_id: str, objective_ids: list[str], score: float = 1.0) -> dict[str, Any]:
    if not objective_ids or not all(objective_ids):
        raise SystemExit("Error: at least one objective ID is required.")
    if not 0 <= score <= 1:
        raise SystemExit("Error: score must be between 0.0 and 1.0.")
    return {
        "schema_version": SCHEMA_VERSION,
        "ts": utc_now(),
        "type": event_type,
        "event_id": event_id,
        "score": score,
        "objective_ids": objective_ids,
    }


def lesson_paths() -> list[Path]:
    return sorted((ROOT / "content" / "lessons" / "ai103").glob("*/*.md"))


def task_paths(status: str | None = None) -> list[Path]:
    paths = sorted((ROOT / "state" / "tasks" / "todo").glob("*.json")) if (ROOT / "state" / "tasks" / "todo").exists() else []
    if status is None:
        return paths
    return [path for path in paths if load_json(path).get("status") == status]


def cmd_status(args: argparse.Namespace) -> None:
    km = load_json(ROOT / "state/learner/knowledge-map.json")
    habits = load_json(ROOT / "state/learner/habits.json")
    meta = load_json(ROOT / "state/learner/meta.json")
    learning_policy = load_json(ROOT / "config/learning-policy.json")
    remediation_threshold = float(learning_policy.get("remediation_threshold", 0.8))
    tasks = sorted((ROOT / "state/tasks/todo").glob("*.json")) if (ROOT / "state/tasks/todo").exists() else []
    if getattr(args, "json", False):
        print_json(
            {
                "remediation_threshold": remediation_threshold,
                "knowledge": km,
                "todo_count": len(tasks),
                "quiz_count": habits.get("quiz_count", 0),
                "events_processed": len(meta.get("processed_event_ids", [])),
            }
        )
        return

    print(f"\n=== Learning Policy ===\n  remediation threshold: {remediation_threshold:.0%}")

    print("\n=== Knowledge Map ===")
    display_map = km.get("domains", km)
    display_concepts = AI103_CONCEPTS if "domains" in km else LEGACY_CONCEPTS
    for concept in display_concepts:
        v = display_map.get(concept, {"mastery": 0.0, "confidence": 0.0})
        mastery = v["mastery"]
        filled = int(mastery * 10)
        bar = "#" * filled + "." * (10 - filled)
        print(f"  {concept:<22} mastery={mastery:.0%}  [{bar}]  confidence={v['confidence']:.0%}")

    print(f"\n=== Todo Tasks ({len(tasks)}) ===")
    if tasks:
        for t in tasks:
            d = load_json(t)
            print(f"  {', '.join(d['objective_ids']):<22} {d['estimated_minutes']}m  [{d['status']}]")
    else:
        print("  none")

    print("\n=== Session Stats ===")
    print(f"  quizzes logged:    {habits.get('quiz_count', 0)}")
    print(f"  last quiz:         {habits.get('last_quiz_ts') or 'never'}")
    print(f"  events processed:  {len(meta.get('processed_event_ids', []))}")
    print()


def cmd_log(args: argparse.Namespace) -> None:
    score = args.score
    if not 0.0 <= score <= 1.0:
        print(f"Error: score must be between 0.0 and 1.0 (got {score})")
        sys.exit(1)
    if args.concept not in CONCEPTS:
        print(f"Error: concept must be one of: {', '.join(CONCEPTS)}")
        sys.exit(1)

    event_id = args.id or f"quiz-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    event = {
        "schema_version": SCHEMA_VERSION,
        "ts": utc_now(),
        "type": "quiz_completed",
        "event_id": event_id,
        "score": score,
        "concepts": [args.concept],
    }

    appended = append_event_once(event)

    print(f"{'Logged' if appended else 'Already logged'}:  {args.concept}  score={score:.0%}  id={event_id}")
    print("Run 'python scripts/alo.py run' to process.")


def cmd_run(_args: argparse.Namespace) -> None:
    from orchestrator import main as orch_main
    sys.argv = ["orchestrator.py"]
    orch_main()
    print("Cycle complete. Run 'python scripts/alo.py status' to see updated state.")


def cmd_init(_args: argparse.Namespace) -> None:
    from orchestrator import initialize
    initialize()
    print("Initialized. Run 'python scripts/alo.py status' to confirm.")


def cmd_doctor(args: argparse.Namespace) -> None:
    from ai103.operations.doctor import main as doctor_main

    code = doctor_main(root=ROOT, live=args.live)
    raise SystemExit(code)


def cmd_curriculum(args: argparse.Namespace) -> None:
    if args.curriculum_command != "audit":
        raise SystemExit("Error: curriculum command must be audit.")
    import curriculum_audit

    errors, report = curriculum_audit.audit(domain=args.domain)
    if args.json:
        print_json({"ok": not errors, "errors": errors, "report": report})
    else:
        print("\n".join(report))
        print("Audit passed." if not errors else "Audit failed.")
    if errors:
        raise SystemExit(1)


def cmd_lesson(args: argparse.Namespace) -> None:
    if args.lesson_command == "next":
        lesson = lesson_paths()[0]
        payload = {"lesson_id": lesson.stem, "path": lesson.relative_to(ROOT).as_posix()}
        print_json(payload) if args.json else print(f"{payload['lesson_id']}  {payload['path']}")
        return
    if args.lesson_command == "show":
        path = next((path for path in lesson_paths() if path.stem == args.lesson_id), None)
        if path is None:
            raise SystemExit(f"Error: unknown lesson: {args.lesson_id}")
        text = path.read_text(encoding="utf-8")
        print_json({"lesson_id": args.lesson_id, "content": text}) if args.json else print(text)
        return
    if args.lesson_command == "complete":
        event_id = args.id or f"lesson-{args.lesson_id}"
        appended = append_event_once(make_event("lesson_completed", event_id, [args.lesson_id], score=args.score))
        payload = {"event_id": event_id, "appended": appended, "lesson_id": args.lesson_id}
        print_json(payload) if args.json else print(f"{'Completed' if appended else 'Already complete'}: {args.lesson_id}")
        return
    raise SystemExit("Error: unknown lesson command.")


def cmd_quiz(args: argparse.Namespace) -> None:
    if args.quiz_command == "start":
        payload = {"objective_id": args.objective_id, "mode": "offline", "question": "Recall one key AI-103 design decision."}
        print_json(payload) if args.json else print(f"{payload['objective_id']}: {payload['question']}")
        return
    if args.quiz_command == "submit":
        event_id = args.id or f"quiz-{args.objective_id}"
        appended = append_event_once(make_event("quiz_completed", event_id, [args.objective_id], score=args.score))
        payload = {"event_id": event_id, "appended": appended, "objective_id": args.objective_id, "score": args.score}
        print_json(payload) if args.json else print(f"{'Submitted' if appended else 'Already submitted'}: {args.objective_id} score={args.score:.0%}")
        return
    if args.quiz_command == "review":
        events = sorted(existing_event_ids())
        print_json({"quiz_event_ids": events}) if args.json else print("\n".join(events))
        return
    raise SystemExit("Error: unknown quiz command.")


def cmd_lab(args: argparse.Namespace) -> None:
    from ai103.labs.registry import default_registry
    from ai103.labs.runner import run_lab

    registry = default_registry(ROOT)
    if args.lab_command == "list":
        payload = {"labs": sorted(registry)}
        print_json(payload) if args.json else print("\n".join(payload["labs"]))
        return
    if args.lab_command == "run":
        if args.live:
            raise SystemExit("Error: live lab mode requires a lab-specific explicit adapter; refusing implicit live mode.")
        if args.lab_id not in registry:
            raise SystemExit(f"Error: unknown lab: {args.lab_id}")
        run = run_lab(args.lab_id, root=ROOT, mode="offline", event_id=args.id or f"lab-{args.lab_id}")
        if run.event is not None:
            append_event_once(run.event)
        payload = {"result": run.result, "event": run.event}
        print_json(payload) if args.json else print(f"{args.lab_id}: score={run.result['score']:.0%}")
        return
    if args.lab_command == "teardown":
        if args.lab_id not in registry:
            raise SystemExit(f"Error: unknown lab: {args.lab_id}")
        append_audit("lab.teardown", args.lab_id, "ok", {"mode": "offline"})
        payload = {"lab_id": args.lab_id, "teardown": "offline-noop"}
        print_json(payload) if args.json else print(f"{args.lab_id}: offline teardown noop")
        return
    raise SystemExit("Error: unknown lab command.")


def cmd_tutor(args: argparse.Namespace) -> None:
    from ai103.services.settings import AzureServiceSettings
    from ai103.tutor.client import offline_tutor_response, request_tutor_response
    from ai103.tutor.context import build_tutor_context, load_approved_sources

    sources = load_approved_sources(ROOT)
    context = build_tutor_context(
        lesson_id=args.lesson_id,
        competency_ids=[args.lesson_id],
        zpd_level=args.zpd_level,
        learner_attempt=args.learner_attempt,
        retrieved_text="Offline tutor context from approved AI-103 lesson material.",
        approved_sources=sources,
    )
    output = request_tutor_response(
        context,
        settings=AzureServiceSettings(
            foundry_project_endpoint="https://acct.services.ai.azure.com/api/projects/offline",
            foundry_model_name="offline-tutor",
        ),
        root=ROOT,
        offline_response=offline_tutor_response(context),
    )
    print_json(output.as_event_payload()) if args.json else print(output.response_markdown)


def cmd_review(args: argparse.Namespace) -> None:
    if args.review_command != "due":
        raise SystemExit("Error: review command must be due.")
    due = [load_json(path) for path in task_paths("open") if load_json(path).get("type") == "review"]
    print_json({"due": due}) if args.json else print("\n".join(task["id"] for task in due) if due else "none")


def cmd_session(args: argparse.Namespace) -> None:
    path = ROOT / "state" / "sessions" / "current.json"
    if args.session_command == "start":
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            payload = load_json(path) | {"resumed": True}
        else:
            payload = {"schema_version": SCHEMA_VERSION, "session_id": args.id or f"session-{utc_now()}", "started_at": utc_now(), "status": "active"}
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            append_audit("session.start", payload["session_id"], "ok")
        print_json(payload) if args.json else print(f"Session active: {payload['session_id']}")
        return
    if args.session_command == "resume":
        if not path.exists():
            raise SystemExit("Error: no active session to resume.")
        payload = load_json(path) | {"resumed": True}
        print_json(payload) if args.json else print(f"Session resumed: {payload['session_id']}")
        return
    if args.session_command == "finish":
        if not path.exists():
            raise SystemExit("Error: no active session to finish.")
        payload = load_json(path) | {"status": "finished", "finished_at": utc_now()}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        append_audit("session.finish", payload["session_id"], "ok")
        print_json(payload) if args.json else print(f"Session finished: {payload['session_id']}")
        return
    raise SystemExit("Error: unknown session command.")


def cmd_migrate(args: argparse.Namespace) -> None:
    path = ROOT / "scripts" / "migrations" / "001_ai103_domains.py"
    spec = importlib.util.spec_from_file_location("migration_001_ai103_domains", path)
    if spec is None or spec.loader is None:
        raise SystemExit("Error: unable to load AI-103 migration.")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    objectives, knowledge, errors = migration.migration_plan(ROOT)
    if errors:
        raise SystemExit("Error: migration blocked: " + "; ".join(errors))
    if args.dry_run:
        result = {"dry_run": True, "objectives_schema": objectives.get("schema_version"), "knowledge_schema": knowledge.get("schema_version"), "writes": []}
    else:
        backups = migration.write_migration(ROOT, objectives, knowledge)
        result = {"dry_run": False, "backups": [path.relative_to(ROOT).as_posix() for path in backups]}
        append_audit("migrate", "ai103-schema", "ok", result)
    print_json(result) if args.json else print("Migration dry run complete." if args.dry_run else "Migration complete.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alo",
        description="Adaptive Learning Orchestrator CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Show knowledge map, tasks, and session stats")
    status.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    sub.add_parser("run", help="Process events and update learner state")
    sub.add_parser("init", help="Create baseline folders and sample files")

    doctor = sub.add_parser("doctor", help="Run local and optional live Azure readiness diagnostics")
    mode = doctor.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="Run local diagnostics only; this is the default")
    mode.add_argument("--live", action="store_true", help="Run read-only Azure readiness checks")

    log = sub.add_parser("log", help="Record a quiz result")
    log.add_argument("concept", choices=CONCEPTS, help="Concept area tested")
    log.add_argument("score", type=float, help="Score as decimal, e.g. 0.72")
    log.add_argument("--id", default="", help="Optional event ID (auto-generated if omitted)")

    curriculum = sub.add_parser("curriculum", help="Curriculum commands")
    curriculum_sub = curriculum.add_subparsers(dest="curriculum_command", required=True)
    curriculum_audit = curriculum_sub.add_parser("audit", help="Audit curriculum coverage")
    curriculum_audit.add_argument("--domain", choices=AI103_CONCEPTS)
    curriculum_audit.add_argument("--json", action="store_true")

    lesson = sub.add_parser("lesson", help="Lesson workflow")
    lesson_sub = lesson.add_subparsers(dest="lesson_command", required=True)
    lesson_next = lesson_sub.add_parser("next")
    lesson_next.add_argument("--json", action="store_true")
    lesson_show = lesson_sub.add_parser("show")
    lesson_show.add_argument("lesson_id")
    lesson_show.add_argument("--json", action="store_true")
    lesson_complete = lesson_sub.add_parser("complete")
    lesson_complete.add_argument("lesson_id")
    lesson_complete.add_argument("--score", type=float, default=1.0)
    lesson_complete.add_argument("--id", default="")
    lesson_complete.add_argument("--json", action="store_true")

    quiz = sub.add_parser("quiz", help="Quiz workflow")
    quiz_sub = quiz.add_subparsers(dest="quiz_command", required=True)
    quiz_start = quiz_sub.add_parser("start")
    quiz_start.add_argument("objective_id")
    quiz_start.add_argument("--json", action="store_true")
    quiz_submit = quiz_sub.add_parser("submit")
    quiz_submit.add_argument("objective_id")
    quiz_submit.add_argument("score", type=float)
    quiz_submit.add_argument("--id", default="")
    quiz_submit.add_argument("--json", action="store_true")
    quiz_review = quiz_sub.add_parser("review")
    quiz_review.add_argument("--json", action="store_true")

    lab = sub.add_parser("lab", help="Lab workflow")
    lab_sub = lab.add_subparsers(dest="lab_command", required=True)
    lab_list = lab_sub.add_parser("list")
    lab_list.add_argument("--json", action="store_true")
    lab_run = lab_sub.add_parser("run")
    lab_run.add_argument("lab_id")
    lab_run.add_argument("--offline", action="store_true")
    lab_run.add_argument("--live", action="store_true")
    lab_run.add_argument("--id", default="")
    lab_run.add_argument("--json", action="store_true")
    lab_teardown = lab_sub.add_parser("teardown")
    lab_teardown.add_argument("lab_id")
    lab_teardown.add_argument("--json", action="store_true")

    tutor = sub.add_parser("tutor", help="Offline tutor response")
    tutor.add_argument("lesson_id")
    tutor.add_argument("--learner-attempt", default="I am ready for retrieval practice.")
    tutor.add_argument("--zpd-level", type=int, default=2)
    tutor.add_argument("--json", action="store_true")

    review = sub.add_parser("review", help="Review workflow")
    review_sub = review.add_subparsers(dest="review_command", required=True)
    review_due = review_sub.add_parser("due")
    review_due.add_argument("--json", action="store_true")

    session = sub.add_parser("session", help="Study session workflow")
    session_sub = session.add_subparsers(dest="session_command", required=True)
    session_start = session_sub.add_parser("start")
    session_start.add_argument("--id", default="")
    session_start.add_argument("--json", action="store_true")
    session_resume = session_sub.add_parser("resume")
    session_resume.add_argument("--json", action="store_true")
    session_finish = session_sub.add_parser("finish")
    session_finish.add_argument("--json", action="store_true")

    migrate = sub.add_parser("migrate", help="Migrate legacy state to AI-103 schemas")
    migrate.add_argument("--dry-run", action="store_true", default=True)
    migrate.add_argument("--apply", action="store_false", dest="dry_run")
    migrate.add_argument("--json", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    {
        "status": cmd_status,
        "log": cmd_log,
        "run": cmd_run,
        "init": cmd_init,
        "doctor": cmd_doctor,
        "curriculum": cmd_curriculum,
        "lesson": cmd_lesson,
        "quiz": cmd_quiz,
        "lab": cmd_lab,
        "tutor": cmd_tutor,
        "review": cmd_review,
        "session": cmd_session,
        "migrate": cmd_migrate,
    }[args.command](args)


if __name__ == "__main__":
    main()
