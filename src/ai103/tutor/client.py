from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from ai103.services.foundry import create_foundry_project_client, foundry_model_name
from ai103.services.settings import AzureServiceSettings

from .context import TutorContext, load_approved_sources
from .schema import TutorOutput, validate_tutor_output


class ResponsesClientProtocol(Protocol):
    responses: Any


def create_responses_client(
    settings: AzureServiceSettings,
    *,
    project_client: Any | None = None,
    project_client_factory: Any = create_foundry_project_client,
) -> Any:
    project = project_client or project_client_factory(settings)
    if not hasattr(project, "get_openai_client"):
        raise TypeError("Foundry project client must expose get_openai_client()")
    return project.get_openai_client()


def request_tutor_response(
    context: TutorContext,
    *,
    settings: AzureServiceSettings,
    root: Path,
    responses_client: ResponsesClientProtocol | None = None,
    offline_response: dict[str, Any] | None = None,
) -> TutorOutput:
    approved_sources = load_approved_sources(root)
    if offline_response is not None:
        return validate_tutor_output(offline_response, approved_sources=approved_sources, allowed_lesson_ids=(context.lesson_id,))
    client = responses_client or create_responses_client(settings)
    response = client.responses.create(
        model=foundry_model_name(settings),
        input=[
            {"role": "system", "content": (root / "content" / "prompts" / "tutor" / "system.md").read_text(encoding="utf-8")},
            {"role": "user", "content": json.dumps(context.as_model_input(), sort_keys=True)},
        ],
    )
    return validate_tutor_output(_response_text(response), approved_sources=approved_sources, allowed_lesson_ids=(context.lesson_id,))


def offline_tutor_response(context: TutorContext) -> dict[str, Any]:
    citation = context.approved_sources[0]
    if context.zpd_level == 0:
        body = (
            "Worked example: first identify the AI-103 competency, then match the Azure service behavior to the "
            "approved source. Concrete example: for a retrieval app, separate grounding data from generation. "
            "Text diagram alt text: learner question -> retrieval -> grounded response. What is the first service "
            "boundary you would check?"
        )
        hint_level = 0
        follow_up = "example"
    else:
        body = (
            "Before an explanation, retrieve what you know: name the AI-103 competency and one Azure design choice "
            "that supports it. Then explain why that choice fits. What is your first recalled clue?"
        )
        hint_level = min(context.zpd_level, 3)
        follow_up = "retrieval"
    flags = []
    combined = f"{context.learner_attempt}\n{context.retrieved_text}".casefold()
    if "subscription" in combined or "api key" in combined or "patient" in combined:
        flags.append("sensitive-context-redacted")
    if "redacted-injection" in combined or "ignore" in combined:
        flags.append("prompt-injection-ignored")
    return {
        "lesson_id": context.lesson_id,
        "zpd_level": context.zpd_level,
        "response_markdown": body,
        "citations": [citation],
        "hint_level": hint_level,
        "suggested_follow_up": follow_up,
        "safety_flags": flags,
    }


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text
    if isinstance(response, dict) and isinstance(response.get("output_text"), str):
        return response["output_text"]
    raise TypeError("Responses API result must expose output_text")

