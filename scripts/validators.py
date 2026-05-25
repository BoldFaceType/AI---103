from __future__ import annotations

from pathlib import Path
from typing import Any


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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


def validate_knowledge_map(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["knowledge map must be an object"]
    for concept, value in data.items():
        if not isinstance(value, dict):
            errors.append(f"knowledge entry '{concept}' must be an object")
            continue
        for field in ("mastery", "confidence"):
            metric = value.get(field)
            if not _is_number(metric) or metric < 0 or metric > 1:
                errors.append(f"knowledge entry '{concept}' field '{field}' must be between 0 and 1")
    return errors


def validate_task(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("id", "type", "objective_ids", "estimated_minutes", "created_at", "source", "status")
    for field in required:
        if field not in data:
            errors.append(f"task missing required field '{field}'")
    if "objective_ids" in data and not isinstance(data["objective_ids"], list):
        errors.append("task.objective_ids must be a list")
    if "estimated_minutes" in data and (not _is_number(data["estimated_minutes"]) or data["estimated_minutes"] <= 0):
        errors.append("task.estimated_minutes must be positive")
    if data.get("status") not in {"open", "in_progress", "done"}:
        errors.append("task.status must be one of open, in_progress, done")
    return errors


def validate_event(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ("ts", "type", "event_id")
    for field in required:
        if field not in data:
            errors.append(f"event missing required field '{field}'")
    if data.get("type") == "quiz_completed":
        if not _is_number(data.get("score")):
            errors.append("quiz_completed.score must be numeric")
        if not isinstance(data.get("concepts"), list) or not data["concepts"]:
            errors.append("quiz_completed.concepts must be a non-empty list")
    return errors


def validate_path(path: Path, data: Any) -> list[str]:
    name = path.name
    if name == "profile.user.json":
        return validate_profile(data)
    if name == "objectives.ai103.json":
        return validate_objectives(data)
    if name == "knowledge-map.json":
        return validate_knowledge_map(data)
    if name.startswith("task-") or path.parent.name in {"todo", "in-progress", "done"}:
        return validate_task(data)
    if path.suffix == ".json" and path.parent.name in {"raw", "derived"}:
        return []
    return []