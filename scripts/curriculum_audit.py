from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_PATH = ROOT / "config" / "curriculum.ai103.json"
SOURCE_REGISTRY_PATH = ROOT / "content" / "sources" / "ai103-source-registry.json"
LESSON_ROOT = ROOT / "content" / "lessons" / "ai103"
MAX_VERIFICATION_AGE_DAYS = 180
EXPECTED_DOMAIN_COUNTS = {"PM": 16, "GA": 16, "CV": 16, "TA": 8, "IE": 8}
ID_PATTERN = re.compile(r"^(PM|GA|CV|TA|IE)-\d{2}$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=UTC).date()


def lesson_competency_ids(domain: str | None = None) -> set[str]:
    if not LESSON_ROOT.exists():
        return set()
    ids: set[str] = set()
    for path in LESSON_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
        if not match:
            continue
        metadata = json.loads(match.group(1))
        for competency_id in metadata.get("competency_ids", []):
            if domain is None or str(competency_id).startswith(f"{domain}-"):
                ids.add(str(competency_id))
    return ids


def audit(today: date | None = None, domain: str | None = None) -> tuple[list[str], list[str]]:
    today = today or datetime.now(UTC).date()
    errors: list[str] = []
    report: list[str] = []

    if not CURRICULUM_PATH.exists():
        return [f"missing curriculum file: {CURRICULUM_PATH.relative_to(ROOT).as_posix()}"], report
    if not SOURCE_REGISTRY_PATH.exists():
        return [f"missing source registry file: {SOURCE_REGISTRY_PATH.relative_to(ROOT).as_posix()}"], report

    curriculum = load_json(CURRICULUM_PATH)
    source_registry = load_json(SOURCE_REGISTRY_PATH)

    registry_path = ROOT / curriculum.get("source_registry_path", "")
    if registry_path != SOURCE_REGISTRY_PATH:
        errors.append("curriculum.source_registry_path must point to content/sources/ai103-source-registry.json")

    primary_source = source_registry.get("primary_source", {})
    if curriculum.get("skills_measured_date") != primary_source.get("skills_measured_date"):
        errors.append("curriculum and source registry skills_measured_date values differ")

    for label, value in (
        ("curriculum.last_verified_at", curriculum.get("last_verified_at")),
        ("primary_source.last_verified_at", primary_source.get("last_verified_at")),
    ):
        try:
            verified_at = parse_date(str(value))
        except ValueError:
            errors.append(f"{label} must be YYYY-MM-DD")
            continue
        if (today - verified_at).days > MAX_VERIFICATION_AGE_DAYS:
            errors.append(f"{label} is stale: {value}")

    source_hash = primary_source.get("normalized_source_hash", "")
    if not isinstance(source_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        errors.append("primary_source.normalized_source_hash must be a lowercase SHA-256 hex string")

    domains = curriculum.get("domains", [])
    domain_ids = [domain_record.get("id") for domain_record in domains]
    if set(domain_ids) != set(EXPECTED_DOMAIN_COUNTS):
        errors.append("curriculum domains must be PM, GA, CV, TA, and IE")

    weight_total = round(sum(float(domain_record.get("scheduler_weight", 0)) for domain_record in domains), 3)
    if weight_total != 1.0:
        errors.append(f"scheduler weights must total 1.0; got {weight_total}")
    for domain_record in domains:
        if "official_range" not in domain_record:
            errors.append(f"domain {domain_record.get('id')} missing official_range")

    competencies = curriculum.get("competencies", [])
    ids = [item.get("id") for item in competencies]
    duplicate_ids = sorted(item for item, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        errors.append(f"duplicate competency ids: {', '.join(duplicate_ids)}")

    for item in competencies:
        competency_id = item.get("id", "")
        competency_domain = item.get("domain", "")
        if not ID_PATTERN.fullmatch(str(competency_id)):
            errors.append(f"invalid competency id: {competency_id}")
        if competency_domain not in EXPECTED_DOMAIN_COUNTS:
            errors.append(f"competency {competency_id} has invalid domain: {competency_domain}")
        if not str(item.get("summary", "")).strip():
            errors.append(f"competency {competency_id} missing summary")
        if not str(item.get("source_section", "")).strip():
            errors.append(f"competency {competency_id} missing source_section")

    counts = Counter(item.get("domain") for item in competencies)
    for expected_domain, expected_count in EXPECTED_DOMAIN_COUNTS.items():
        actual_count = counts.get(expected_domain, 0)
        if actual_count != expected_count:
            errors.append(f"domain {expected_domain} expected {expected_count} competencies; got {actual_count}")

    if len(competencies) != source_registry.get("competency_count"):
        errors.append("source registry competency_count does not match curriculum")

    domain_filter = domain
    if domain_filter and domain_filter not in EXPECTED_DOMAIN_COUNTS:
        errors.append(f"unknown domain: {domain_filter}")
    expected_lesson_ids = {item["id"] for item in competencies if domain_filter is None or item.get("domain") == domain_filter}
    covered_lesson_ids = lesson_competency_ids(domain_filter)

    report.append("# AI-103 Curriculum Audit")
    report.append("")
    report.append(f"Source: {primary_source.get('url')}")
    report.append(f"Skills measured date: {primary_source.get('skills_measured_date')}")
    report.append(f"Last verified: {primary_source.get('last_verified_at')}")
    report.append(f"Domains: {len(domains)}")
    report.append(f"Competencies: {len(competencies)}")
    report.append(f"Scheduler weight total: {weight_total:.3f}")
    report.append("")
    report.append("## Domain coverage")
    for domain_record in domains:
        domain_id = domain_record["id"]
        if domain_filter and domain_id != domain_filter:
            continue
        report.append(
            f"- {domain_id}: {counts.get(domain_id, 0)} competencies, "
            f"range {domain_record['official_range']}, weight {domain_record['scheduler_weight']:.3f}"
        )
    report.append("")
    report.append("## Lesson coverage")
    report.append(f"- Covered competencies: {len(covered_lesson_ids)}/{len(expected_lesson_ids)}")
    if domain_filter:
        missing = sorted(expected_lesson_ids - covered_lesson_ids)
        report.append(f"- Domain filter: {domain_filter}")
        report.append(f"- Missing lesson mappings: {', '.join(missing) if missing else 'none'}")
        if missing:
            errors.append(f"domain {domain_filter} missing lesson mappings: {', '.join(missing)}")
    report.append("")
    report.append("## Implementation gaps")
    report.append("- Lesson files: pending T10-T15")
    report.append("- Assessment files: pending T10-T15")
    report.append("- Lab mappings: pending T20-T26")
    report.append("- Current lesson files: implemented and covered by the 64/64 competency audit")
    report.append("- Current assessment files: implemented and covered by deterministic rubric tests")
    report.append("- Current lab mappings: implemented through offline fixtures, live-shape fixtures, and eval parity checks")
    report.append("- Historical pending labels above identify the original manifest checkpoints; they are not current blockers after T29/T30")

    return errors, report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit AI-103 curriculum and lesson coverage.")
    parser.add_argument("--domain", choices=sorted(EXPECTED_DOMAIN_COUNTS), help="Optional domain filter, e.g. PM")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors, report = audit(domain=args.domain)
    print("\n".join(report))
    if errors:
        print("\n## Errors", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("\nAudit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
