from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .redaction import assert_no_sensitive_content, redact_mapping


@dataclass(frozen=True)
class TraceRecord:
    correlation_id: str
    service: str
    mode: str
    result: str
    latency_ms: int
    token_usage: dict[str, int]
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "correlation_id": self.correlation_id,
            "service": self.service,
            "mode": self.mode,
            "result": self.result,
            "latency_ms": self.latency_ms,
            "token_usage": dict(self.token_usage),
            "details": redact_mapping(self.details),
        }


def build_trace(
    *,
    correlation_id: str,
    service: str,
    mode: str,
    result: str,
    latency_ms: int,
    token_usage: dict[str, int] | None = None,
    details: dict[str, Any] | None = None,
) -> TraceRecord:
    if mode not in {"offline", "live"}:
        raise ValueError("trace mode must be offline or live")
    if latency_ms < 0:
        raise ValueError("trace latency must be non-negative")
    tokens = token_usage or {"input": 0, "output": 0, "total": 0}
    return TraceRecord(
        correlation_id=correlation_id,
        service=service,
        mode=mode,
        result=result,
        latency_ms=latency_ms,
        token_usage=tokens,
        details=details or {},
    )


def append_trace(path: Path, record: TraceRecord) -> None:
    row = record.as_dict()
    serialized = json.dumps(row, sort_keys=True)
    assert_no_sensitive_content(serialized)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing + serialized + "\n", encoding="utf-8")

