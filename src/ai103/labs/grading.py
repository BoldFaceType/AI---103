from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from .registry import LabSpec

Mode = Literal["offline", "live"]
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
URL_RE = re.compile(r"https://[^\s,]+")


class LabValidationError(ValueError):
    """Raised when lab input or output violates the Section 10 contract."""


@dataclass(frozen=True)
class NormalizedLabOutput:
    responses: dict[str, Any]
    resource_ids: tuple[str, ...] = ()
    cost_estimate: dict[str, Any] | None = None
    teardown_verified: bool = True
    partial_resources: tuple[str, ...] = ()


def normalize_lab_output(raw: dict[str, Any]) -> NormalizedLabOutput:
    if "responses" in raw:
        responses = dict(raw["responses"])
    elif "vision" in raw:
        responses = {"vision": dict(raw["vision"])}
    else:
        responses = {
            "search": _normalize_search(raw.get("search", {})),
            "foundry": _normalize_foundry(raw.get("foundry", {})),
            "content_understanding": _normalize_content_understanding(raw.get("content_understanding", {})),
            "storage": _normalize_storage(raw.get("storage", {})),
        }
    return NormalizedLabOutput(
        responses=responses,
        resource_ids=tuple(str(value) for value in raw.get("resource_ids", [])),
        cost_estimate=raw.get("cost_estimate"),
        teardown_verified=bool(raw.get("teardown_verified", True)),
        partial_resources=tuple(str(value) for value in raw.get("partial_resources", [])),
    )


def grade_lab_output(
    spec: LabSpec,
    normalized: NormalizedLabOutput,
    *,
    mode: Mode = "offline",
    started_at: str | None = None,
    completed_at: str | None = None,
) -> dict[str, Any]:
    validate_lab_input({"lab_id": spec.lab_id, "mode": mode, "objective_ids": list(spec.objective_ids)})
    missing_shapes = sorted(set(spec.required_response_shapes) - set(normalized.responses))
    if missing_shapes:
        raise LabValidationError(f"missing Azure response shapes: {', '.join(missing_shapes)}")

    checks = []
    for check in spec.checks:
        actual = _get_path(normalized.responses[check.response], check.path)
        passed = actual == check.expected
        evidence = check.evidence_template.format(value=actual)
        checks.append({"id": check.id, "passed": passed, "evidence": redact_text(evidence)})
    if not normalized.teardown_verified:
        checks.append({"id": "teardown-verified", "passed": False, "evidence": "Teardown was not verified."})
    possible = len(checks)
    passed_count = sum(1 for check in checks if check["passed"])
    score = round(passed_count / possible, 4) if possible else 0.0
    result = {
        "schema_version": 1,
        "lab_id": spec.lab_id,
        "mode": mode,
        "started_at": started_at or utc_now(),
        "completed_at": completed_at or utc_now(),
        "checks": checks,
        "score": score,
        "objective_ids": list(spec.objective_ids),
        "resource_ids": [redact_resource_id(value) for value in normalized.resource_ids],
        "cost_estimate": normalized.cost_estimate,
        "teardown_verified": normalized.teardown_verified,
    }
    if normalized.partial_resources:
        result["partial_resources"] = [redact_resource_id(value) for value in normalized.partial_resources]
    validate_lab_result(result)
    return result


def validate_lab_input(data: dict[str, Any]) -> None:
    if data.get("mode") not in {"offline", "live"}:
        raise LabValidationError("lab input mode must be offline or live")
    if not isinstance(data.get("lab_id"), str) or not data["lab_id"].strip():
        raise LabValidationError("lab input lab_id must be a non-empty string")
    objective_ids = data.get("objective_ids")
    if not isinstance(objective_ids, list) or not objective_ids or not all(isinstance(item, str) and item for item in objective_ids):
        raise LabValidationError("lab input objective_ids must be non-empty strings")


def validate_lab_result(data: dict[str, Any]) -> None:
    required = (
        "schema_version",
        "lab_id",
        "mode",
        "started_at",
        "completed_at",
        "checks",
        "score",
        "objective_ids",
        "resource_ids",
        "cost_estimate",
        "teardown_verified",
    )
    missing = [field for field in required if field not in data]
    if missing:
        raise LabValidationError(f"lab result missing fields: {', '.join(missing)}")
    if data["schema_version"] != 1:
        raise LabValidationError("lab result schema_version must be 1")
    validate_lab_input({"lab_id": data["lab_id"], "mode": data["mode"], "objective_ids": data["objective_ids"]})
    if not ISO_RE.match(str(data["started_at"])) or not ISO_RE.match(str(data["completed_at"])):
        raise LabValidationError("lab result timestamps must be ISO-8601 strings")
    if not isinstance(data["checks"], list) or not data["checks"]:
        raise LabValidationError("lab result checks must be a non-empty list")
    for check in data["checks"]:
        if not isinstance(check, dict):
            raise LabValidationError("lab result checks must contain objects")
        if not isinstance(check.get("id"), str) or not isinstance(check.get("passed"), bool) or not isinstance(check.get("evidence"), str):
            raise LabValidationError("lab result check must include id, passed, and evidence")
    if not isinstance(data["score"], (int, float)) or isinstance(data["score"], bool) or not 0 <= float(data["score"]) <= 1:
        raise LabValidationError("lab result score must be between 0 and 1")
    if not isinstance(data["resource_ids"], list):
        raise LabValidationError("lab result resource_ids must be a list")
    if not isinstance(data["teardown_verified"], bool):
        raise LabValidationError("lab result teardown_verified must be a boolean")


def lab_result_to_event(result: dict[str, Any], *, event_id: str) -> dict[str, Any]:
    validate_lab_result(result)
    return {
        "schema_version": 2,
        "ts": result["completed_at"],
        "type": "lab_completed",
        "event_id": event_id,
        "score": float(result["score"]),
        "objective_ids": list(result["objective_ids"]),
        "lab_id": result["lab_id"],
        "mode": result["mode"],
        "result_ref": f"lab:{result['lab_id']}:{event_id}",
    }


def redact_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = URL_RE.sub("https://<redacted-endpoint>", text)
    text = GUID_RE.sub("<redacted-id>", text)
    for marker in ("token", "secret", "password", "key"):
        text = text.replace(marker, "<redacted>")
        text = text.replace(marker.upper(), "<redacted>")
    if len(text) > 240:
        return f"{text[:120]}…<redacted>…{text[-60:]}"
    return text


def redact_resource_id(resource_id: str) -> str:
    return URL_RE.sub("https://<redacted-endpoint>", GUID_RE.sub("<redacted-id>", resource_id))


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _normalize_search(raw: dict[str, Any]) -> dict[str, Any]:
    value = raw.get("value", [])
    citations = []
    if value and isinstance(value, list):
        first = value[0]
        citations.append({"source_id": first.get("source_id") or first.get("citation") or first.get("id")})
    return {"citations": citations, "documents": value}


def _normalize_foundry(raw: dict[str, Any]) -> dict[str, Any]:
    return {"answer": raw.get("answer") or raw.get("output_text") or "", "citations": raw.get("citations", [])}


def _normalize_content_understanding(raw: dict[str, Any]) -> dict[str, Any]:
    result = raw.get("result", raw)
    return {"markdown_sections": result.get("markdown_sections") or result.get("sections") or []}


def _normalize_storage(raw: dict[str, Any]) -> dict[str, Any]:
    properties = raw.get("properties", raw)
    return {"allow_blob_public_access": properties.get("allowBlobPublicAccess", properties.get("allow_blob_public_access"))}


def _get_path(data: Any, path: tuple[str, ...]) -> Any:
    current = data
    for part in path:
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current
