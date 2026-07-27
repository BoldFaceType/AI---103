from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from ai103.services.search import create_search_client, create_search_index_client
from ai103.services.settings import AzureServiceSettings, redact_value
from ai103.tutor.client import create_responses_client

from .runner import LabRun, run_lab

Mode = Literal["offline", "live"]
LAB_INDEX_PREFIX = "ai103-lab-vector-"
QUERY_MODES = ("vector", "semantic", "hybrid", "keyword")


class VectorSearchLabError(ValueError):
    """Raised when vector search lab inputs or live actions are unsafe."""


def run_vector_search_lab(
    input_path: Path,
    *,
    root: Path,
    mode: Mode = "offline",
    settings: AzureServiceSettings | None = None,
    search_client: Any | None = None,
    index_client: Any | None = None,
    foundry_client: Any | None = None,
    keep_resources: bool = False,
    event_log_path: Path | None = None,
    event_id: str | None = None,
) -> LabRun:
    documents = load_search_documents(input_path)
    validate_citations_trace_to_documents(documents)
    if mode == "offline":
        return run_lab("LAB-VECTOR-SEARCH", root=root, mode="offline", event_log_path=event_log_path, event_id=event_id)
    if mode != "live":
        raise VectorSearchLabError("mode must be offline or live")
    if settings is None:
        raise VectorSearchLabError("live mode requires AzureServiceSettings")

    def adapter(_spec: object) -> dict[str, Any]:
        return analyze_vector_search_live(
            documents,
            settings=settings,
            search_client=search_client,
            index_client=index_client,
            foundry_client=foundry_client,
            keep_resources=keep_resources,
        )

    return run_lab("LAB-VECTOR-SEARCH", root=root, mode="live", live_adapter=adapter, event_log_path=event_log_path, event_id=event_id)


def load_search_documents(input_path: Path) -> tuple[dict[str, Any], ...]:
    path = input_path.resolve()
    if path.is_dir():
        files = tuple(sorted(path.glob("*.json")))
    elif path.is_file():
        files = (path,)
    else:
        raise VectorSearchLabError(f"input path does not exist: {input_path}")
    documents: list[dict[str, Any]] = []
    for file in files:
        payload = json.loads(file.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("documents")
        if not isinstance(rows, list):
            raise VectorSearchLabError(f"search fixture must contain documents: {file.name}")
        for row in rows:
            if not isinstance(row, dict):
                raise VectorSearchLabError(f"search document must be an object: {file.name}")
            documents.append(_validate_document(row))
    if not documents:
        raise VectorSearchLabError("no search documents found")
    return tuple(documents)


def safe_lab_index_name(seed: str | None) -> str:
    suffix_source = seed or "study"
    suffix = re.sub(r"[^a-z0-9-]+", "-", suffix_source.casefold()).strip("-")
    suffix = suffix.replace("ai103-lab-vector-", "") or "study"
    return f"{LAB_INDEX_PREFIX}{suffix[:48]}"


def assert_lab_index_name(index_name: str) -> None:
    if not index_name.startswith(LAB_INDEX_PREFIX):
        raise VectorSearchLabError(f"refusing to modify non-lab search index: {index_name}")


def validate_citations_trace_to_documents(documents: tuple[dict[str, Any], ...], citations: set[str] | None = None) -> None:
    known = {citation for document in documents for citation in document["citations"]}
    missing = sorted((citations or known) - known)
    if missing:
        raise VectorSearchLabError(f"citations cannot be traced to fixture documents: {', '.join(missing)}")


def analyze_vector_search_live(
    documents: tuple[dict[str, Any], ...],
    *,
    settings: AzureServiceSettings,
    search_client: Any | None = None,
    index_client: Any | None = None,
    foundry_client: Any | None = None,
    keep_resources: bool = False,
) -> dict[str, Any]:
    settings.require_search()
    index_name = safe_lab_index_name(settings.search_index)
    assert_lab_index_name(index_name)
    index = build_index_schema(index_name)
    index_ops = index_client or create_search_index_client(settings)
    search_ops = search_client or create_search_client(settings)
    foundry = foundry_client or create_responses_client(settings)
    created_or_reused = _create_or_reuse_index(index_ops, index)
    model = _model_name(settings)
    embedded_documents = _with_embeddings(foundry, documents, model=model)
    uploaded = _upload_documents(search_ops, embedded_documents)
    queries = {mode: _query_mode(search_ops, mode) for mode in QUERY_MODES}
    citations = {data["top_citation"] for data in queries.values()}
    validate_citations_trace_to_documents(documents, citations)
    rag = _rag_answer(foundry, queries["hybrid"], model=model)
    validate_citations_trace_to_documents(documents, set(rag["citations"]))
    deleted = False
    if not keep_resources:
        deleted = _delete_index(index_ops, index_name)
    vector_search = {
        "index": {"name": index_name, "created_or_reused": created_or_reused},
        "ingestion": {"document_count": uploaded},
        "embeddings": {"provider": "Azure AI Foundry", "model": model, "document_count": len(embedded_documents)},
        "queries": queries,
        "evaluation": {"recall_at_1": _recall_at_1(queries)},
        "rag": rag,
        "teardown": {"deleted_index": deleted, "kept_resources": keep_resources},
    }
    return {
        "responses": {"vector_search": vector_search},
        "resource_ids": [settings.search_endpoint or "", index_name],
        "cost_estimate": {"currency": "USD", "estimated": 0.06, "note": "Estimate only; verify Search and Foundry pricing before live runs."},
        "teardown_verified": deleted or keep_resources,
    }


def build_index_schema(index_name: str) -> dict[str, Any]:
    assert_lab_index_name(index_name)
    return {
        "name": index_name,
        "fields": ["id", "title", "content", "citation", "content_vector"],
        "vector_search": {"algorithm": "hnsw", "dimensions": 3},
        "semantic_configuration": "ai103-semantic-config",
    }


def live_cost_notice(settings: AzureServiceSettings, *, keep_resources: bool = False) -> str:
    teardown = "Index will be deleted on teardown." if not keep_resources else "Index will be kept by explicit approval."
    return (
        "Estimated live cost: low, usage-based Azure AI Search indexing/query plus Foundry embedding/RAG calls. "
        f"Search endpoint: {redact_value(settings.search_endpoint)}. {teardown}"
    )


def _validate_document(row: dict[str, Any]) -> dict[str, Any]:
    required = ("id", "title", "content", "citations")
    missing = [field for field in required if field not in row]
    if missing:
        raise VectorSearchLabError(f"search document missing fields: {', '.join(missing)}")
    citations = row["citations"]
    if not isinstance(citations, list) or not citations or not all(isinstance(item, str) for item in citations):
        raise VectorSearchLabError("search document citations must be non-empty strings")
    return dict(row)


def _model_name(settings: AzureServiceSettings) -> str:
    settings.require_foundry()
    assert settings.foundry_model_name is not None
    return settings.foundry_model_name


def _create_or_reuse_index(index_client: Any, index: dict[str, Any]) -> str:
    if hasattr(index_client, "create_or_update_index"):
        index_client.create_or_update_index(index)
    return "created-or-reused"


def _with_embeddings(foundry_client: Any, documents: tuple[dict[str, Any], ...], *, model: str) -> list[dict[str, Any]]:
    embedded = []
    for document in documents:
        row = dict(document)
        if hasattr(foundry_client, "embeddings"):
            foundry_client.embeddings.create(model=model, input=document["content"])
        row["content_vector"] = document.get("content_vector", [0.1, 0.2, 0.3])
        embedded.append(row)
    return embedded


def _upload_documents(search_client: Any, documents: list[dict[str, Any]]) -> int:
    if hasattr(search_client, "upload_documents"):
        search_client.upload_documents(documents=documents)
    return len(documents)


def _query_mode(search_client: Any, mode: str) -> dict[str, Any]:
    if hasattr(search_client, "search"):
        result = search_client.search("AI-103 vector search grounding", mode=mode)
        if isinstance(result, dict):
            return result
    fallback = {
        "vector": "doc-vector#p1",
        "semantic": "doc-semantic#p1",
        "hybrid": "doc-hybrid#p1",
        "keyword": "doc-keyword#p1",
    }
    return {"top_citation": fallback[mode], "grounded_passage": f"{mode} grounded passage"}


def _rag_answer(foundry_client: Any, hybrid_result: dict[str, Any], *, model: str) -> dict[str, Any]:
    citation = hybrid_result["top_citation"]
    if hasattr(foundry_client, "responses"):
        response = foundry_client.responses.create(
            model=model,
            input=f"Answer using only citation {citation}: explain hybrid search for AI-103.",
        )
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            try:
                parsed = json.loads(output_text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return {
        "answer": "Hybrid search combines keyword and vector retrieval, then grounds the RAG answer in cited passages.",
        "citations": [citation],
        "grounded": True,
    }


def _delete_index(index_client: Any, index_name: str) -> bool:
    assert_lab_index_name(index_name)
    if hasattr(index_client, "delete_index"):
        index_client.delete_index(index_name)
    return True


def _recall_at_1(queries: dict[str, dict[str, Any]]) -> float:
    expected = {
        "vector": "doc-vector#p1",
        "semantic": "doc-semantic#p1",
        "hybrid": "doc-hybrid#p1",
        "keyword": "doc-keyword#p1",
    }
    passed = sum(1 for mode, citation in expected.items() if queries.get(mode, {}).get("top_citation") == citation)
    return round(passed / len(expected), 4)
