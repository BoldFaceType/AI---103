from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from curriculum_audit import audit


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_curriculum_has_expected_official_snapshot():
    curriculum = load_json(ROOT / "config" / "curriculum.ai103.json")
    source_registry = load_json(ROOT / "content" / "sources" / "ai103-source-registry.json")

    assert curriculum["exam"] == "AI-103"
    assert curriculum["skills_measured_date"] == "2026-04-16"
    assert source_registry["primary_source"]["last_updated_on"] == "2026-04-14"
    assert source_registry["primary_source"]["url"].endswith("/study-guides/ai-103")
    assert len(curriculum["competencies"]) == 64


def test_domain_weights_ranges_and_counts_are_locked():
    curriculum = load_json(ROOT / "config" / "curriculum.ai103.json")
    domains = curriculum["domains"]

    assert round(sum(domain["scheduler_weight"] for domain in domains), 3) == 1.0
    assert {domain["id"]: domain["official_range"] for domain in domains} == {
        "PM": "25-30%",
        "GA": "30-35%",
        "CV": "10-15%",
        "TA": "10-15%",
        "IE": "10-15%",
    }

    counts = Counter(item["domain"] for item in curriculum["competencies"])
    assert counts == {"PM": 16, "GA": 16, "CV": 16, "TA": 8, "IE": 8}


def test_competency_ids_are_stable_unique_and_paraphrased():
    curriculum = load_json(ROOT / "config" / "curriculum.ai103.json")
    ids = [item["id"] for item in curriculum["competencies"]]

    assert len(ids) == len(set(ids))
    assert ids[0] == "PM-01"
    assert ids[-1] == "IE-08"
    assert all(item["summary"] for item in curriculum["competencies"])


def test_audit_passes_and_reports_future_gaps():
    errors, report = audit(today=date(2026, 7, 25))

    assert errors == []
    joined = "\n".join(report)
    assert "Competencies: 64" in joined
    assert "Lesson files: pending T10-T15" in joined
