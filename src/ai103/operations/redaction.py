from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
ENDPOINT_RE = re.compile(r"https://[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_./?=&%-]*)?")
SECRET_ASSIGNMENT_RE = re.compile(r"(?i)\b(api[_-]?key|secret|token|password|connection[_-]?string)\b\s*[:=]\s*['\"]?[^'\"\s,;]+")
ANSWER_KEY_RE = re.compile(r"(?im)(answer\s*key|correct\s*answers?)\s*:.*$")
PROMPT_INJECTION_RE = re.compile(r"(?i)(ignore (all )?(previous|system) instructions|reveal (the )?(answer key|system prompt)|developer message)")
MEDICAL_SOURCE_RE = re.compile(r"(?i)(synthetic patient:.*|Taylor Example|SYN-[A-Z0-9-]+)")
SCAN_SUFFIXES = {".json", ".md", ".py", ".ps1", ".toml", ".txt", ".yaml", ".yml"}
SCAN_EXCLUDED_DIRS = {
    ".azure-local",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".uv-cache",
    ".venv",
    "__pycache__",
    "logs",
    "reports",
    "state",
    "tests",
}
SECRET_SCAN_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?i)AI103_CANARY_SECRET_[A-Z0-9_]+"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)


class RedactionError(ValueError):
    """Raised when sensitive content remains after redaction."""


def redact_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = ANSWER_KEY_RE.sub("[redacted-answer-key]", text)
    text = SECRET_ASSIGNMENT_RE.sub("<redacted-secret>", text)
    text = GUID_RE.sub("<redacted-id>", text)
    text = ENDPOINT_RE.sub("https://<redacted-endpoint>", text)
    text = MEDICAL_SOURCE_RE.sub("<redacted-source-text>", text)
    text = PROMPT_INJECTION_RE.sub("[redacted-prompt-injection]", text)
    if len(text) > 800:
        return text[:360] + "\n[redacted-truncated]\n" + text[-160:]
    return text


def redact_mapping(data: dict[str, Any]) -> dict[str, Any]:
    return {key: _redact_value(value) for key, value in data.items()}


def assert_no_sensitive_content(text: str) -> None:
    safe_text = text
    for placeholder in ("<redacted-secret>", "<redacted-id>", "https://<redacted-endpoint>", "<redacted-source-text>", "[redacted-answer-key]"):
        safe_text = safe_text.replace(placeholder, "")
    checks = [
        ("endpoint", ENDPOINT_RE),
        ("id", GUID_RE),
        ("secret", SECRET_ASSIGNMENT_RE),
        ("answer key", ANSWER_KEY_RE),
        ("prompt injection", PROMPT_INJECTION_RE),
        ("medical source", MEDICAL_SOURCE_RE),
    ]
    for label, pattern in checks:
        if pattern.search(safe_text):
            raise RedactionError(f"sensitive {label} content was not redacted")


def defend_untrusted_text(text: str, *, boundary: str) -> dict[str, Any]:
    redacted = redact_text(text)
    return {
        "boundary": boundary,
        "trusted": False,
        "prompt_injection_detected": bool(PROMPT_INJECTION_RE.search(text)),
        "content": redacted,
    }


def tool_requires_approval(tool_name: str, *, destructive: bool = False, billable: bool = False) -> bool:
    allowlist = {"lookup_objective", "query_lab_index", "request_human_approval", "summarize_trace"}
    if tool_name not in allowlist:
        raise RedactionError(f"tool outside allowlist: {tool_name}")
    return destructive or billable


def retention_delete_plan(root: Path, *, include_tutor: bool = True) -> list[Path]:
    paths = [root / "logs" / "events.ndjson", root / "_meta" / "cli-audit.ndjson", root / "state" / "sessions" / "current.json"]
    if include_tutor:
        paths.append(root / "logs" / "tutor-feedback.ndjson")
    return paths


def scan_paths(paths: Iterable[Path]) -> list[str]:
    findings: list[str] = []
    for root in paths:
        files = [root] if root.is_file() else _iter_scan_files(root)
        for file in files:
            text = file.read_text(encoding="utf-8", errors="ignore")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if "ALLOW_CANARY_SECRET" in line:
                    continue
                for pattern in SECRET_SCAN_PATTERNS:
                    if pattern.search(line):
                        findings.append(f"{file}:{line_number}: potential secret")
    return findings


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def _iter_scan_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in SCAN_SUFFIXES and not any(part in SCAN_EXCLUDED_DIRS for part in path.parts)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan repository text files for obvious committed secrets.")
    parser.add_argument("--scan", nargs="+", type=Path, required=True)
    args = parser.parse_args(argv)
    findings = scan_paths(args.scan)
    if findings:
        print(json.dumps({"ok": False, "findings": findings}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "findings": []}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
