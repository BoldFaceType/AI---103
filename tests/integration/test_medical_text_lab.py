from __future__ import annotations

import json
import re
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

from ai103.labs.grading import grade_lab_output, normalize_lab_output
from ai103.labs.medical_text import MedicalTextLabError, discover_synthetic_documents, live_cost_notice, run_medical_text_lab
from ai103.labs.registry import get_lab_spec
from ai103.services.settings import AzureServiceSettings

REAL_PHI_PATTERNS = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b"),
)


def valid_settings() -> AzureServiceSettings:
    return AzureServiceSettings(
        foundry_project_endpoint="https://acct.services.ai.azure.com/api/projects/project-a",
        foundry_model_name="medical-text-deployment",
        content_understanding_endpoint="https://acct.services.ai.azure.com",
    )


def synthetic_dir() -> Path:
    return ROOT / "fixtures" / "medical-synthetic"


def test_synthetic_medical_fixtures_are_marked_and_contain_no_real_phi_patterns():
    documents = discover_synthetic_documents(synthetic_dir())

    assert documents
    for document in documents:
        text = document.read_text(encoding="utf-8")
        assert "SYNTHETIC TRAINING NOTE" in text
        assert not any(pattern.search(text) for pattern in REAL_PHI_PATTERNS)


def test_offline_medical_text_lab_passes_and_emits_redacted_event(tmp_path):
    event_log = tmp_path / "events.ndjson"

    run = run_medical_text_lab(synthetic_dir(), root=ROOT, mode="offline", event_log_path=event_log, event_id="medical-1")
    serialized = json.dumps({"result": run.result, "event": run.event}, sort_keys=True)

    assert run.result["lab_id"] == "LAB-MEDICAL-TEXT"
    assert run.result["score"] == 1.0
    assert run.event is not None
    assert run.event["type"] == "lab_completed"
    assert "IE-03" in run.event["objective_ids"]
    assert "Taylor Example" not in serialized
    assert "SYN-TRIAGE-001" not in serialized
    assert json.loads(event_log.read_text(encoding="utf-8").splitlines()[0]) == run.event


def test_medical_text_discovery_rejects_non_synthetic_or_unsupported_files(tmp_path):
    unsupported = tmp_path / "note.csv"
    unsupported.write_text("SYNTHETIC TRAINING NOTE", encoding="utf-8")
    with pytest.raises(MedicalTextLabError, match="unsupported document type"):
        discover_synthetic_documents(unsupported)

    unmarked = tmp_path / "note.txt"
    unmarked.write_text("Taylor has a headache.", encoding="utf-8")
    with pytest.raises(MedicalTextLabError, match="lacks synthetic marker"):
        discover_synthetic_documents(unmarked)


def test_live_raw_medical_text_fixture_normalizes_tolerated_variants():
    spec = get_lab_spec("LAB-MEDICAL-TEXT", ROOT)
    raw = json.loads((ROOT / "fixtures" / "azure-responses" / "LAB-MEDICAL-TEXT.live-raw.json").read_text(encoding="utf-8"))

    result = grade_lab_output(spec, normalize_lab_output(raw), mode="live")

    assert result["score"] == 1.0
    assert result["cost_estimate"] == {"currency": "USD", "estimated": 0.04}
    assert result["resource_ids"] == ["https://<redacted-endpoint>", "https://<redacted-endpoint>"]


@dataclass
class FakeResponse:
    output_text: str


class FakeResponses:
    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        return FakeResponse(json.dumps(self.output))


class FakeOpenAIClient:
    def __init__(self, output: dict[str, Any]) -> None:
        self.responses = FakeResponses(output)


class FakeContentUnderstandingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def begin_analyze(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        return object()


def live_fixture_output() -> dict[str, Any]:
    return json.loads((ROOT / "fixtures" / "azure-responses" / "LAB-MEDICAL-TEXT.offline.json").read_text(encoding="utf-8"))[
        "responses"
    ]["medical_text"]


def test_live_medical_text_lab_calls_approved_services_and_redacts_source_text():
    fake_openai = FakeOpenAIClient(live_fixture_output())
    fake_content = FakeContentUnderstandingClient()

    run = run_medical_text_lab(
        synthetic_dir(),
        root=ROOT,
        mode="live",
        settings=valid_settings(),
        responses_client=fake_openai,
        content_understanding_client=fake_content,
    )
    model_call = json.dumps(fake_openai.responses.calls, sort_keys=True)
    content_call = json.dumps(fake_content.calls, sort_keys=True)

    assert fake_openai.responses.calls[0]["model"] == "medical-text-deployment"
    assert fake_content.calls[0]["analyzer_id"] == "ai103-synthetic-clinical"
    assert "Taylor Example" not in model_call
    assert "SYN-TRIAGE-001" not in model_call
    assert "Taylor Example" not in content_call
    assert "SYN-TRIAGE-001" not in content_call
    assert run.result["score"] == 1.0
    assert run.result["cost_estimate"]["currency"] == "USD"


def test_live_mode_requires_settings_and_displays_cost_notice():
    with pytest.raises(MedicalTextLabError, match="requires AzureServiceSettings"):
        run_medical_text_lab(synthetic_dir(), root=ROOT, mode="live")

    notice = live_cost_notice(valid_settings())
    assert "Estimated live cost" in notice
    assert "https://acct.services.ai.azure.com" not in notice
    assert "https://<redacted-endpoint>" in notice


def test_medical_text_lab_script_offline_command_passes_without_source_text():
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "labs" / "Extract_MedicalText_Clinical.py"),
            "--offline",
            str(synthetic_dir()),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["result"]["score"] == 1.0
    assert payload["event"]["type"] == "lab_completed"
    assert "Taylor Example" not in completed.stdout
    assert "SYN-TRIAGE-001" not in completed.stdout

