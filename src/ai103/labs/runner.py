from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ai103.learning.events import validate_learning_event

from .grading import grade_lab_output, lab_result_to_event, normalize_lab_output, redact_resource_id, redact_text, utc_now, validate_lab_result
from .registry import LabSpec, get_lab_spec

Mode = Literal["offline", "live"]
LiveAdapter = Callable[[LabSpec], dict[str, Any]]


class LabRunError(RuntimeError):
    """Raised when a lab cannot be executed safely."""


class LabNetworkError(RuntimeError):
    def __init__(self, message: str, *, partial_resources: list[str] | None = None) -> None:
        super().__init__(message)
        self.partial_resources = partial_resources or []


@dataclass(frozen=True)
class LabRun:
    result: dict[str, Any]
    event: dict[str, Any] | None = None
    error: str | None = None


def run_lab(
    lab_id: str,
    *,
    root: Path,
    mode: Mode = "offline",
    live_adapter: LiveAdapter | None = None,
    event_log_path: Path | None = None,
    event_id: str | None = None,
) -> LabRun:
    spec = get_lab_spec(lab_id, root)
    started_at = utc_now()
    if mode == "offline":
        raw = json.loads(spec.fixture_path.read_text(encoding="utf-8"))
    elif mode == "live":
        if live_adapter is None:
            raise LabRunError("live mode requires an explicit live_adapter; offline is the default")
        try:
            raw = live_adapter(spec)
        except LabNetworkError as exc:
            result = _failed_network_result(spec, mode=mode, started_at=started_at, error=str(exc), partial_resources=exc.partial_resources)
            return LabRun(result=result, error=str(exc))
    else:
        raise LabRunError("mode must be offline or live")

    result = grade_lab_output(spec, normalize_lab_output(raw), mode=mode, started_at=started_at, completed_at=utc_now())
    event = None
    if result["score"] >= spec.passing_score:
        event = lab_result_to_event(result, event_id=event_id or f"lab-{lab_id}-{result['completed_at']}")
        event_errors = validate_learning_event(event)
        if event_errors:
            raise LabRunError(f"generated invalid lab_completed event: {'; '.join(event_errors)}")
        if event_log_path is not None:
            _append_event(event_log_path, event)
    return LabRun(result=result, event=event)


def _failed_network_result(
    spec: LabSpec,
    *,
    mode: Mode,
    started_at: str,
    error: str,
    partial_resources: list[str],
) -> dict[str, Any]:
    result = {
        "schema_version": 1,
        "lab_id": spec.lab_id,
        "mode": mode,
        "started_at": started_at,
        "completed_at": utc_now(),
        "checks": [{"id": "network", "passed": False, "evidence": redact_text(f"Network failure: {error}")}],
        "score": 0.0,
        "objective_ids": list(spec.objective_ids),
        "resource_ids": [],
        "partial_resources": [redact_resource_id(value) for value in partial_resources],
        "cost_estimate": None,
        "teardown_verified": False,
    }
    validate_lab_result(result)
    return result


def _append_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing + json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")
