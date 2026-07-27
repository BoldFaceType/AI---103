from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LabCheckSpec:
    id: str
    response: str
    path: tuple[str, ...]
    expected: object
    evidence_template: str


@dataclass(frozen=True)
class LabSpec:
    lab_id: str
    title: str
    objective_ids: tuple[str, ...]
    fixture_path: Path
    required_response_shapes: tuple[str, ...]
    checks: tuple[LabCheckSpec, ...]
    passing_score: float = 0.8


def default_registry(root: Path) -> dict[str, LabSpec]:
    return {
        "LAB-VISION-ANALYSIS": LabSpec(
            lab_id="LAB-VISION-ANALYSIS",
            title="Multimodal vision analysis fixture",
            objective_ids=("CV-01", "CV-02", "GA-03"),
            fixture_path=root / "fixtures" / "azure-responses" / "LAB-VISION-ANALYSIS.offline.json",
            required_response_shapes=("vision",),
            checks=(
                LabCheckSpec(
                    id="caption-present",
                    response="vision",
                    path=("caption",),
                    expected="A learner reviews an Azure AI study diagram on a laptop.",
                    evidence_template="Vision caption matched approved fixture caption: {value}.",
                ),
                LabCheckSpec(
                    id="detailed-description-present",
                    response="vision",
                    path=("detailed_description",),
                    expected="The image shows a desk setup with a laptop displaying an AI-103 study diagram, notes, and a visible prompt-injection warning label.",
                    evidence_template="Detailed description covered scene and study context: {value}.",
                ),
                LabCheckSpec(
                    id="accessible-alt-text-present",
                    response="vision",
                    path=("alt_text",),
                    expected="Laptop on a desk showing an AI-103 study diagram with notes and a prompt-injection warning.",
                    evidence_template="Accessible alt text was produced: {value}.",
                ),
                LabCheckSpec(
                    id="visual-qa-grounded",
                    response="vision",
                    path=("visual_qa", "0", "answer"),
                    expected="The visible study topic is AI-103 vision analysis.",
                    evidence_template="Visual Q&A answered from image evidence: {value}.",
                ),
                LabCheckSpec(
                    id="object-region-detected",
                    response="vision",
                    path=("objects", "0", "name"),
                    expected="laptop",
                    evidence_template="Object detection included expected object: {value}.",
                ),
                LabCheckSpec(
                    id="region-supported",
                    response="vision",
                    path=("regions", "0", "label"),
                    expected="screen",
                    evidence_template="Region metadata included supported region: {value}.",
                ),
                LabCheckSpec(
                    id="embedded-text-injection-ignored",
                    response="vision",
                    path=("safety", "embedded_text_prompt_injection_detected"),
                    expected=True,
                    evidence_template="Embedded text injection detection was {value}.",
                ),
                LabCheckSpec(
                    id="unsafe-content-checked",
                    response="vision",
                    path=("safety", "unsafe_content_detected"),
                    expected=False,
                    evidence_template="Unsafe content detection was {value}.",
                ),
                LabCheckSpec(
                    id="service-metadata-cited",
                    response="vision",
                    path=("model_metadata", "service"),
                    expected="offline-fixture",
                    evidence_template="Vision output cited service metadata: {value}.",
                ),
            ),
        ),
        "LAB-SEARCH-RAG": LabSpec(
            lab_id="LAB-SEARCH-RAG",
            title="Grounded search and RAG fixture",
            objective_ids=("GA-02", "IE-02", "IE-04"),
            fixture_path=root / "fixtures" / "azure-responses" / "LAB-SEARCH-RAG.offline.json",
            required_response_shapes=("search", "foundry", "content_understanding", "storage"),
            checks=(
                LabCheckSpec(
                    id="search-returned-citation",
                    response="search",
                    path=("citations", "0", "source_id"),
                    expected="doc-1#p3",
                    evidence_template="Search returned grounding citation {value}.",
                ),
                LabCheckSpec(
                    id="rag-answer-cited-source",
                    response="foundry",
                    path=("citations", "0"),
                    expected="doc-1#p3",
                    evidence_template="Model answer cited retrieved source {value}.",
                ),
                LabCheckSpec(
                    id="content-understanding-markdown",
                    response="content_understanding",
                    path=("markdown_sections", "0"),
                    expected="Vector search setup",
                    evidence_template="Analyzer produced markdown section {value}.",
                ),
                LabCheckSpec(
                    id="storage-public-access-disabled",
                    response="storage",
                    path=("allow_blob_public_access",),
                    expected=False,
                    evidence_template="Storage public blob access is {value}.",
                ),
            ),
        )
    }


def get_lab_spec(lab_id: str, root: Path) -> LabSpec:
    registry = default_registry(root)
    try:
        return registry[lab_id]
    except KeyError as exc:
        raise ValueError(f"unknown lab_id: {lab_id}") from exc
