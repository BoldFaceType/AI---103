from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

APPROVED_FOLLOW_UPS = {"retrieval", "example", "self_explanation", "lab"}
FORBIDDEN_OUTPUT_MARKERS = (
    "answer key",
    "api key",
    "access token",
    "connection string",
    "subscription id",
    "subscription identifier",
    "tenant id",
    "tenant identifier",
    "real phi",
    "pass/fail",
    "certification readiness",
)
FORBIDDEN_GRADING_MARKERS = ("score", "mastery", "grade", "passing", "failing")


class TutorValidationError(ValueError):
    """Raised when a tutor response violates the tutor contract."""


@dataclass(frozen=True)
class TutorCitation:
    title: str
    url: str


@dataclass(frozen=True)
class TutorOutput:
    lesson_id: str
    zpd_level: int
    response_markdown: str
    citations: tuple[TutorCitation, ...]
    hint_level: int
    suggested_follow_up: str
    safety_flags: tuple[str, ...]

    def as_event_payload(self) -> dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "zpd_level": self.zpd_level,
            "response_markdown": self.response_markdown,
            "citations": [citation.__dict__ for citation in self.citations],
            "hint_level": self.hint_level,
            "suggested_follow_up": self.suggested_follow_up,
            "safety_flags": list(self.safety_flags),
        }


def parse_tutor_output(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise TutorValidationError("tutor output must be JSON") from exc
    elif isinstance(value, dict):
        parsed = value
    else:
        raise TutorValidationError("tutor output must be a JSON object")
    if not isinstance(parsed, dict):
        raise TutorValidationError("tutor output must be a JSON object")
    return parsed


def validate_tutor_output(
    value: Any,
    *,
    approved_sources: Iterable[dict[str, str]],
    allowed_lesson_ids: Iterable[str] | None = None,
) -> TutorOutput:
    data = parse_tutor_output(value)
    approved_by_url = {source["url"]: source["title"] for source in approved_sources}
    lesson_id = _required_str(data, "lesson_id")
    if allowed_lesson_ids is not None and lesson_id not in set(allowed_lesson_ids):
        raise TutorValidationError("lesson_id is not in the allowed context")
    zpd_level = _bounded_int(data, "zpd_level", minimum=0, maximum=4)
    response_markdown = _required_str(data, "response_markdown")
    _reject_forbidden_text(response_markdown)
    citations = _validate_citations(data.get("citations"), approved_by_url)
    hint_level = _bounded_int(data, "hint_level", minimum=0, maximum=3)
    suggested_follow_up = _required_str(data, "suggested_follow_up")
    if suggested_follow_up not in APPROVED_FOLLOW_UPS:
        raise TutorValidationError("suggested_follow_up is not approved")
    safety_flags = tuple(_string_list(data.get("safety_flags", []), "safety_flags"))
    return TutorOutput(
        lesson_id=lesson_id,
        zpd_level=zpd_level,
        response_markdown=response_markdown,
        citations=tuple(citations),
        hint_level=hint_level,
        suggested_follow_up=suggested_follow_up,
        safety_flags=safety_flags,
    )


def tutor_feedback_event(output: TutorOutput, *, event_id: str, timestamp: str, competency_ids: Iterable[str]) -> dict[str, Any]:
    payload = output.as_event_payload()
    return {
        "schema_version": 2,
        "event_id": event_id,
        "event_type": "tutor_feedback_received",
        "timestamp": timestamp,
        "payload": {
            "competency_ids": list(competency_ids),
            "feedback": payload,
        },
    }


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TutorValidationError(f"{key} is required")
    return value.strip()


def _bounded_int(data: dict[str, Any], key: str, *, minimum: int, maximum: int) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise TutorValidationError(f"{key} must be an integer from {minimum} to {maximum}")
    return value


def _string_list(value: Any, key: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TutorValidationError(f"{key} must be a list of strings")
    return [item.strip() for item in value if item.strip()]


def _validate_citations(value: Any, approved_by_url: dict[str, str]) -> list[TutorCitation]:
    if not isinstance(value, list) or not value:
        raise TutorValidationError("at least one approved citation is required")
    citations = []
    for item in value:
        if not isinstance(item, dict):
            raise TutorValidationError("citations must be objects")
        title = item.get("title")
        url = item.get("url")
        if not isinstance(title, str) or not isinstance(url, str):
            raise TutorValidationError("citation title and url are required")
        if url not in approved_by_url or title != approved_by_url[url]:
            raise TutorValidationError("citation is not an approved Microsoft source")
        citations.append(TutorCitation(title=title, url=url))
    return citations


def _reject_forbidden_text(text: str) -> None:
    folded = text.casefold()
    for marker in FORBIDDEN_OUTPUT_MARKERS:
        if marker in folded:
            raise TutorValidationError(f"tutor output exposes forbidden marker: {marker}")
    for marker in FORBIDDEN_GRADING_MARKERS:
        if marker in folded:
            raise TutorValidationError("tutor output must not grade or alter mastery")

