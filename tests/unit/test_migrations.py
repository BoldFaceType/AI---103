from __future__ import annotations

import importlib.util
from pathlib import Path

from state_utils import load_json, save_json


ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = ROOT / "scripts" / "migrations" / "001_ai103_domains.py"
SPEC = importlib.util.spec_from_file_location("migration_001_ai103_domains", MIGRATION_PATH)
migration = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(migration)


def test_migration_maps_legacy_state_without_increasing_mastery():
    legacy = {
        "vision-services": {"mastery": 0.6, "confidence": 0.5},
        "language-services": {"mastery": 0.7, "confidence": 0.7},
        "search-services": {"mastery": 0.4, "confidence": 0.3},
        "responsible-ai": {"mastery": 0.8, "confidence": 0.6},
    }

    migrated, errors = migration.migrate_knowledge_map(legacy, captured_at="2026-07-25T00:00:00Z")

    assert errors == []
    assert migrated["schema_version"] == 2
    assert migrated["domains"]["CV"]["mastery"] == 0.6
    assert migrated["domains"]["PM"]["mastery"] == 0.8
    assert migrated["domains"]["IE"]["mastery"] == 0.4
    assert migrated["legacy_evidence"]["concepts"] == legacy


def test_migration_is_idempotent_for_v2_state():
    v2 = {
        "schema_version": 2,
        "exam": "AI-103",
        "domains": {
            "PM": {"mastery": 0.1, "confidence": 0.2, "evidence_refs": []},
            "GA": {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []},
            "CV": {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []},
            "TA": {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []},
            "IE": {"mastery": 0.0, "confidence": 0.0, "evidence_refs": []},
        },
    }

    migrated, errors = migration.migrate_knowledge_map(v2)

    assert migrated is v2
    assert errors == []


def test_migration_blocks_unknown_legacy_keys():
    migrated, errors = migration.migrate_knowledge_map({"mystery": {"mastery": 0.1, "confidence": 0.1}})

    assert migrated["mystery"]["mastery"] == 0.1
    assert errors == ["unknown legacy knowledge key: mystery"]


def test_write_migration_creates_recoverable_backups(tmp_path):
    save_json(tmp_path / "config" / "objectives.ai103.json", {"vision-services": {"weight": 0.25}})
    save_json(tmp_path / "state" / "learner" / "knowledge-map.json", {"vision-services": {"mastery": 0.2, "confidence": 0.3}})

    objectives, knowledge, errors = migration.migration_plan(tmp_path)
    backup_paths = migration.write_migration(tmp_path, objectives, knowledge)

    assert errors == []
    assert all(path.exists() for path in backup_paths)
    assert load_json(tmp_path / "config" / "objectives.ai103.json")["schema_version"] == 2
    assert load_json(tmp_path / "state" / "learner" / "knowledge-map.json")["schema_version"] == 2
    assert load_json(backup_paths[1])["vision-services"]["mastery"] == 0.2
