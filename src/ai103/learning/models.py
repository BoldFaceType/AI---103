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


@dataclass(frozen=True)
class LearningItem:
    competency_id: str
    domain: str
    mastery: float
    confidence: float = 0.0
    spacing_stage: int = 0
    last_reviewed_on: date | None = None
    consecutive_failures: int = 0


@dataclass(frozen=True)
class PlannedTask:
    task_type: str
    competency_id: str
    domain: str
    reason: str
    due_on: date
    priority: float
    estimated_minutes: int

    @property
    def stable_id(self) -> str:
        return f"task-{self.task_type}-{self.competency_id}-{self.due_on:%Y%m%d}"

    def to_task_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "id": self.stable_id,
            "type": self.task_type,
            "objective_ids": [self.competency_id],
            "domain": self.domain,
            "estimated_minutes": self.estimated_minutes,
            "created_at": f"{self.due_on.isoformat()}T00:00:00Z",
            "source": "planner",
            "status": "open",
            "reason": self.reason,
        }
