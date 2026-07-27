from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import curriculum_audit
from ai103.assessment.models import QuestionRubric
from ai103.assessment.rubrics import score_question
from ai103.curriculum.lesson import parse_lesson, validate_lesson_file
from ai103.labs.agents import validate_agent_lab_output
from ai103.labs.grading import grade_lab_output, normalize_lab_output
from ai103.labs.registry import default_registry
from ai103.labs.vector_search import load_search_documents, validate_citations_trace_to_documents
from ai103.tutor.client import offline_tutor_response
from ai103.tutor.context import build_tutor_context, load_approved_sources
from ai103.tutor.schema import TutorValidationError, validate_tutor_output

TODAY = date(2026, 7, 27)
CURRICULUM = ROOT / "config" / "curriculum.ai103.json"
SOURCE_REGISTRY = ROOT / "content" / "sources" / "ai103-source-registry.json"
LESSON_ROOT = ROOT / "content" / "lessons" / "ai103"
ASSESSMENT_ROOT = ROOT / "content" / "assessments" / "ai103"
THRESHOLDS = ROOT / "evals" / "regression_thresholds.json"


@dataclass(frozen=True)
class EvalCase:
    id: str
    passed: bool
    metric: str
    detail: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic AI-103 offline eval suites.")
    parser.add_argument("--offline", action="store_true", help="Run CI-safe deterministic offline evals.")
    args = parser.parse_args(argv)
    if not args.offline:
        raise SystemExit("Error: only --offline evals are implemented in this CI-safe runner.")
    report = run_offline_evals()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


def run_offline_evals() -> dict[str, Any]:
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    suite_fns: dict[str, Callable[[], list[EvalCase]]] = {
        "curriculum": eval_curriculum,
        "lessons": eval_lessons,
        "assessments": eval_assessments,
        "tutor": eval_tutor,
        "labs": eval_labs,
        "retrieval_rag": eval_retrieval_rag,
        "agents": eval_agents,
        "live_fixture_metadata": eval_live_fixture_metadata,
    }
    suites: dict[str, Any] = {}
    failed_case_ids: list[str] = []
    for suite_name, suite_fn in suite_fns.items():
        cases = suite_fn()
        threshold = float(thresholds["suites"][suite_name]["threshold"])
        pass_rate = _pass_rate(cases)
        failed = [case.id for case in cases if not case.passed]
        failed_case_ids.extend(failed)
        suites[suite_name] = {
            "metric": thresholds["suites"][suite_name]["metric"],
            "threshold": threshold,
            "pass_rate": pass_rate,
            "passed": pass_rate >= threshold,
            "failed_case_ids": failed,
            "cases": [case.__dict__ for case in cases],
        }
    return {
        "schema_version": 1,
        "mode": "offline",
        "ok": not failed_case_ids and all(suite["passed"] for suite in suites.values()),
        "failed_case_ids": failed_case_ids,
        "prohibited_gate": thresholds["prohibited_gate"],
        "suites": suites,
    }


def eval_curriculum() -> list[EvalCase]:
    errors, _report = curriculum_audit.audit(today=TODAY)
    source = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    curriculum = json.loads(CURRICULUM.read_text(encoding="utf-8"))
    return [
        EvalCase("curriculum.coverage_and_freshness", not errors, "audit_errors", "; ".join(errors) or "audit passed"),
        EvalCase(
            "curriculum.source_registry_match",
            curriculum["skills_measured_date"] == source["primary_source"]["skills_measured_date"],
            "skills_measured_date_match",
            source["primary_source"]["url"],
        ),
    ]


def eval_lessons() -> list[EvalCase]:
    cases: list[EvalCase] = []
    for lesson_path in sorted(path for path in LESSON_ROOT.rglob("*.md") if path.name != "TEMPLATE.md"):
        lesson = parse_lesson(lesson_path)
        errors = validate_lesson_file(lesson_path, CURRICULUM, SOURCE_REGISTRY, today=TODAY)
        required_terms = {
            "retrieval": "Pre-Lesson Retrieval Questions",
            "spaced_practice": "Assessment Links",
            "interleaving": "Substantive Explanation",
            "elaboration": "Elaboration Prompts",
            "dual_coding": "Mermaid Diagram",
            "self_explanation": "Feynman Self-Explanation",
            "concrete_examples": "Concrete Azure Example",
            "zpd": "Guided Exercise with Fading Hints",
        }
        sections_ok = all(lesson.sections.get(section) for section in required_terms.values())
        cases.append(
            EvalCase(
                f"lesson.{lesson.metadata.get('lesson_id', lesson_path.stem)}.pedagogy",
                not errors and sections_ok,
                "lesson_contract_and_pedagogy",
                "; ".join(error.format() for error in errors) or "required pedagogy sections present",
            )
        )
    return cases


def eval_assessments() -> list[EvalCase]:
    cases: list[EvalCase] = []
    for path in sorted(ASSESSMENT_ROOT.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for question in data.get("questions", []):
            rubric = _rubric(question)
            answer = _passing_answer(question)
            first = score_question(rubric, answer)
            second = score_question(rubric, answer)
            cases.append(
                EvalCase(
                    f"assessment.{data['lesson_id']}.{question['id']}",
                    first == second and first.score >= 0.8,
                    "rubric_determinism",
                    f"score={first.score}",
                )
            )
    return cases


def eval_tutor() -> list[EvalCase]:
    cases: list[EvalCase] = []
    sources = load_approved_sources(ROOT)
    for raw in _jsonl(ROOT / "evals" / "tutor_cases.jsonl"):
        context = build_tutor_context(
            lesson_id=str(raw["lesson_id"]),
            competency_ids=[str(item) for item in raw["competency_ids"]],
            zpd_level=int(raw["zpd_level"]),
            learner_attempt=str(raw["learner_attempt"]),
            retrieved_text=str(raw["retrieved_text"]),
            approved_sources=sources,
        )
        try:
            candidate = offline_tutor_response(context)
            if "expected_rejection" in raw:
                candidate["citations"] = [{"title": "Unsupported", "url": "https://example.com/not-microsoft"}]
            output = validate_tutor_output(candidate, approved_sources=sources, allowed_lesson_ids=[context.lesson_id])
            passed = "expected_rejection" not in raw and output.hint_level <= min(context.zpd_level, 3)
            detail = "validated"
        except TutorValidationError as exc:
            passed = "expected_rejection" in raw and str(raw["expected_rejection"]) in str(exc)
            detail = str(exc)
        cases.append(EvalCase(f"tutor.{raw['id']}", passed, "grounding_hint_safety", detail))
    return cases


def eval_labs() -> list[EvalCase]:
    cases: list[EvalCase] = []
    for spec in default_registry(ROOT).values():
        offline_raw = json.loads(spec.fixture_path.read_text(encoding="utf-8"))
        live_path = spec.fixture_path.with_name(spec.fixture_path.name.replace(".offline.json", ".live-raw.json"))
        live_raw = json.loads(live_path.read_text(encoding="utf-8"))
        offline_result = grade_lab_output(spec, normalize_lab_output(offline_raw), mode="offline")
        live_result = grade_lab_output(spec, normalize_lab_output(live_raw), mode="live")
        cases.append(
            EvalCase(
                f"lab.{spec.lab_id}.offline_live_parity",
                offline_result["score"] >= spec.passing_score and live_result["score"] >= spec.passing_score,
                "offline_live_score_parity",
                f"offline={offline_result['score']} live={live_result['score']}",
            )
        )
    return cases


def eval_retrieval_rag() -> list[EvalCase]:
    raw = json.loads((ROOT / "fixtures" / "azure-responses" / "LAB-VECTOR-SEARCH.offline.json").read_text(encoding="utf-8"))
    vector_search = raw["responses"]["vector_search"]
    documents = load_search_documents(ROOT / "fixtures" / "search-documents")
    citations = {query["top_citation"] for query in vector_search["queries"].values()} | set(vector_search["rag"]["citations"])
    try:
        validate_citations_trace_to_documents(documents, citations)
        citations_ok = True
        detail = "citations trace to fixture documents"
    except ValueError as exc:
        citations_ok = False
        detail = str(exc)
    return [
        EvalCase("retrieval.fixed_query_recall", vector_search["evaluation"]["recall_at_1"] >= 1.0, "recall_at_1", "threshold=1.0"),
        EvalCase("rag.grounded_citations", citations_ok and vector_search["rag"]["grounded"], "groundedness", detail),
    ]


def eval_agents() -> list[EvalCase]:
    raw = json.loads((ROOT / "fixtures" / "azure-responses" / "agents" / "LAB-AGENT-WORKFLOWS.offline.json").read_text(encoding="utf-8"))
    agents = raw["responses"]["agents"]
    live_raw = json.loads((ROOT / "fixtures" / "azure-responses" / "agents" / "LAB-AGENT-WORKFLOWS.live-raw.json").read_text(encoding="utf-8"))
    live_agents = live_raw.get("validated_agents", live_raw["agents"])
    try:
        validate_agent_lab_output(agents)
        validate_agent_lab_output(live_agents)
        valid = True
        detail = "agent fixture valid"
    except ValueError as exc:
        valid = False
        detail = str(exc)
    evaluation = agents["evaluation"]
    cost = raw["cost_estimate"]["estimated"]
    return [
        EvalCase("agents.tool_approval_bounds_safety", valid, "guarded_agent_contract", detail),
        EvalCase("agents.latency_cost", evaluation["latency_ms"] <= 5000 and cost == 0.0, "latency_and_cost", f"latency={evaluation['latency_ms']} cost={cost}"),
    ]


def eval_live_fixture_metadata() -> list[EvalCase]:
    cases: list[EvalCase] = []
    for spec in default_registry(ROOT).values():
        live_path = spec.fixture_path.with_name(spec.fixture_path.name.replace(".offline.json", ".live-raw.json"))
        raw = json.loads(live_path.read_text(encoding="utf-8"))
        cost = raw.get("cost_estimate", {})
        service_or_model = json.dumps(raw, sort_keys=True)
        cases.append(
            EvalCase(
                f"live_metadata.{spec.lab_id}",
                isinstance(cost.get("estimated"), (int, float)) and bool(cost.get("currency")) and ("model" in service_or_model or "service" in service_or_model or cost["estimated"] == 0.0),
                "service_model_cost_metadata",
                json.dumps(cost, sort_keys=True),
            )
        )
    return cases


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _rubric(question: dict[str, Any]) -> QuestionRubric:
    return QuestionRubric(
        question_id=question["id"],
        kind=question["kind"],
        competency_id=question["competency_id"],
        points=float(question["points"]),
        answer_key=question.get("answer_key"),
        required_concepts=tuple(question.get("required_concepts", [])),
        required_substrings=tuple(question.get("required_substrings", [])),
        forbidden_substrings=tuple(question.get("forbidden_substrings", [])),
    )


def _passing_answer(question: dict[str, Any]) -> Any:
    if question["kind"] in {"multiple_choice", "multiple_select", "ordering", "matching", "structured_output"}:
        return question.get("answer_key")
    if question["kind"] == "concept_checklist":
        return " ".join(question.get("required_concepts", []))
    if question["kind"] == "code_check":
        return " ".join(question.get("required_substrings", []))
    return None


def _pass_rate(cases: list[EvalCase]) -> float:
    return round(sum(1 for case in cases if case.passed) / len(cases), 4) if cases else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
