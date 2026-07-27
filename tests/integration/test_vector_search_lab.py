from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.labs.vector_search import (
    VectorSearchLabError,
    assert_lab_index_name,
    build_index_schema,
    live_cost_notice,
    load_search_documents,
    run_vector_search_lab,
    safe_lab_index_name,
    validate_citations_trace_to_documents,
)
from ai103.services.settings import AzureServiceSettings


def valid_settings() -> AzureServiceSettings:
    return AzureServiceSettings(
        foundry_project_endpoint="https://acct.services.ai.azure.com/api/projects/project-a",
        foundry_model_name="vector-rag-deployment",
        search_endpoint="https://search-a.search.windows.net",
        search_index="study",
    )


def search_docs_dir() -> Path:
    return ROOT / "fixtures" / "search-documents"


def test_offline_vector_search_lab_passes_and_compares_all_retrieval_modes(tmp_path):
    event_log = tmp_path / "events.ndjson"

    run = run_vector_search_lab(search_docs_dir(), root=ROOT, mode="offline", event_log_path=event_log, event_id="vector-1")

    assert run.result["lab_id"] == "LAB-VECTOR-SEARCH"
    assert run.result["score"] == 1.0
    assert run.event is not None
    assert run.event["type"] == "lab_completed"
    check_ids = {check["id"] for check in run.result["checks"]}
    assert {"vector-query-cited", "semantic-query-cited", "hybrid-query-cited", "keyword-query-cited"} <= check_ids
    assert json.loads(event_log.read_text(encoding="utf-8").splitlines()[0]) == run.event


def test_index_names_cannot_collide_with_non_lab_indexes():
    assert safe_lab_index_name("Study Index") == "ai103-lab-vector-study-index"
    build_index_schema("ai103-lab-vector-study")

    with pytest.raises(VectorSearchLabError, match="non-lab search index"):
        assert_lab_index_name("production-index")
    with pytest.raises(VectorSearchLabError, match="non-lab search index"):
        build_index_schema("prod-customers")


def test_citations_must_trace_to_fixture_documents():
    documents = load_search_documents(search_docs_dir())
    validate_citations_trace_to_documents(documents, {"doc-vector#p1", "doc-hybrid#p1"})

    with pytest.raises(VectorSearchLabError, match="cannot be traced"):
        validate_citations_trace_to_documents(documents, {"missing#p1"})


class FakeIndexClient:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.deleted: list[str] = []

    def create_or_update_index(self, index: dict[str, Any]) -> None:
        self.created.append(index)

    def delete_index(self, index_name: str) -> None:
        self.deleted.append(index_name)


class FakeSearchClient:
    def __init__(self) -> None:
        self.uploads: list[list[dict[str, Any]]] = []
        self.searches: list[dict[str, Any]] = []

    def upload_documents(self, *, documents: list[dict[str, Any]]) -> None:
        self.uploads.append(documents)

    def search(self, search_text: str, **kwargs: Any) -> dict[str, Any]:
        mode = kwargs["mode"]
        self.searches.append({"search_text": search_text, "mode": mode})
        citations = {
            "vector": "doc-vector#p1",
            "semantic": "doc-semantic#p1",
            "hybrid": "doc-hybrid#p1",
            "keyword": "doc-keyword#p1",
        }
        return {"top_citation": citations[mode], "grounded_passage": f"{mode} grounded passage"}


class FakeEmbeddings:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        return object()


@dataclass
class FakeResponse:
    output_text: str


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        return FakeResponse(
            json.dumps(
                {
                    "answer": "Hybrid search combines keyword and vector retrieval and cites grounded passages.",
                    "citations": ["doc-hybrid#p1"],
                    "grounded": True,
                }
            )
        )


class FakeFoundryClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddings()
        self.responses = FakeResponses()


def test_live_vector_search_lab_verifies_ingestion_query_rag_and_teardown():
    index_client = FakeIndexClient()
    search_client = FakeSearchClient()
    foundry_client = FakeFoundryClient()

    run = run_vector_search_lab(
        search_docs_dir(),
        root=ROOT,
        mode="live",
        settings=valid_settings(),
        index_client=index_client,
        search_client=search_client,
        foundry_client=foundry_client,
    )

    assert run.result["score"] == 1.0
    assert index_client.created[0]["name"] == "ai103-lab-vector-study"
    assert index_client.deleted == ["ai103-lab-vector-study"]
    assert len(search_client.uploads[0]) == 3
    assert {call["mode"] for call in search_client.searches} == {"vector", "semantic", "hybrid", "keyword"}
    assert {call["model"] for call in foundry_client.embeddings.calls} == {"vector-rag-deployment"}
    assert foundry_client.responses.calls[0]["model"] == "vector-rag-deployment"
    assert run.result["resource_ids"] == ["https://<redacted-endpoint>", "ai103-lab-vector-study"]


def test_live_mode_requires_settings_and_keep_resources_is_explicit():
    with pytest.raises(VectorSearchLabError, match="requires AzureServiceSettings"):
        run_vector_search_lab(search_docs_dir(), root=ROOT, mode="live")

    assert "Index will be deleted on teardown" in live_cost_notice(valid_settings())
    assert "kept by explicit approval" in live_cost_notice(valid_settings(), keep_resources=True)


def test_vector_search_lab_script_offline_command_passes():
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "labs" / "Query_VectorSearch_Azure.py"),
            "--offline",
            str(search_docs_dir()),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["result"]["score"] == 1.0
    assert payload["event"]["type"] == "lab_completed"
    assert "rag-grounded" in {check["id"] for check in payload["result"]["checks"]}

