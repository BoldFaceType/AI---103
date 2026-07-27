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

from ai103.labs.vision import VisionLabError, discover_image_inputs, live_cost_notice, run_vision_lab
from ai103.services.settings import AzureServiceSettings


def valid_settings() -> AzureServiceSettings:
    return AzureServiceSettings(
        foundry_project_endpoint="https://acct.services.ai.azure.com/api/projects/project-a",
        foundry_model_name="vision-deployment",
    )


def fixture_image() -> Path:
    return ROOT / "fixtures" / "images" / "ai103-vision-fixture.png"


def test_offline_vision_lab_passes_from_directory_and_emits_event(tmp_path):
    event_log = tmp_path / "events.ndjson"

    run = run_vision_lab(ROOT / "fixtures" / "images", root=ROOT, mode="offline", event_log_path=event_log, event_id="vision-1")

    assert run.result["lab_id"] == "LAB-VISION-ANALYSIS"
    assert run.result["mode"] == "offline"
    assert run.result["score"] == 1.0
    assert run.event is not None
    assert run.event["type"] == "lab_completed"
    assert "CV-01" in run.event["objective_ids"]
    assert json.loads(event_log.read_text(encoding="utf-8").splitlines()[0]) == run.event


def test_offline_vision_lab_accepts_single_file():
    run = run_vision_lab(fixture_image(), root=ROOT, mode="offline")

    assert run.result["score"] == 1.0
    assert all(check["passed"] for check in run.result["checks"])


def test_discovery_never_uploads_unsupported_files(tmp_path):
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("not an image", encoding="utf-8")

    with pytest.raises(VisionLabError, match="unsupported image type"):
        discover_image_inputs(unsupported)

    approved = tmp_path / "ok.png"
    approved.write_bytes(fixture_image().read_bytes())
    assert discover_image_inputs(tmp_path) == (approved.resolve(),)


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


def live_fixture_output() -> dict[str, Any]:
    return {
        "caption": "A learner reviews an Azure AI study diagram on a laptop.",
        "detailed_description": "The image shows a desk setup with a laptop displaying an AI-103 study diagram, notes, and a visible prompt-injection warning label.",
        "alt_text": "Laptop on a desk showing an AI-103 study diagram with notes and a prompt-injection warning.",
        "visual_qa": [{"question": "What study topic is visible?", "answer": "The visible study topic is AI-103 vision analysis."}],
        "objects": [{"name": "laptop", "region": {"x": 12, "y": 14, "width": 640, "height": 360}}],
        "regions": [{"label": "screen", "x": 32, "y": 24, "width": 590, "height": 300}],
        "safety": {"embedded_text_prompt_injection_detected": True, "unsafe_content_detected": False},
    }


def test_live_vision_lab_calls_foundry_responses_and_cites_metadata():
    fake_client = FakeOpenAIClient(live_fixture_output())

    run = run_vision_lab(fixture_image(), root=ROOT, mode="live", settings=valid_settings(), responses_client=fake_client)

    call = fake_client.responses.calls[0]
    assert call["model"] == "vision-deployment"
    assert "data:image/png;base64," in json.dumps(call)
    assert "notes.txt" not in json.dumps(call)
    assert run.result["score"] >= 0.8
    assert run.result["cost_estimate"]["currency"] == "USD"
    assert run.result["resource_ids"][0] == "https://<redacted-endpoint>"
    assert any(check["id"] == "service-metadata-cited" for check in run.result["checks"])


def test_live_mode_requires_explicit_settings_and_cost_notice():
    with pytest.raises(VisionLabError, match="requires AzureServiceSettings"):
        run_vision_lab(fixture_image(), root=ROOT, mode="live")

    notice = live_cost_notice(valid_settings())
    assert "Estimated live cost" in notice
    assert "00000000-1111-2222-3333-444444444444" not in notice


def test_vision_lab_script_offline_command_passes():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "labs" / "Create_VisionAnalysis_WSL.py"), "--offline", str(ROOT / "fixtures" / "images")],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["result"]["score"] == 1.0
    assert payload["event"]["type"] == "lab_completed"
    assert "unsafe-content-checked" in {check["id"] for check in payload["result"]["checks"]}
