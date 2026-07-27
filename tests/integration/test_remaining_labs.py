from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.labs.governance import GovernanceLabError, run_governance_lab, validate_governance_fixture
from ai103.labs.media_generation import MediaGenerationLabError, run_media_generation_lab, validate_media_generation_fixture
from ai103.labs.speech import SpeechLabError, run_speech_lab, validate_audio_fixture_metadata


def test_media_generation_lab_uses_offline_simulation_and_policy_labels(tmp_path):
    event_log = tmp_path / "events.ndjson"

    run = run_media_generation_lab(root=ROOT, event_log_path=event_log, event_id="media-1")

    assert run.result["lab_id"] == "LAB-MEDIA-GENERATION"
    assert run.result["score"] == 1.0
    assert run.event["type"] == "lab_completed"
    assert "media-policy-labeled" in {check["id"] for check in run.result["checks"]}
    validate_media_generation_fixture(ROOT / "fixtures" / "media-generation" / "README.md")


def test_speech_lab_has_consent_license_and_core_modalities():
    run = run_speech_lab(root=ROOT)

    assert run.result["lab_id"] == "LAB-SPEECH-TRANSLATION"
    assert run.result["score"] == 1.0
    check_ids = {check["id"] for check in run.result["checks"]}
    assert {"speech-to-text", "text-to-speech", "translation", "audio-consent-license"} <= check_ids
    validate_audio_fixture_metadata(ROOT / "fixtures" / "audio" / "README.md")


def test_governance_lab_blocks_unsafe_behavior_and_checks_operations():
    run = run_governance_lab(root=ROOT)

    assert run.result["lab_id"] == "LAB-GOVERNANCE-MONITORING"
    assert run.result["score"] == 1.0
    check_ids = {check["id"] for check in run.result["checks"]}
    assert {"unsafe-behavior-blocked", "approval-controls", "monitoring-trace", "quota-cost-health"} <= check_ids
    validate_governance_fixture(ROOT / "fixtures" / "governance" / "README.md")


def test_remaining_labs_block_live_mode_until_availability_quota_policy_and_approval_exist():
    with pytest.raises(MediaGenerationLabError, match="regional availability"):
        run_media_generation_lab(root=ROOT, mode="live")
    with pytest.raises(SpeechLabError, match="consent"):
        run_speech_lab(root=ROOT, mode="live")
    with pytest.raises(GovernanceLabError, match="explicit approval"):
        run_governance_lab(root=ROOT, mode="live")


def test_remaining_labs_fixtures_have_no_generated_binary_media_or_real_audio():
    assert sorted(path.name for path in (ROOT / "fixtures" / "media-generation").iterdir()) == ["README.md"]
    assert sorted(path.name for path in (ROOT / "fixtures" / "audio").iterdir()) == ["README.md"]
    assert "No real voice recording" in (ROOT / "fixtures" / "audio" / "README.md").read_text(encoding="utf-8")


def test_remaining_labs_script_offline_command_passes():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "labs" / "run_remaining_labs.py"), "--offline"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["media"]["result"]["score"] == 1.0
    assert payload["speech"]["result"]["score"] == 1.0
    assert payload["governance"]["result"]["score"] == 1.0
    assert payload["media"]["event"]["type"] == "lab_completed"
    assert payload["speech"]["event"]["type"] == "lab_completed"
    assert payload["governance"]["event"]["type"] == "lab_completed"

