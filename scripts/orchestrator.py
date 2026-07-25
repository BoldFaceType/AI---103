from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from merge_utils import merge_progress
from state_utils import ROOT, append_audit, append_ndjson, load_json, load_ndjson, relative_key, save_json, update_vmeta, utc_now
from validators import (
    validate_event,
    validate_knowledge_map,
    validate_learning_policy,
    validate_objectives,
    validate_path,
    validate_profile,
    validate_task,
)

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.learning.events import (
    corrupt_event_record,
    evidence_signal,
    is_audit_only_event,
    is_deterministic_evidence_event,
    is_known_event,
)


DEFAULT_REMEDIATION_THRESHOLD = 0.8
AI103_SCHEMA_VERSION = 2
AI103_DOMAINS = ("PM", "GA", "CV", "TA", "IE")
LEGACY_CONCEPT_MAPPING = {
    "vision-services": ["CV"],
    "language-services": ["TA", "IE"],
    "search-services": ["GA", "IE"],
    "responsible-ai": ["PM"],
}
AI103_OBJECTIVES = {
    "PM": {"weight": 0.275, "competency_ids": [f"PM-{index:02d}" for index in range(1, 17)]},
    "GA": {"weight": 0.325, "competency_ids": [f"GA-{index:02d}" for index in range(1, 17)]},
    "CV": {"weight": 0.133, "competency_ids": [f"CV-{index:02d}" for index in range(1, 17)]},
    "TA": {"weight": 0.133, "competency_ids": [f"TA-{index:02d}" for index in range(1, 9)]},
    "IE": {"weight": 0.134, "competency_ids": [f"IE-{index:02d}" for index in range(1, 9)]},
}


class StateRepository:
    def __init__(self, root: Path):
        self.root = root

    def load_profile(self) -> dict[str, Any]:
        return load_json(self.root / "config" / "profile.user.json")

    def load_objectives(self) -> dict[str, Any]:
        return load_json(self.root / "config" / "objectives.ai103.json")

    def load_learning_policy(self) -> dict[str, Any]:
        return load_json(self.root / "config" / "learning-policy.json", {"remediation_threshold": DEFAULT_REMEDIATION_THRESHOLD})

    def load_knowledge_map(self) -> dict[str, Any]:
        return load_json(self.root / "state" / "learner" / "knowledge-map.json")

    def save_knowledge_map(self, knowledge: dict[str, Any], actor: str) -> None:
        path = self.root / "state" / "learner" / "knowledge-map.json"
        save_json(path, knowledge)
        update_vmeta(path, actor, self.root)

    def load_habits(self) -> dict[str, Any]:
        return load_json(self.root / "state" / "learner" / "habits.json")

    def save_habits(self, habits: dict[str, Any], actor: str) -> None:
        path = self.root / "state" / "learner" / "habits.json"
        save_json(path, habits)
        update_vmeta(path, actor, self.root)

    def load_progress(self) -> dict[str, Any]:
        return load_json(self.root / "state" / "learner" / "progress.json")

    def save_progress(self, progress: dict[str, Any], actor: str) -> None:
        path = self.root / "state" / "learner" / "progress.json"
        save_json(path, progress)
        update_vmeta(path, actor, self.root)

    def load_meta(self) -> dict[str, Any]:
        return load_json(self.root / "state" / "learner" / "meta.json")

    def save_meta(self, meta: dict[str, Any], actor: str) -> None:
        path = self.root / "state" / "learner" / "meta.json"
        save_json(path, meta)
        update_vmeta(path, actor, self.root)

    def list_todo_tasks(self) -> list[Path]:
        todo_dir = self.root / "state" / "tasks" / "todo"
        if not todo_dir.exists():
            return []
        return sorted(todo_dir.glob("*.json"))

    def load_task(self, path: Path) -> dict[str, Any]:
        return load_json(path)

    def write_task(self, task: dict[str, Any], actor: str) -> None:
        path = self.root / "state" / "tasks" / "todo" / f"{task['id']}.json"
        save_json(path, task)
        update_vmeta(path, actor, self.root)

    def load_events(self) -> list[dict[str, Any]]:
        return load_ndjson(self.root / "logs" / "events.ndjson")

    def load_event_records(self) -> list[dict[str, Any]]:
        path = self.root / "logs" / "events.ndjson"
        if not path.exists():
            return []
        records: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                records.append({"event": json.loads(line), "corrupt": None})
            except json.JSONDecodeError as exc:
                records.append({"event": None, "corrupt": corrupt_event_record(line_number, raw_line, str(exc))})
        return records

    def quarantine_event(self, record: dict[str, Any]) -> None:
        path = self.root / "_meta" / "quarantine" / "events.ndjson"
        append_ndjson(path, [record])
        update_vmeta(path, "orchestrator", self.root)

    def append_event(self, event: dict[str, Any]) -> None:
        path = self.root / "logs" / "events.ndjson"
        append_ndjson(path, [event])
        update_vmeta(path, "orchestrator", self.root)

    def write_session_snapshot(self, snapshot: dict[str, Any], actor: str) -> None:
        safe_ts = snapshot["timestamp"].replace(":", "-")
        path = self.root / "state" / "sessions" / f"{safe_ts}.json"
        save_json(path, snapshot)
        update_vmeta(path, actor, self.root)


def require_valid(label: str, errors: list[str]) -> None:
    if errors:
        joined = "; ".join(errors)
        raise ValueError(f"{label} validation failed: {joined}")


def baseline_objectives() -> dict[str, Any]:
    return {
        "schema_version": AI103_SCHEMA_VERSION,
        "exam": "AI-103",
        "source_curriculum": "config/curriculum.ai103.json",
        "objectives": AI103_OBJECTIVES,
        "legacy_objective_mapping": {
            key: {"mapped_to": value, "preservation": "legacy evidence retained; mastery is not increased"}
            for key, value in LEGACY_CONCEPT_MAPPING.items()
        },
    }


def baseline_knowledge_map() -> dict[str, Any]:
    return {
        "schema_version": AI103_SCHEMA_VERSION,
        "exam": "AI-103",
        "domains": {
            domain_id: {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []}
            for domain_id in AI103_DOMAINS
        },
        "legacy_evidence": {
            "source_schema_version": 1,
            "concepts": {},
            "mapping": LEGACY_CONCEPT_MAPPING,
        },
    }


def objective_entries(objectives: dict[str, Any]) -> dict[str, Any]:
    if isinstance(objectives.get("objectives"), dict):
        return objectives["objectives"]
    return objectives


def knowledge_entries(knowledge: dict[str, Any]) -> dict[str, Any]:
    if isinstance(knowledge.get("domains"), dict):
        return knowledge["domains"]
    return knowledge


def event_concepts_for_knowledge(knowledge: dict[str, Any], concept: str) -> list[str]:
    if isinstance(knowledge.get("domains"), dict):
        return LEGACY_CONCEPT_MAPPING.get(concept, [concept])
    return [concept]


def update_metric(
    current: dict[str, Any],
    score: float,
    event_id: str,
    remediation_threshold: float,
) -> dict[str, Any]:
    mastery = float(current.get("mastery", 0.0))
    confidence = float(current.get("confidence", 0.0))
    if score >= remediation_threshold:
        mastery = min(1.0, mastery + 0.1)
        confidence = min(1.0, confidence + 0.1)
    else:
        mastery = max(0.0, mastery - 0.05)
        confidence = max(0.0, confidence - 0.05)
    updated = dict(current)
    updated["mastery"] = round(mastery, 3)
    updated["confidence"] = round(confidence, 3)
    if "evidence_refs" in current:
        updated["evidence_refs"] = sorted(set(current.get("evidence_refs", []) + [event_id]))
    return updated


def bootstrap_files(repo: StateRepository) -> list[Path]:
    files: dict[Path, Any] = {
        repo.root / "config" / "profile.user.json": {
            "name": "Jeremie",
            "primary_goal": "Pass AI-103",
            "preferences": {
                "style": "structured-visual-actionable",
                "default_session_minutes": 45,
            },
        },
        repo.root / "config" / "objectives.ai103.json": baseline_objectives(),
        repo.root / "config" / "learning-policy.json": {
            "remediation_threshold": DEFAULT_REMEDIATION_THRESHOLD,
        },
        repo.root / "state" / "learner" / "knowledge-map.json": baseline_knowledge_map(),
        repo.root / "state" / "learner" / "habits.json": {
            "quiz_count": 0,
            "last_quiz_ts": None,
        },
        repo.root / "state" / "learner" / "progress.json": {
            "percentComplete": 0.0,
            "events": [],
        },
        repo.root / "state" / "learner" / "meta.json": {
            "processed_event_ids": [],
            "last_processed_ts": None,
        },
        repo.root / "content" / "notes" / "ai103" / "README.md": "# AI-103 Notes\n\nAdd lesson notes here.\n",
        repo.root / "content" / "prompts" / "tutor" / "system.md": "# Tutor Prompt\n\nDescribe tutoring instructions here.\n",
    }
    created: list[Path] = []
    for path, data in files.items():
        if path.exists():
            continue
        if isinstance(data, str):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data, encoding="utf-8")
        else:
            save_json(path, data)
        update_vmeta(path, "init")
        created.append(path)

    events_path = repo.root / "logs" / "events.ndjson"
    if not events_path.exists():
        append_ndjson(
            events_path,
            [
                {
                    "schema_version": AI103_SCHEMA_VERSION,
                    "ts": utc_now(),
                    "type": "quiz_completed",
                    "event_id": "seed-quiz-001",
                    "score": 0.55,
                    "concepts": ["vision-services"],
                }
            ],
        )
        update_vmeta(events_path, "init")
        created.append(events_path)

    for folder in (
        repo.root / "state" / "tasks" / "todo",
        repo.root / "state" / "tasks" / "in-progress",
        repo.root / "state" / "tasks" / "done",
        repo.root / "state" / "assessments" / "raw",
        repo.root / "state" / "assessments" / "derived",
        repo.root / "exports",
        repo.root / "_meta",
    ):
        folder.mkdir(parents=True, exist_ok=True)
    return created


def apply_quiz_event(
    knowledge: dict[str, Any],
    habits: dict[str, Any],
    event: dict[str, Any],
    remediation_threshold: float = DEFAULT_REMEDIATION_THRESHOLD,
) -> dict[str, Any]:
    score = float(event.get("score", 0.0))
    for concept in event.get("concepts", []):
        for target in event_concepts_for_knowledge(knowledge, concept):
            entries = knowledge_entries(knowledge)
            current = entries.get(target, {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []})
            entries[target] = update_metric(current, score, event.get("event_id", ""), remediation_threshold)
    habits["quiz_count"] = int(habits.get("quiz_count", 0)) + 1
    habits["last_quiz_ts"] = event.get("ts")
    return knowledge


def apply_learning_event(
    knowledge: dict[str, Any],
    habits: dict[str, Any],
    event: dict[str, Any],
    remediation_threshold: float = DEFAULT_REMEDIATION_THRESHOLD,
) -> dict[str, Any]:
    if event.get("type") == "quiz_completed" and "concepts" in event:
        return apply_quiz_event(knowledge, habits, event, remediation_threshold)

    signal = evidence_signal(event)
    for objective_id in signal.objective_ids:
        entries = knowledge_entries(knowledge)
        domain_id = objective_id.split("-", 1)[0] if "-" in objective_id else objective_id
        if domain_id not in entries:
            continue
        entries[domain_id] = update_metric(entries[domain_id], signal.score, signal.event_id, remediation_threshold)
        if "-" in objective_id:
            competencies = dict(entries[domain_id].get("competencies", {}))
            current = competencies.get(objective_id, {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []})
            competencies[objective_id] = update_metric(current, signal.score, signal.event_id, remediation_threshold)
            entries[domain_id]["competencies"] = competencies
    if event.get("type") == "quiz_completed":
        habits["quiz_count"] = int(habits.get("quiz_count", 0)) + 1
        habits["last_quiz_ts"] = event.get("ts")
    else:
        habits["evidence_event_count"] = int(habits.get("evidence_event_count", 0)) + 1
    return knowledge


def process_events(
    repo: StateRepository,
    knowledge: dict[str, Any],
    habits: dict[str, Any],
    progress: dict[str, Any],
    meta: dict[str, Any],
    remediation_threshold: float = DEFAULT_REMEDIATION_THRESHOLD,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    processed_event_ids = set(meta.get("processed_event_ids", []))
    incoming_events: list[dict[str, Any]] = []
    for record in repo.load_event_records():
        if record.get("corrupt"):
            repo.quarantine_event(record["corrupt"])
            append_audit("quarantine_event", "logs/events.ndjson", "orchestrator", "failed", record["corrupt"])
            continue
        event = record["event"]
        errors = validate_event(event)
        if errors:
            repo.quarantine_event({"schema_version": AI103_SCHEMA_VERSION, "event": event, "errors": errors})
            append_audit("validate_event", "logs/events.ndjson", "orchestrator", "failed", {"errors": errors, "event": event})
            continue
        if event["event_id"] in processed_event_ids:
            continue
        if not is_known_event(event):
            append_audit("skip_unknown_event", "logs/events.ndjson", "orchestrator", "skipped", {"event": event})
            processed_event_ids.add(event["event_id"])
            continue
        if is_audit_only_event(event):
            append_audit("audit_only_event", "logs/events.ndjson", "orchestrator", "ok", {"event": event})
            processed_event_ids.add(event["event_id"])
            continue
        if not is_deterministic_evidence_event(event):
            continue
        knowledge = apply_learning_event(knowledge, habits, event, remediation_threshold)
        incoming_events.append(event)
        processed_event_ids.add(event["event_id"])
        meta["last_processed_ts"] = event.get("ts")

    if incoming_events or sorted(processed_event_ids) != sorted(meta.get("processed_event_ids", [])):
        progress = merge_progress(progress, incoming_events)
        meta["processed_event_ids"] = sorted(processed_event_ids)
    return knowledge, habits, progress, meta


def build_task(concept: str, objective_weight: float) -> dict[str, Any]:
    timestamp = utc_now()
    slug = concept.replace(" ", "-")
    return {
        "schema_version": AI103_SCHEMA_VERSION,
        "id": f"task-{slug}-{timestamp.replace(':', '').replace('-', '')}",
        "type": "quiz",
        "objective_ids": [concept],
        "estimated_minutes": 10 if objective_weight < 0.3 else 15,
        "created_at": timestamp,
        "source": "orchestrator",
        "status": "open",
    }


def generate_tasks(
    repo: StateRepository,
    knowledge: dict[str, Any],
    objectives: dict[str, Any],
    max_new_tasks: int = 3,
    remediation_threshold: float = DEFAULT_REMEDIATION_THRESHOLD,
) -> list[dict[str, Any]]:
    existing = [repo.load_task(path) for path in repo.list_todo_tasks()]
    if isinstance(knowledge.get("domains"), dict) and isinstance(objectives.get("objectives"), dict):
        available_slots = max(0, max_new_tasks - len(existing))
        if available_slots == 0:
            return []
        from ai103.learning.planner import plan_tasks

        return plan_tasks(
            knowledge_entries(knowledge),
            objective_entries(objectives),
            existing,
            today=datetime.now(UTC).date(),
            seed=0,
            max_tasks=available_slots,
            remediation_threshold=remediation_threshold,
        )

    tracked_objectives = {objective for task in existing for objective in task.get("objective_ids", [])}
    available_slots = max(0, max_new_tasks - len(existing))
    candidates = []
    objective_map = objective_entries(objectives)
    for concept, metrics in knowledge_entries(knowledge).items():
        if metrics.get("mastery", 0.0) >= remediation_threshold:
            continue
        if concept in tracked_objectives:
            continue
        candidates.append((concept, objective_map.get(concept, {}).get("weight", 0.0)))
    candidates.sort(key=lambda item: item[1], reverse=True)
    return [build_task(concept, weight) for concept, weight in candidates[:available_slots]]


def write_tasks(repo: StateRepository, tasks: list[dict[str, Any]]) -> None:
    for task in tasks:
        require_valid("task", validate_task(task))
        repo.write_task(task, "orchestrator")
        append_audit("write_task", relative_key(repo.root / "state" / "tasks" / "todo" / f"{task['id']}.json", repo.root), "orchestrator", "ok", {"task_id": task["id"]})


def build_snapshot(knowledge: dict[str, Any], habits: dict[str, Any], repo: StateRepository) -> dict[str, Any]:
    return {
        "schema_version": AI103_SCHEMA_VERSION,
        "timestamp": utc_now(),
        "knowledge": knowledge,
        "habits": habits,
        "tasks": {
            "todo": len(repo.list_todo_tasks()),
        },
    }


def run_once() -> None:
    repo = StateRepository(ROOT)
    profile = repo.load_profile()
    objectives = repo.load_objectives()
    learning_policy = repo.load_learning_policy()
    knowledge = repo.load_knowledge_map()
    habits = repo.load_habits()
    progress = repo.load_progress()
    meta = repo.load_meta()

    require_valid("profile", validate_profile(profile))
    require_valid("objectives", validate_objectives(objectives))
    require_valid("learning-policy", validate_learning_policy(learning_policy))
    require_valid("knowledge-map", validate_knowledge_map(knowledge))
    remediation_threshold = float(learning_policy["remediation_threshold"])

    knowledge, habits, progress, meta = process_events(repo, knowledge, habits, progress, meta, remediation_threshold)

    repo.save_knowledge_map(knowledge, "orchestrator")
    repo.save_habits(habits, "orchestrator")
    repo.save_progress(progress, "orchestrator")
    repo.save_meta(meta, "orchestrator")
    append_audit("persist_state", "state/learner", "orchestrator", "ok", {"processed_events": len(meta.get("processed_event_ids", []))})

    tasks = generate_tasks(repo, knowledge, objectives, remediation_threshold=remediation_threshold)
    write_tasks(repo, tasks)

    snapshot = build_snapshot(knowledge, habits, repo)
    repo.write_session_snapshot(snapshot, "orchestrator")
    append_audit("write_snapshot", relative_key(repo.root / "state" / "sessions", repo.root), "orchestrator", "ok", {"timestamp": snapshot["timestamp"]})

    repo.append_event(
        {
            "schema_version": AI103_SCHEMA_VERSION,
            "ts": utc_now(),
            "type": "decision_made",
            "event_id": f"decision-{snapshot['timestamp']}",
            "tasks_created": len(tasks),
        }
    )


def initialize() -> None:
    repo = StateRepository(ROOT)
    created = bootstrap_files(repo)
    for path in created:
        if path.suffix == ".json":
            errors = validate_path(path, load_json(path))
            require_valid(relative_key(path, repo.root), errors)
    append_audit("init", ".", "orchestrator", "ok", {"created": [relative_key(path, repo.root) for path in created]})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adaptive Learning Orchestrator")
    parser.add_argument("--init", action="store_true", help="Create baseline folders and sample files")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.init:
        initialize()
        return
    run_once()


if __name__ == "__main__":
    main()
