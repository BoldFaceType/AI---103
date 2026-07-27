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

