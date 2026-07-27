from __future__ import annotations

from pathlib import Path
from typing import Literal

from .runner import LabRun, run_lab

Mode = Literal["offline", "live"]


class GovernanceLabError(ValueError):
    """Raised when governance fixture controls are incomplete."""


def run_governance_lab(*, root: Path, mode: Mode = "offline", event_log_path: Path | None = None, event_id: str | None = None) -> LabRun:
    if mode != "offline":
        raise GovernanceLabError("governance live mode requires explicit approval for billable or policy-affecting actions")
    validate_governance_fixture(root / "fixtures" / "governance" / "README.md")
    return run_lab("LAB-GOVERNANCE-MONITORING", root=root, mode="offline", event_log_path=event_log_path, event_id=event_id)


def validate_governance_fixture(path: Path) -> None:
    text = path.read_text(encoding="utf-8").casefold()
    for phrase in ("blocked unsafe behavior", "approval controls", "quota", "cost", "resource health"):
        if phrase not in text:
            raise GovernanceLabError(f"governance fixture missing {phrase}")

