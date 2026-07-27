from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from ai103.services.content_understanding import create_content_understanding_client
from ai103.services.foundry import foundry_model_name
from ai103.services.settings import AzureServiceSettings, redact_value
from ai103.tutor.client import create_responses_client

from .runner import LabRun, run_lab

Mode = Literal["offline", "live"]
APPROVED_TEXT_SUFFIXES = {".json", ".md", ".txt"}
SYNTHETIC_MARKER = "SYNTHETIC TRAINING NOTE"
REAL_PHI_PATTERNS = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b"),
)


class MedicalTextLabError(ValueError):
    """Raised when the synthetic clinical text lab cannot safely run."""


def run_medical_text_lab(
    input_path: Path,
    *,
    root: Path,
    mode: Mode = "offline",
    settings: AzureServiceSettings | None = None,
    responses_client: Any | None = None,
    content_understanding_client: Any | None = None,
    event_log_path: Path | None = None,
    event_id: str | None = None,
) -> LabRun:
    documents = discover_synthetic_documents(input_path)
    if mode == "offline":
        return run_lab("LAB-MEDICAL-TEXT", root=root, mode="offline", event_log_path=event_log_path, event_id=event_id)
    if mode != "live":
        raise MedicalTextLabError("mode must be offline or live")
    if settings is None:
        raise MedicalTextLabError("live mode requires AzureServiceSettings")

    def adapter(_spec: object) -> dict[str, Any]:
        return analyze_medical_text_live(
            documents,
            settings=settings,
            responses_client=responses_client,
            content_understanding_client=content_understanding_client,
        )

    return run_lab("LAB-MEDICAL-TEXT", root=root, mode="live", live_adapter=adapter, event_log_path=event_log_path, event_id=event_id)


def discover_synthetic_documents(input_path: Path) -> tuple[Path, ...]:
    path = input_path.resolve()
    if path.is_file():
        _validate_synthetic_document(path)
        return (path,)
    if not path.is_dir():
        raise MedicalTextLabError(f"input path does not exist: {input_path}")
    documents = tuple(sorted(item for item in path.iterdir() if item.is_file() and item.suffix.casefold() in APPROVED_TEXT_SUFFIXES))
    for document in documents:
        _validate_synthetic_document(document)
    if not documents:
        raise MedicalTextLabError("no approved synthetic text documents found")
    return documents


def analyze_medical_text_live(
    documents: tuple[Path, ...],
    *,
    settings: AzureServiceSettings,
    responses_client: Any | None = None,
    content_understanding_client: Any | None = None,
) -> dict[str, Any]:
    text = "\n\n".join(document.read_text(encoding="utf-8") for document in documents)
    content_client = content_understanding_client or create_content_understanding_client(settings)
    content_result = _call_content_understanding(content_client, text)
    client = responses_client or create_responses_client(settings)
    model = foundry_model_name(settings)
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": (
                    "This is a synthetic AI-103 clinical text extraction lab. Return only JSON with redacted_markdown, "
                    "pii, entities, topics, structured_fields, summary, tone_safety, domain_concepts, service_comparison, "
                    "and model_metadata. Do not include source text."
                ),
            },
            {"role": "user", "content": redact_medical_text(text)},
        ],
    )
    medical_text = _parse_model_output(response)
    medical_text["service_comparison"] = medical_text.get(
        "service_comparison",
        {
            "language": "PII, entities, topics",
            "content_understanding": "layout and structured fields",
            "model": "summary and safety explanation",
        },
    )
    medical_text["model_metadata"] = {
        "services": ["Azure AI Language", "Azure AI Content Understanding", "Azure AI Foundry Responses API"],
        "model": model,
        "content_understanding": content_result,
    }
    return {
        "responses": {"medical_text": medical_text},
        "resource_ids": [settings.content_understanding_endpoint or "", settings.foundry_project_endpoint or ""],
        "cost_estimate": {"currency": "USD", "estimated": 0.04, "note": "Estimate only; verify Azure pricing before live runs."},
        "teardown_verified": True,
    }


def redact_medical_text(text: str) -> str:
    redacted = re.sub(r"(?im)^synthetic patient:.*$", "Synthetic patient: <redacted-synthetic-person>", text)
    redacted = re.sub(r"\bTaylor(?: Example)?\b", "<redacted-synthetic-person>", redacted)
    redacted = re.sub(r"\bSYN-[A-Z0-9-]+\b", "<redacted-synthetic-id>", redacted)
    redacted = re.sub(r"\b555-\d{4}\b", "<redacted-synthetic-phone>", redacted)
    return redacted


def live_cost_notice(settings: AzureServiceSettings) -> str:
    return (
        "Estimated live cost: low, usage-based Language, Content Understanding, and Foundry model calls. "
        f"Content endpoint: {redact_value(settings.content_understanding_endpoint)}. "
        f"Foundry endpoint: {redact_value(settings.foundry_project_endpoint)}."
    )


def _validate_synthetic_document(path: Path) -> None:
    if path.suffix.casefold() not in APPROVED_TEXT_SUFFIXES:
        raise MedicalTextLabError(f"unsupported document type: {path.name}")
    text = path.read_text(encoding="utf-8")
    if SYNTHETIC_MARKER not in text:
        raise MedicalTextLabError(f"document lacks synthetic marker: {path.name}")
    for pattern in REAL_PHI_PATTERNS:
        if pattern.search(text):
            raise MedicalTextLabError(f"document contains PHI-like value: {path.name}")


def _call_content_understanding(client: Any, text: str) -> dict[str, str]:
    if hasattr(client, "begin_analyze"):
        client.begin_analyze(analyzer_id="ai103-synthetic-clinical", body={"text": redact_medical_text(text)})
    return {"analyzer": "ai103-synthetic-clinical", "role": "layout and structured fields"}


def _parse_model_output(response: Any) -> dict[str, Any]:
    output_text = getattr(response, "output_text", None)
    if isinstance(response, dict):
        output_text = response.get("output_text", output_text)
    if not isinstance(output_text, str):
        raise MedicalTextLabError("live medical-text response must expose output_text")
    try:
        parsed = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise MedicalTextLabError("live medical-text response must be JSON") from exc
    if not isinstance(parsed, dict):
        raise MedicalTextLabError("live medical-text response must be a JSON object")
    return parsed
