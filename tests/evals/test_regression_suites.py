from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_evals


EXPECTED_SUITES = {
    "curriculum",
    "lessons",
    "assessments",
    "tutor",
    "labs",
    "retrieval_rag",
    "agents",
    "live_fixture_metadata",
}


def test_run_evals_offline_command_returns_deterministic_regression_report():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_evals.py"), "--offline"],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert report["ok"] is True
    assert report["mode"] == "offline"
    assert report["failed_case_ids"] == []
    assert set(report["suites"]) == EXPECTED_SUITES
    assert report["prohibited_gate"] == "LLM says pass"
    for suite in report["suites"].values():
        assert suite["threshold"] == 1.0
        assert suite["pass_rate"] == 1.0
        assert suite["failed_case_ids"] == []
        assert suite["cases"]


def test_eval_runner_identifies_exact_failed_case_ids(monkeypatch):
    monkeypatch.setattr(
        run_evals,
        "eval_curriculum",
        lambda: [run_evals.EvalCase("curriculum.synthetic_failure", False, "test_metric", "intentional")],
    )

    report = run_evals.run_offline_evals()

    assert report["ok"] is False
    assert "curriculum.synthetic_failure" in report["failed_case_ids"]
    assert report["suites"]["curriculum"]["failed_case_ids"] == ["curriculum.synthetic_failure"]


def test_eval_thresholds_are_explicit_and_do_not_use_llm_judgment():
    thresholds = json.loads((ROOT / "evals" / "regression_thresholds.json").read_text(encoding="utf-8"))

    assert thresholds["offline_required_pass_rate"] == 1.0
    assert thresholds["prohibited_gate"] == "LLM says pass"
    for name, suite in thresholds["suites"].items():
        assert name in EXPECTED_SUITES
        assert suite["threshold"] == 1.0
        assert "LLM" not in suite["metric"]
        assert "says" not in suite["metric"]


def test_eval_report_covers_required_manifest_domains():
    report = run_evals.run_offline_evals()

    assert any(case["id"] == "curriculum.coverage_and_freshness" for case in report["suites"]["curriculum"]["cases"])
    assert all(case["metric"] == "lesson_contract_and_pedagogy" for case in report["suites"]["lessons"]["cases"])
    assert all(case["metric"] == "rubric_determinism" for case in report["suites"]["assessments"]["cases"])
    assert any(case["id"] == "tutor.injection_ignored" for case in report["suites"]["tutor"]["cases"])
    assert all(case["metric"] == "offline_live_score_parity" for case in report["suites"]["labs"]["cases"])
    assert any(case["id"] == "rag.grounded_citations" for case in report["suites"]["retrieval_rag"]["cases"])
    assert any(case["id"] == "agents.tool_approval_bounds_safety" for case in report["suites"]["agents"]["cases"])
    assert all(case["metric"] == "service_model_cost_metadata" for case in report["suites"]["live_fixture_metadata"]["cases"])

