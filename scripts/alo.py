"""ALO CLI — Adaptive Learning Orchestrator interface."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))

CONCEPTS = ["vision-services", "language-services", "search-services", "responsible-ai"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def cmd_status(_args: argparse.Namespace) -> None:
    km = load_json(ROOT / "state/learner/knowledge-map.json")
    habits = load_json(ROOT / "state/learner/habits.json")
    meta = load_json(ROOT / "state/learner/meta.json")
    tasks = sorted((ROOT / "state/tasks/todo").glob("*.json")) if (ROOT / "state/tasks/todo").exists() else []

    print("\n=== Knowledge Map ===")
    for concept in CONCEPTS:
        v = km.get(concept, {"mastery": 0.0, "confidence": 0.0})
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
        "ts": utc_now(),
        "type": "quiz_completed",
        "event_id": event_id,
        "score": score,
        "concepts": [args.concept],
    }

    log_path = ROOT / "logs/events.ndjson"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    log_path.write_text(existing + json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")

    print(f"Logged:  {args.concept}  score={score:.0%}  id={event_id}")
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alo",
        description="Adaptive Learning Orchestrator CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show knowledge map, tasks, and session stats")
    sub.add_parser("run", help="Process events and update learner state")
    sub.add_parser("init", help="Create baseline folders and sample files")

    log = sub.add_parser("log", help="Record a quiz result")
    log.add_argument("concept", choices=CONCEPTS, help="Concept area tested")
    log.add_argument("score", type=float, help="Score as decimal, e.g. 0.72")
    log.add_argument("--id", default="", help="Optional event ID (auto-generated if omitted)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    {"status": cmd_status, "log": cmd_log, "run": cmd_run, "init": cmd_init}[args.command](args)


if __name__ == "__main__":
    main()
