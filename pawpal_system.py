"""
PawPal+ logic layer — domain model and scheduling API.

Pure Python (no Streamlit): build objects here, call Scheduler.build_plan from the UI or tests.
See CLASS_DIAGRAM.md for the intended relationships and method contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterator, List, Optional


@dataclass
class Owner:
    name: str
    preferences: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return self.name


@dataclass
class Pet:
    name: str
    species: str

    def __str__(self) -> str:
        return f"{self.name} ({self.species})"


@dataclass(order=False)
class CareTask:
    title: str
    duration_minutes: int
    priority: str
    id: str = ""
    notes: str = ""

    def priority_score(self) -> int:
        # Default mapping; extend with Owner.preferences when scheduling behavior is implemented.
        order = {"low": 1, "medium": 2, "high": 3}
        return order.get(self.priority.lower(), 0)

    def __lt__(self, other: CareTask) -> bool:
        if not isinstance(other, CareTask):
            return NotImplemented
        if self.priority_score() != other.priority_score():
            return self.priority_score() < other.priority_score()
        return self.title < other.title


@dataclass
class DailyConstraint:
    minutes_available: int
    day: date

    def __str__(self) -> str:
        return f"{self.day.isoformat()}: {self.minutes_available} min available"


@dataclass
class PlanItem:
    task: CareTask
    reason: str
    order_index: int
    start_minute_optional: Optional[int] = None


@dataclass
class DailyPlan:
    items: List[PlanItem] = field(default_factory=list)
    total_minutes_used: int = 0
    leftover_minutes: int = 0
    skipped_tasks: List[CareTask] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Scheduled {len(self.items)} task(s), "
            f"{self.total_minutes_used} min used, "
            f"{self.leftover_minutes} min remaining.",
        ]
        if self.skipped_tasks:
            lines.append(f"Skipped {len(self.skipped_tasks)} task(s) (e.g. time budget).")
        return " ".join(lines)

    def iter_with_reasons(self) -> Iterator[tuple[CareTask, str]]:
        for item in sorted(self.items, key=lambda i: i.order_index):
            yield item.task, item.reason


class Scheduler:
    """
    Produces a DailyPlan from owner context, pet, tasks, and a daily time budget.
    """

    def build_plan(
        self,
        owner: Owner,
        pet: Pet,
        tasks: List[CareTask],
        constraint: DailyConstraint,
    ) -> DailyPlan:
        raise NotImplementedError(
            "Orchestrate _sort_candidates, _pack_into_budget, and skipped_tasks / PlanItems."
        )

    def _sort_candidates(self, tasks: List[CareTask]) -> List[CareTask]:
        """Order tasks before packing (e.g. by priority, preferences)."""
        raise NotImplementedError

    def _pack_into_budget(
        self, tasks: List[CareTask], minutes: int
    ) -> tuple[List[CareTask], List[CareTask], int]:
        """Return (selected_in_order, skipped, total_minutes_used)."""
        raise NotImplementedError

    def _explain_choice(self, task: CareTask, context: Any) -> str:
        """Explain why a task was included or skipped."""
        raise NotImplementedError
