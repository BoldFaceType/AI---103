from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.learning.events import KNOWN_EVENT_TYPES, validate_learning_event

AI103_DOMAIN_IDS = {"PM", "GA", "CV", "TA", "IE"}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    candidate = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
    except ValueError:
        return False
    return True


def _validate_metric_entry(label: str, value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"knowledge entry '{label}' must be an object"]
    for field in ("mastery", "confidence"):
        metric = value.get(field)
        if not _is_number(metric) or metric < 0 or metric > 1:
            errors.append(f"knowledge entry '{label}' field '{field}' must be between 0 and 1")
    evidence_refs = value.get("evidence_refs")
    if evidence_refs is not None and not isinstance(evidence_refs, list):
        errors.append(f"knowledge entry '{label}' evidence_refs must be a list")
    return errors


def validate_profile(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data.get("name"), str) or not data["name"].strip():
        errors.append("profile.name must be a non-empty string")
    if not isinstance(data.get("primary_goal"), str) or not data["primary_goal"].strip():
        errors.append("profile.primary_goal must be a non-empty string")
    preferences = data.get("preferences", {})
    if not isinstance(preferences, dict):
        errors.append("profile.preferences must be an object")
    return errors


def validate_objectives(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict) or not data:
        return ["objectives must be a non-empty object"]

    if "schema_version" in data:
        if data.get("schema_version") != 2:
            errors.append("objectives.schema_version must be 2")
        objectives = data.get("objectives")
        if not isinstance(objectives, dict) or not objectives:
            errors.append("objectives.objectives must be a non-empty object")
            return errors
        if set(objectives) != AI103_DOMAIN_IDS:
            errors.append("objectives.objectives keys must be exactly PM, GA, CV, TA, and IE")
        weight_total = 0.0
        for key, value in objectives.items():
            if not isinstance(value, dict):
                errors.append(f"objective '{key}' must map to an object")
                continue
            weight = value.get("weight")
            if not _is_number(weight) or weight < 0 or weight > 1:
                errors.append(f"objective '{key}' weight must be between 0 and 1")
            else:
                weight_total += float(weight)
            competency_ids = value.get("competency_ids")
            if not isinstance(competency_ids, list) or not competency_ids:
                errors.append(f"objective '{key}' competency_ids must be a non-empty list")
        if round(weight_total, 3) != 1.0:
            errors.append(f"objectives weights must total 1.0; got {weight_total:.3f}")
        return errors

    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            errors.append("objective ids must be non-empty strings")
            continue
        if not isinstance(value, dict):
            errors.append(f"objective '{key}' must map to an object")
            continue
        weight = value.get("weight")
        if not _is_number(weight) or weight < 0:
            errors.append(f"objective '{key}' weight must be a non-negative number")
    return errors


def validate_learning_policy(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["learning policy must be an object"]
    threshold = data.get("remediation_threshold")
    if not _is_number(threshold) or threshold <= 0 or threshold > 1:
        errors.append("learning_policy.remediation_threshold must be greater than 0 and at most 1")
    return errors


def validate_knowledge_map(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["knowledge map must be an object"]

    if "schema_version" in data:
        if data.get("schema_version") != 2:
            errors.append("knowledge-map.schema_version must be 2")
        domains = data.get("domains")
        if not isinstance(domains, dict) or not domains:
            errors.append("knowledge-map.domains must be a non-empty object")
            return errors
        if set(domains) != AI103_DOMAIN_IDS:
            errors.append("knowledge-map.domains keys must be exactly PM, GA, CV, TA, and IE")
        for domain_id, value in domains.items():
            errors.extend(_validate_metric_entry(str(domain_id), value))
        legacy_evidence = data.get("legacy_evidence", {})
        if legacy_evidence is not None and not isinstance(legacy_evidence, dict):
            errors.append("knowledge-map.legacy_evidence must be an object")
        return errors

    for concept, value in data.items():
        errors.extend(_validate_metric_entry(concept, value))
    return errors


def validate_task(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("id", "type", "objective_ids", "estimated_minutes", "created_at", "source", "status")
    for field in required:
        if field not in data:
            errors.append(f"task missing required field '{field}'")
    if "schema_version" in data and data["schema_version"] != 2:
        errors.append("task.schema_version must be 2")
    if "objective_ids" in data and not isinstance(data["objective_ids"], list):
        errors.append("task.objective_ids must be a list")
    if "estimated_minutes" in data and (not _is_number(data["estimated_minutes"]) or data["estimated_minutes"] <= 0):
        errors.append("task.estimated_minutes must be positive")
    if data.get("status") not in {"open", "in_progress", "done"}:
        errors.append("task.status must be one of open, in_progress, done")
    if "created_at" in data and not _is_timestamp(data["created_at"]):
        errors.append("task.created_at must be an ISO timestamp")
    return errors


def validate_event(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("ts", "type", "event_id")
    for field in required:
        if field not in data:
            errors.append(f"event missing required field '{field}'")
    if "schema_version" not in data:
        errors.append("event.schema_version must be 2")
    elif data["schema_version"] != 2:
        errors.append("event.schema_version must be 2")
    if "ts" in data and not _is_timestamp(data["ts"]):
        errors.append("event.ts must be an ISO timestamp")
    if data.get("type") in KNOWN_EVENT_TYPES:
        errors.extend(validate_learning_event(data))
    return errors


def validate_path(path: Path, data: Any) -> list[str]:
    name = path.name
    if name == "profile.user.json":
        return validate_profile(data)
    if name == "objectives.ai103.json":
        return validate_objectives(data)
    if name == "learning-policy.json":
        return validate_learning_policy(data)
    if name == "knowledge-map.json":
        return validate_knowledge_map(data)
    if name.startswith("task-") or path.parent.name in {"todo", "in-progress", "done"}:
        return validate_task(data)
    if path.suffix == ".json" and path.parent.name in {"raw", "derived"}:
        return []
    return []
