from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai103.labs.agents import AgentLabError, run_agent_lab, validate_agent_lab_output, validate_tool_call


def load_agents() -> dict[str, object]:
    return json.loads(
        (ROOT / "fixtures" / "azure-responses" / "agents" / "LAB-AGENT-WORKFLOWS.offline.json").read_text(encoding="utf-8")
    )["responses"]["agents"]


def test_agent_lab_offline_fixture_passes_and_emits_event(tmp_path):
    event_log = tmp_path / "events.ndjson"

    run = run_agent_lab(root=ROOT, mode="offline", event_log_path=event_log, event_id="agents-1")

    assert run.result["lab_id"] == "LAB-AGENT-WORKFLOWS"
    assert run.result["score"] == 1.0
    assert run.event is not None
    assert run.event["type"] == "lab_completed"
    check_ids = {check["id"] for check in run.result["checks"]}
    assert {
        "single-agent-tool-memory",
        "retrieval-agent-index",
        "approval-gate-enforced",
        "multi-agent-handoff-traceable",
        "tool-failure-covered",
        "timeout-covered",
        "refusal-covered",
        "injection-covered",
        "bounds-enforced",
        "tracing-present",
        "safety-evaluated",
    } <= check_ids
    assert json.loads(event_log.read_text(encoding="utf-8").splitlines()[0]) == run.event


def test_tool_inputs_outputs_validate_against_schema_and_allowlist():
    agents = load_agents()
    tools = agents["tools"]
    validate_tool_call(agents["single_agent"]["tool_call"], tools)

    bad_tool = deepcopy(agents["single_agent"]["tool_call"])
    bad_tool["name"] = "delete_everything"
    with pytest.raises(AgentLabError, match="outside allowlist"):
        validate_tool_call(bad_tool, tools)

    missing_arg = deepcopy(agents["single_agent"]["tool_call"])
    missing_arg["args"] = {}
    with pytest.raises(AgentLabError, match="missing required input"):
        validate_tool_call(missing_arg, tools)


def test_destructive_or_billable_tools_require_approval():
    agents = load_agents()
    call = deepcopy(agents["approval_workflow"]["tool_call"])

    with pytest.raises(AgentLabError, match="require approval"):
        validate_tool_call(call, agents["tools"], approved=False)

    validate_tool_call(call, agents["tools"], approved=True)


def test_agent_loops_have_step_token_and_latency_limits():
    agents = load_agents()
    validate_agent_lab_output(agents)

    too_many_steps = deepcopy(agents)
    too_many_steps["evaluation"]["steps"] = 9
    with pytest.raises(AgentLabError, match="step limit"):
        validate_agent_lab_output(too_many_steps)

    too_many_tokens = deepcopy(agents)
    too_many_tokens["evaluation"]["tokens"] = 2001
    with pytest.raises(AgentLabError, match="token limit"):
        validate_agent_lab_output(too_many_tokens)

    too_slow = deepcopy(agents)
    too_slow["evaluation"]["latency_ms"] = 5001
    with pytest.raises(AgentLabError, match="latency limit"):
        validate_agent_lab_output(too_slow)


def test_multi_agent_handoffs_are_traceable_and_replayable():
    agents = load_agents()
    validate_agent_lab_output(agents)

    broken = deepcopy(agents)
    broken["multi_agent"]["handoffs"][0]["trace_id"] = "missing-trace"
    with pytest.raises(AgentLabError, match="not traceable"):
        validate_agent_lab_output(broken)


def test_offline_fixture_covers_tool_failure_timeout_refusal_and_injection():
    agents = load_agents()
    assert {"tool_failure", "timeout", "refusal", "injection"} <= set(agents["failure_cases"])

    missing = deepcopy(agents)
    del missing["failure_cases"]["timeout"]
    with pytest.raises(AgentLabError, match="missing failure cases"):
        validate_agent_lab_output(missing)

    unhandled = deepcopy(agents)
    unhandled["failure_cases"]["injection"]["handled"] = False
    with pytest.raises(AgentLabError, match="not handled"):
        validate_agent_lab_output(unhandled)


def test_agent_lab_blocks_non_offline_mode_until_live_guard_exists():
    with pytest.raises(AgentLabError, match="offline replay is the safe default"):
        run_agent_lab(root=ROOT, mode="live")


def test_agent_lab_script_offline_command_passes():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "labs" / "run_agent_lab.py"), "--offline"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["result"]["score"] == 1.0
    assert payload["event"]["type"] == "lab_completed"
    assert "approval-gate-enforced" in {check["id"] for check in payload["result"]["checks"]}

