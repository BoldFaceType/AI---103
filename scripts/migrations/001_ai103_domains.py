from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parents[1]
ROOT = SCRIPT_DIR.parents[0]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from orchestrator import AI103_DOMAINS, AI103_SCHEMA_VERSION, LEGACY_CONCEPT_MAPPING, baseline_objectives
from state_utils import load_json, save_json, utc_now
from validators import validate_knowledge_map, validate_objectives


def _safe_timestamp() -> str:
    return utc_now().replace(":", "").replace("-", "")


def _legacy_keys(knowledge: dict[str, Any]) -> list[str]:
    return [key for key, value in knowledge.items() if isinstance(value, dict)]


def migrate_knowledge_map(legacy: dict[str, Any], captured_at: str | None = None) -> tuple[dict[str, Any], list[str]]:
    if legacy.get("schema_version") == AI103_SCHEMA_VERSION and isinstance(legacy.get("domains"), dict):
        return legacy, []

    unknown = sorted(set(_legacy_keys(legacy)) - set(LEGACY_CONCEPT_MAPPING))
    if unknown:
        return legacy, [f"unknown legacy knowledge key: {key}" for key in unknown]

    captured_at = captured_at or utc_now()
    domain_sources: dict[str, list[tuple[str, dict[str, Any]]]] = {domain_id: [] for domain_id in AI103_DOMAINS}
    for concept, targets in LEGACY_CONCEPT_MAPPING.items():
        metrics = legacy.get(concept, {"mastery": 0.0, "confidence": 0.0})
        if not isinstance(metrics, dict):
            return legacy, [f"legacy knowledge key '{concept}' must map to an object"]
        for target in targets:
            domain_sources[target].append((concept, metrics))

    domains: dict[str, dict[str, Any]] = {}
    for domain_id, sources in domain_sources.items():
        if sources:
            mastery = min(float(metrics.get("mastery", 0.0)) for _, metrics in sources)
            confidence = min(float(metrics.get("confidence", 0.0)) for _, metrics in sources)
            evidence_refs = [f"legacy:{concept}" for concept, _ in sources if concept in legacy]
        else:
            mastery = 0.0
            confidence = 0.0
            evidence_refs = []
        domains[domain_id] = {
            "mastery": round(mastery, 3),
            "confidence": round(confidence, 3),
            "evidence_refs": sorted(evidence_refs),
        }

    migrated = {
        "schema_version": AI103_SCHEMA_VERSION,
        "exam": "AI-103",
        "domains": domains,
        "legacy_evidence": {
            "captured_at": captured_at,
            "source_schema_version": 1,
            "concepts": legacy,
            "mapping": LEGACY_CONCEPT_MAPPING,
            "rule": "Domain mastery/confidence uses the minimum mapped legacy value; unmapped domains start at 0.",
        },
    }
    return migrated, validate_knowledge_map(migrated)


def migration_plan(root: Path) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    objectives = load_json(root / "config" / "objectives.ai103.json")
    knowledge = load_json(root / "state" / "learner" / "knowledge-map.json")

    migrated_objectives = objectives
    if objectives.get("schema_version") != AI103_SCHEMA_VERSION:
        migrated_objectives = baseline_objectives()

    migrated_knowledge, knowledge_errors = migrate_knowledge_map(knowledge)
    errors = validate_objectives(migrated_objectives) + knowledge_errors
    return migrated_objectives, migrated_knowledge, errors


def write_migration(root: Path, objectives: dict[str, Any], knowledge: dict[str, Any]) -> list[Path]:
    stamp = _safe_timestamp()
    backups = root / "state" / "learner" / "backups"
    current_objectives = load_json(root / "config" / "objectives.ai103.json")
    current_knowledge = load_json(root / "state" / "learner" / "knowledge-map.json")

    backup_paths = [
        backups / f"objectives.ai103.{stamp}.json",
        backups / f"knowledge-map.{stamp}.json",
    ]
    save_json(backup_paths[0], current_objectives)
    save_json(backup_paths[1], current_knowledge)
    save_json(root / "config" / "objectives.ai103.json", objectives)
    save_json(root / "state" / "learner" / "knowledge-map.json", knowledge)
    return backup_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate legacy learner state to AI-103 domain schemas.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report without writing files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    objectives, knowledge, errors = migration_plan(root)
    if errors:
        print("Migration blocked:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("DRY RUN: AI-103 schema migration is valid.")
        print(f"Objectives schema: {objectives.get('schema_version')}")
        print(f"Knowledge schema: {knowledge.get('schema_version')}")
        print("Writes: none")
        return 0

    backup_paths = write_migration(root, objectives, knowledge)
    print("AI-103 schema migration complete.")
    for path in backup_paths:
        print(f"Backup: {path.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
