from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.assessment.engine import grade_assessment, mastery_evidence
from ai103.assessment.models import AssessmentAttempt, QuestionRubric
from ai103.assessment.rubrics import score_question


def attempt(answer, attempt_type="first", model_score=None) -> AssessmentAttempt:
    return AssessmentAttempt(
        attempt_id="attempt-1",
        question_id="q1",
        answer=answer,
        attempt_type=attempt_type,
        submitted_on=date(2026, 7, 25),
        model_coaching="Try reviewing the grounding checklist.",
        model_score=model_score,
    )


def rubric(kind, answer_key=None, **extra) -> QuestionRubric:
    return QuestionRubric(
        question_id="q1",
        kind=kind,
        competency_id="GA-01",
        points=1.0,
        answer_key=answer_key,
        **extra,
    )


def test_multiple_choice_scores_exact_normalized_answer():
    score = score_question(rubric("multiple_choice", "Azure AI Foundry"), " azure ai foundry ")

    assert score.score == 1.0
    assert score.passed is True


def test_multiple_select_answer_order_does_not_change_score():
    answer_key = ["retrieval", "tool", "memory"]

    first = score_question(rubric("multiple_select", answer_key), ["memory", "retrieval", "tool"])
    second = score_question(rubric("multiple_select", answer_key), ["tool", "memory", "retrieval"])

    assert first.score == second.score == 1.0


def test_ordering_requires_order():
    item = rubric("ordering", ["ingest", "index", "retrieve", "ground"])

    assert score_question(item, ["ingest", "index", "retrieve", "ground"]).score == 1.0
    assert score_question(item, ["index", "ingest", "retrieve", "ground"]).score == 0.0


def test_matching_ignores_object_order():
    item = rubric("matching", {"agent": "tool use", "rag": "grounding"})

    assert score_question(item, {"rag": "grounding", "agent": "tool use"}).score == 1.0


def test_exact_structured_output_ignores_json_key_order():
    item = rubric("structured_output", {"answer": {"service": "search", "mode": "hybrid"}, "ok": True})

    assert score_question(item, {"ok": True, "answer": {"mode": "hybrid", "service": "search"}}).score == 1.0


def test_code_checks_use_required_and_forbidden_substrings():
    item = rubric("code_check", required_substrings=("DefaultAzureCredential", "SearchClient"), forbidden_substrings=("api_key=",))

    assert score_question(item, "client = SearchClient(endpoint, index, DefaultAzureCredential())").score == 1.0
    assert score_question(item, "client = SearchClient(endpoint, index, api_key='secret')").score == 0.0


def test_concept_checklist_short_answer_scores_partial_credit():
    item = rubric("concept_checklist", required_concepts=("grounding", "citations", "retrieval"))

    score = score_question(item, "Grounding uses retrieval and source citations to reduce unsupported answers.")

    assert score.score == 1.0


def test_missing_and_malformed_answers_fail_safely():
    assert score_question(rubric("multiple_select", ["a"]), None).score == 0.0
    assert score_question(rubric("matching", {"a": "b"}), ["a", "b"]).score == 0.0
    assert score_question(rubric("structured_output", {"a": 1}), {"a": 2}).score == 0.0


def test_grade_assessment_separates_attempt_type_and_uses_practice_scale():
    result = grade_assessment([rubric("multiple_choice", "A")], attempt("A", attempt_type="hinted"))

    assert result.score == 1.0
    assert result.attempt_type == "hinted"
    assert result.score_scale == "practice"
    assert "Microsoft" not in result.score_scale


def test_llm_text_and_model_score_cannot_set_score_or_mastery():
    result = grade_assessment([rubric("multiple_choice", "A")], attempt("B", model_score=1.0))
    evidence = mastery_evidence(result, {"GA-01": 1.0}, today=date(2026, 7, 25))

    assert result.score == 0.0
    assert result.metadata["model_score_ignored"] is True
    assert result.coaching == "Try reviewing the grounding checklist."
    assert evidence[0].mastery_delta == 0.0


def test_mastery_uses_quality_recency_independence_and_weight():
    first = grade_assessment([rubric("multiple_choice", "A")], attempt("A", attempt_type="first"))
    hinted = grade_assessment([rubric("multiple_choice", "A")], attempt("A", attempt_type="hinted"))

    first_evidence = mastery_evidence(first, {"GA-01": 0.5}, today=date(2026, 7, 25))
    hinted_evidence = mastery_evidence(hinted, {"GA-01": 0.5}, today=date(2026, 7, 25), last_seen={"GA-01": date(2026, 6, 1)})

    assert first_evidence[0].mastery_delta == 0.05
    assert hinted_evidence[0].mastery_delta == 0.018
    assert hinted_evidence[0].independence_multiplier == 0.6
    assert hinted_evidence[0].recency_multiplier == 0.6
