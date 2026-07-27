from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.labs.runner import LabNetworkError, LabRunError, run_lab


def test_runner_defaults_to_offline_and_appends_passing_lab_event(tmp_path):
    event_log = tmp_path / "logs" / "events.ndjson"

    run = run_lab("LAB-SEARCH-RAG", root=ROOT, event_log_path=event_log, event_id="lab-pass-1")

    assert run.error is None
    assert run.result["mode"] == "offline"
    assert run.result["score"] == 1.0
    assert run.event is not None
    rows = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines()]
    assert rows == [run.event]
    assert rows[0]["type"] == "lab_completed"


def test_live_mode_cannot_run_implicitly():
    with pytest.raises(LabRunError, match="live mode requires an explicit live_adapter"):
        run_lab("LAB-SEARCH-RAG", root=ROOT, mode="live")


def test_live_adapter_output_is_normalized_before_event_creation(tmp_path):
    raw = json.loads((ROOT / "fixtures" / "azure-responses" / "LAB-SEARCH-RAG.live-raw.json").read_text(encoding="utf-8"))
    event_log = tmp_path / "logs" / "events.ndjson"

    run = run_lab("LAB-SEARCH-RAG", root=ROOT, mode="live", live_adapter=lambda _spec: raw, event_log_path=event_log, event_id="lab-live-1")

    assert run.result["mode"] == "live"
    assert run.result["score"] == 1.0
    assert run.event is not None
    assert json.loads(event_log.read_text(encoding="utf-8").splitlines()[0])["event_id"] == "lab-live-1"


def test_network_failure_does_not_corrupt_learner_state_and_surfaces_partial_resources(tmp_path):
    event_log = tmp_path / "logs" / "events.ndjson"

    def failing_adapter(_spec):
        raise LabNetworkError(
            "timeout contacting https://acct.services.ai.azure.com/api/projects/project-a with token abc",
            partial_resources=[
                "/subscriptions/00000000-1111-2222-3333-444444444444/resourceGroups/rg-ai103/providers/Microsoft.Search/searchServices/ai103-search"
            ],
        )

    run = run_lab("LAB-SEARCH-RAG", root=ROOT, mode="live", live_adapter=failing_adapter, event_log_path=event_log)

    assert run.event is None
    assert run.error is not None
    assert run.result["score"] == 0.0
    assert run.result["teardown_verified"] is False
    assert "partial_resources" in run.result
    assert "<redacted-id>" in run.result["partial_resources"][0]
    assert "token" not in run.result["checks"][0]["evidence"].casefold()
    assert not event_log.exists()


def test_non_passing_result_does_not_emit_lab_completed_event(tmp_path):
    raw = json.loads((ROOT / "fixtures" / "azure-responses" / "LAB-SEARCH-RAG.offline.json").read_text(encoding="utf-8"))
    raw["responses"]["storage"]["allow_blob_public_access"] = True
    raw["teardown_verified"] = False
    event_log = tmp_path / "logs" / "events.ndjson"

    run = run_lab("LAB-SEARCH-RAG", root=ROOT, mode="live", live_adapter=lambda _spec: raw, event_log_path=event_log)

    assert run.result["score"] < 0.8
    assert run.event is None
    assert not event_log.exists()
