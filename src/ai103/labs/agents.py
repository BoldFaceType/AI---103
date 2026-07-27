from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from .runner import LabRun, run_lab

Mode = Literal["offline", "live"]
MAX_STEPS = 8
MAX_TOKENS = 2000
MAX_LATENCY_MS = 5000
ALLOWED_TOOLS = {"lookup_objective", "query_lab_index", "request_human_approval", "summarize_trace"}
REQUIRED_FAILURE_CASES = {"tool_failure", "timeout", "refusal", "injection"}


class AgentLabError(ValueError):
    """Raised when agent lab output violates the guarded-agent contract."""


def run_agent_lab(
    *,
    root: Path,
    mode: Mode = "offline",
    fixture_path: Path | None = None,
    event_log_path: Path | None = None,
    event_id: str | None = None,
) -> LabRun:
    if mode != "offline":
        raise AgentLabError("agent labs require explicit live implementation in a later task; offline replay is the safe default")
    fixture = fixture_path or root / "fixtures" / "azure-responses" / "agents" / "LAB-AGENT-WORKFLOWS.offline.json"
    validate_agent_lab_output(json.loads(fixture.read_text(encoding="utf-8"))["responses"]["agents"])
    return run_lab("LAB-AGENT-WORKFLOWS", root=root, mode="offline", event_log_path=event_log_path, event_id=event_id)


def validate_agent_lab_output(agents: dict[str, Any]) -> None:
    _validate_tools(agents)
    _validate_single_agent(agents)
    _validate_retrieval_agent(agents)
    _validate_approval_workflow(agents)
    _validate_multi_agent(agents)
    _validate_failures(agents)
    _validate_evaluation(agents)


def validate_tool_call(call: dict[str, Any], tools: dict[str, dict[str, Any]], *, approved: bool = False) -> None:
    name = call.get("name")
    if name not in tools or name not in ALLOWED_TOOLS:
        raise AgentLabError(f"tool outside allowlist: {name}")
    args = call.get("args")
    output = call.get("output")
    if not isinstance(args, dict) or not isinstance(output, dict):
        raise AgentLabError("tool inputs and outputs must be objects")
    required_args = set(tools[name]["input_schema"].get("required", []))
    required_output = set(tools[name]["output_schema"].get("required", []))
    if not required_args <= set(args):
        raise AgentLabError(f"tool call missing required input fields: {name}")
    if not required_output <= set(output):
        raise AgentLabError(f"tool call missing required output fields: {name}")
    if call.get("destructive") or call.get("billable"):
        if not call.get("approval_required") or not approved:
            raise AgentLabError("destructive or billable tools require approval before execution")


def _validate_tools(agents: dict[str, Any]) -> None:
    tools = agents.get("tools")
    if not isinstance(tools, dict) or not tools:
        raise AgentLabError("agent lab requires tool definitions")
    for name, definition in tools.items():
        if name not in ALLOWED_TOOLS:
            raise AgentLabError(f"tool outside allowlist: {name}")
        if not isinstance(definition.get("input_schema"), dict) or not isinstance(definition.get("output_schema"), dict):
            raise AgentLabError(f"tool schemas are required: {name}")


def _validate_single_agent(agents: dict[str, Any]) -> None:
    single = agents.get("single_agent", {})
    for field in ("role", "goal", "memory", "tool_call"):
        if field not in single:
            raise AgentLabError(f"single agent missing {field}")
    validate_tool_call(single["tool_call"], agents["tools"])
    if not single["memory"].get("used"):
        raise AgentLabError("single agent must use memory")


def _validate_retrieval_agent(agents: dict[str, Any]) -> None:
    retrieval = agents.get("retrieval_agent", {})
    if retrieval.get("index_name") != "ai103-lab-vector-study":
        raise AgentLabError("retrieval agent must use the T24 lab search index")
    validate_tool_call(retrieval.get("tool_call", {}), agents["tools"])
    if not retrieval.get("citations"):
        raise AgentLabError("retrieval agent requires citations")


def _validate_approval_workflow(agents: dict[str, Any]) -> None:
    workflow = agents.get("approval_workflow", {})
    call = workflow.get("tool_call", {})
    validate_tool_call(call, agents["tools"], approved=bool(workflow.get("approved_before_execution")))


def _validate_multi_agent(agents: dict[str, Any]) -> None:
    handoffs = agents.get("multi_agent", {}).get("handoffs", [])
    traces = {event.get("trace_id") for event in agents.get("trace", []) if isinstance(event, dict)}
    if not handoffs:
        raise AgentLabError("multi-agent workflow requires handoffs")
    for handoff in handoffs:
        if not {"trace_id", "from", "to", "task", "result"} <= set(handoff):
            raise AgentLabError("multi-agent handoffs must include trace_id, from, to, task, and result")
        if handoff["trace_id"] not in traces:
            raise AgentLabError(f"handoff is not traceable: {handoff['trace_id']}")


def _validate_failures(agents: dict[str, Any]) -> None:
    failures = agents.get("failure_cases", {})
    missing = sorted(REQUIRED_FAILURE_CASES - set(failures))
    if missing:
        raise AgentLabError(f"offline fixture missing failure cases: {', '.join(missing)}")
    for name in REQUIRED_FAILURE_CASES:
        if not failures[name].get("handled"):
            raise AgentLabError(f"failure case is not handled: {name}")


def _validate_evaluation(agents: dict[str, Any]) -> None:
    evaluation = agents.get("evaluation", {})
    if evaluation.get("steps", MAX_STEPS + 1) > MAX_STEPS:
        raise AgentLabError("agent loop exceeded step limit")
    if evaluation.get("tokens", MAX_TOKENS + 1) > MAX_TOKENS:
        raise AgentLabError("agent loop exceeded token limit")
    if evaluation.get("latency_ms", MAX_LATENCY_MS + 1) > MAX_LATENCY_MS:
        raise AgentLabError("agent loop exceeded latency limit")
    if not evaluation.get("within_limits") or not evaluation.get("trace_complete") or not evaluation.get("safety_passed"):
        raise AgentLabError("agent evaluation must pass limits, tracing, and safety")

