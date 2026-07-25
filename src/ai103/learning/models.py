from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

EvidenceOutcome = Literal["success", "failure"]
EvidenceMode = Literal["independent", "hinted"]


@dataclass(frozen=True)
class EvidenceEvent:
    event_id: str
    competency_id: str
    domain: str
    zpd_level: int
    outcome: EvidenceOutcome
    mode: EvidenceMode
    first_attempt: bool
    occurred_on: date
    unsafe_live_lab_behavior: bool = False
    model_feedback: dict[str, Any] = field(default_factory=dict)
    model_suggested_zpd_level: int | None = None

    @property
    def is_independent_success(self) -> bool:
        return self.outcome == "success" and self.mode == "independent" and self.first_attempt

    @property
    def is_hinted_success(self) -> bool:
        return self.outcome == "success" and self.mode == "hinted"

    @property
    def is_failure(self) -> bool:
        return self.outcome == "failure" or self.unsafe_live_lab_behavior


@dataclass(frozen=True)
class ScaffoldDecision:
    zpd_level: int
    scaffold: str
    hint_level: str
    reason: str
    due_review: bool


@dataclass(frozen=True)
class PedagogyConfig:
    techniques: tuple[str, ...]
    spacing_intervals_days: tuple[int, ...]
    promotion_independent_successes: int
    demotion_consecutive_failures: int
    stale_review_days: int
    zpd_levels: dict[int, dict[str, Any]]
