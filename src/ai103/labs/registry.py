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
        "LAB-MEDICAL-TEXT": LabSpec(
            lab_id="LAB-MEDICAL-TEXT",
            title="Synthetic clinical text extraction fixture",
            objective_ids=("IE-01", "IE-03", "TA-01", "PM-04"),
            fixture_path=root / "fixtures" / "azure-responses" / "LAB-MEDICAL-TEXT.offline.json",
            required_response_shapes=("medical_text",),
            checks=(
                LabCheckSpec(
                    id="source-redacted",
                    response="medical_text",
                    path=("redacted_markdown",),
                    expected="Synthetic clinical note: <redacted-synthetic-person> reports mild headache after screen-heavy study. No emergency signs reported.",
                    evidence_template="Medical source text was redacted into grounded markdown: {value}.",
                ),
                LabCheckSpec(
                    id="pii-redaction-detected",
                    response="medical_text",
                    path=("pii", "0", "redacted"),
                    expected=True,
                    evidence_template="Synthetic PII redaction status was {value}.",
                ),
                LabCheckSpec(
                    id="entity-extracted",
                    response="medical_text",
                    path=("entities", "0", "text"),
                    expected="headache",
                    evidence_template="Medical entity extraction found expected entity: {value}.",
                ),
                LabCheckSpec(
                    id="topic-extracted",
                    response="medical_text",
                    path=("topics", "0"),
                    expected="triage",
                    evidence_template="Topic extraction included expected topic: {value}.",
                ),
                LabCheckSpec(
                    id="structured-field-severity",
                    response="medical_text",
                    path=("structured_fields", "severity"),
                    expected="mild",
                    evidence_template="Structured severity field normalized to {value}.",
                ),
                LabCheckSpec(
                    id="summary-grounded",
                    response="medical_text",
                    path=("summary",),
                    expected="Synthetic note describes mild headache after screen-heavy study with no emergency signs.",
                    evidence_template="Grounded summary was produced: {value}.",
                ),
                LabCheckSpec(
                    id="tone-safety-checked",
                    response="medical_text",
                    path=("tone_safety", "urgent_risk"),
                    expected=False,
                    evidence_template="Tone and safety urgent-risk status was {value}.",
                ),
                LabCheckSpec(
                    id="domain-concept-extracted",
                    response="medical_text",
                    path=("domain_concepts", "0"),
                    expected="PII redaction",
                    evidence_template="Domain concept extraction included {value}.",
                ),
                LabCheckSpec(
                    id="service-comparison-included",
                    response="medical_text",
                    path=("service_comparison", "content_understanding"),
                    expected="layout and structured fields",
                    evidence_template="Service comparison cited Content Understanding role: {value}.",
                ),
                LabCheckSpec(
                    id="approved-service-metadata",
                    response="medical_text",
                    path=("model_metadata", "services", "0"),
                    expected="Azure AI Language",
                    evidence_template="Approved service metadata included {value}.",
                ),
            ),
        ),
        "LAB-VECTOR-SEARCH": LabSpec(
            lab_id="LAB-VECTOR-SEARCH",
            title="Azure vector, semantic, hybrid, keyword, and RAG search fixture",
            objective_ids=("GA-02", "IE-02", "IE-04"),
            fixture_path=root / "fixtures" / "azure-responses" / "LAB-VECTOR-SEARCH.offline.json",
            required_response_shapes=("vector_search",),
            checks=(
                LabCheckSpec(
                    id="index-namespaced",
                    response="vector_search",
                    path=("index", "name"),
                    expected="ai103-lab-vector-study",
                    evidence_template="Lab index used safe namespace: {value}.",
                ),
                LabCheckSpec(
                    id="documents-ingested",
                    response="vector_search",
                    path=("ingestion", "document_count"),
                    expected=3,
                    evidence_template="Search ingestion loaded {value} sample documents.",
                ),
                LabCheckSpec(
                    id="embeddings-generated-through-foundry",
                    response="vector_search",
                    path=("embeddings", "provider"),
                    expected="Azure AI Foundry",
                    evidence_template="Embeddings provider was {value}.",
                ),
                LabCheckSpec(
                    id="vector-query-cited",
                    response="vector_search",
                    path=("queries", "vector", "top_citation"),
                    expected="doc-vector#p1",
                    evidence_template="Vector query top citation was {value}.",
                ),
                LabCheckSpec(
                    id="semantic-query-cited",
                    response="vector_search",
                    path=("queries", "semantic", "top_citation"),
                    expected="doc-semantic#p1",
                    evidence_template="Semantic query top citation was {value}.",
                ),
                LabCheckSpec(
                    id="hybrid-query-cited",
                    response="vector_search",
                    path=("queries", "hybrid", "top_citation"),
                    expected="doc-hybrid#p1",
                    evidence_template="Hybrid query top citation was {value}.",
                ),
                LabCheckSpec(
                    id="keyword-query-cited",
                    response="vector_search",
                    path=("queries", "keyword", "top_citation"),
                    expected="doc-keyword#p1",
                    evidence_template="Keyword query top citation was {value}.",
                ),
                LabCheckSpec(
                    id="recall-meets-threshold",
                    response="vector_search",
                    path=("evaluation", "recall_at_1"),
                    expected=1.0,
                    evidence_template="Fixed query set recall@1 was {value}.",
                ),
                LabCheckSpec(
                    id="rag-grounded",
                    response="vector_search",
                    path=("rag", "grounded"),
                    expected=True,
                    evidence_template="RAG answer groundedness was {value}.",
                ),
                LabCheckSpec(
                    id="rag-citation-traceable",
                    response="vector_search",
                    path=("rag", "citations", "0"),
                    expected="doc-hybrid#p1",
                    evidence_template="RAG citation traced to fixture document: {value}.",
                ),
                LabCheckSpec(
                    id="teardown-deleted-index",
                    response="vector_search",
                    path=("teardown", "deleted_index"),
                    expected=True,
                    evidence_template="Lab index deletion status was {value}.",
                ),
            ),
        ),
        "LAB-AGENT-WORKFLOWS": LabSpec(
            lab_id="LAB-AGENT-WORKFLOWS",
            title="Guarded agent, tool, memory, and multi-agent workflows",
            objective_ids=("GA-01", "GA-03", "GA-04", "PM-04"),
            fixture_path=root / "fixtures" / "azure-responses" / "agents" / "LAB-AGENT-WORKFLOWS.offline.json",
            required_response_shapes=("agents",),
            checks=(
                LabCheckSpec(
                    id="single-agent-tool-memory",
                    response="agents",
                    path=("single_agent", "memory", "used"),
                    expected=True,
                    evidence_template="Single agent used role, goal, memory, and function tool: {value}.",
                ),
                LabCheckSpec(
                    id="retrieval-agent-index",
                    response="agents",
                    path=("retrieval_agent", "index_name"),
                    expected="ai103-lab-vector-study",
                    evidence_template="Retrieval agent used lab index: {value}.",
                ),
                LabCheckSpec(
                    id="approval-gate-enforced",
                    response="agents",
                    path=("approval_workflow", "approved_before_execution"),
                    expected=True,
                    evidence_template="Semiautonomous approval gate status was {value}.",
                ),
                LabCheckSpec(
                    id="multi-agent-handoff-traceable",
                    response="agents",
                    path=("multi_agent", "handoffs", "0", "trace_id"),
                    expected="trace-handoff-1",
                    evidence_template="Multi-agent handoff trace id was {value}.",
                ),
                LabCheckSpec(
                    id="tool-failure-covered",
                    response="agents",
                    path=("failure_cases", "tool_failure", "handled"),
                    expected=True,
                    evidence_template="Tool failure handling status was {value}.",
                ),
                LabCheckSpec(
                    id="timeout-covered",
                    response="agents",
                    path=("failure_cases", "timeout", "handled"),
                    expected=True,
                    evidence_template="Timeout handling status was {value}.",
                ),
                LabCheckSpec(
                    id="refusal-covered",
                    response="agents",
                    path=("failure_cases", "refusal", "handled"),
                    expected=True,
                    evidence_template="Refusal handling status was {value}.",
                ),
                LabCheckSpec(
                    id="injection-covered",
                    response="agents",
                    path=("failure_cases", "injection", "handled"),
                    expected=True,
                    evidence_template="Prompt injection handling status was {value}.",
                ),
                LabCheckSpec(
                    id="bounds-enforced",
                    response="agents",
                    path=("evaluation", "within_limits"),
                    expected=True,
                    evidence_template="Step, token, and latency bounds status was {value}.",
                ),
                LabCheckSpec(
                    id="tracing-present",
                    response="agents",
                    path=("evaluation", "trace_complete"),
                    expected=True,
                    evidence_template="Agent trace completeness status was {value}.",
                ),
                LabCheckSpec(
                    id="safety-evaluated",
                    response="agents",
                    path=("evaluation", "safety_passed"),
                    expected=True,
                    evidence_template="Agent safety evaluation status was {value}.",
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
