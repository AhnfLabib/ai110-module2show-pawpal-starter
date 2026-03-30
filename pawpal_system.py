"""
PawPal+ logic layer — domain model and scheduling API.

Pure Python (no Streamlit): build objects here, call Scheduler.build_plan from the UI or tests.
See CLASS_DIAGRAM.md for the intended relationships and method contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple


@dataclass
class Owner:
    name: str
    preferences: dict = field(default_factory=dict)
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        if any(p.name == pet.name for p in self.pets):
            raise ValueError(f"Pet with name '{pet.name}' already exists for owner '{self.name}'.")
        self.pets.append(pet)

    def get_pet(self, name: str) -> Pet:
        for pet in self.pets:
            if pet.name == name:
                return pet
        raise KeyError(f"No pet named '{name}' for owner '{self.name}'.")

    def all_tasks(self) -> List[CareTask]:
        tasks: List[CareTask] = []
        for pet in self.pets:
            tasks.extend(list(pet.tasks))
        return tasks

    def __str__(self) -> str:
        return self.name


@dataclass
class Pet:
    name: str
    species: str
    details: Dict[str, Any] = field(default_factory=dict)
    tasks: List[CareTask] = field(default_factory=list)

    def add_task(self, task: CareTask) -> None:
        if task.id and any(t.id == task.id for t in self.tasks):
            raise ValueError(f"Task with id '{task.id}' already exists for pet '{self.name}'.")
        self.tasks.append(task)

    def get_task(self, task_id: str) -> CareTask:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise KeyError(f"No task with id '{task_id}' for pet '{self.name}'.")

    def list_tasks(self, *, include_completed: bool = True) -> List[CareTask]:
        if include_completed:
            return list(self.tasks)
        return [t for t in self.tasks if not t.completed]

    def __str__(self) -> str:
        return f"{self.name} ({self.species})"


class TaskFrequency(str, Enum):
    once = "once"
    daily = "daily"
    weekly = "weekly"
    as_needed = "as_needed"


@dataclass(order=False)
class CareTask:
    """
    A single activity/task.

    Terminology mapping (for UI language):
    - description -> title (+ optional notes)
    - time -> duration_minutes
    - frequency -> frequency
    - completion status -> completed (+ optional last_completed_day)
    """

    title: str
    duration_minutes: int
    priority: str
    id: str = ""
    notes: str = ""
    frequency: TaskFrequency = TaskFrequency.once
    completed: bool = False
    last_completed_day: Optional[date] = None

    def mark_completed(self, *, day: Optional[date] = None) -> None:
        self.completed = True
        self.last_completed_day = day or date.today()

    def mark_incomplete(self) -> None:
        self.completed = False

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
        tasks: Sequence[CareTask],
        constraint: DailyConstraint,
    ) -> DailyPlan:
        candidates = self._sort_candidates(list(tasks), owner=owner, pet=pet, constraint=constraint)
        selected, skipped, used = self._pack_into_budget(candidates, constraint.minutes_available)

        items: List[PlanItem] = []
        for idx, task in enumerate(selected):
            items.append(
                PlanItem(
                    task=task,
                    reason=self._explain_choice(
                        task,
                        {
                            "selected": True,
                            "owner": owner,
                            "pet": pet,
                            "constraint": constraint,
                        },
                    ),
                    order_index=idx,
                )
            )

        plan = DailyPlan(
            items=items,
            total_minutes_used=used,
            leftover_minutes=max(constraint.minutes_available - used, 0),
            skipped_tasks=list(skipped),
        )
        return plan

    def _sort_candidates(
        self,
        tasks: List[CareTask],
        *,
        owner: Owner,
        pet: Pet,
        constraint: DailyConstraint,
    ) -> List[CareTask]:
        """Order tasks before packing (e.g. by priority, preferences)."""
        _ = (owner, pet)  # reserved for preference-aware sorting
        # Filter out tasks that are already completed for the constraint day (simple rule).
        filtered: List[CareTask] = []
        for t in tasks:
            if t.completed and t.last_completed_day == constraint.day:
                continue
            filtered.append(t)

        # We want highest priority and shortest duration first; invert duration component accordingly.
        # Use a key that sorts ascending; prioritize by negative priority_score.
        return sorted(
            filtered,
            key=lambda t: (-t.priority_score(), t.duration_minutes, t.title.lower()),
        )

    def _pack_into_budget(
        self, tasks: Sequence[CareTask], minutes: int
    ) -> tuple[List[CareTask], List[CareTask], int]:
        """Return (selected_in_order, skipped, total_minutes_used)."""
        selected: List[CareTask] = []
        skipped: List[CareTask] = []
        used = 0

        for task in tasks:
            if task.duration_minutes <= 0:
                skipped.append(task)
                continue
            if used + task.duration_minutes <= minutes:
                selected.append(task)
                used += task.duration_minutes
            else:
                skipped.append(task)

        return selected, skipped, used

    def _explain_choice(self, task: CareTask, context: Any) -> str:
        """Explain why a task was included or skipped."""
        selected = bool(getattr(context, "get", lambda _k, _d=None: None)("selected", True))  # type: ignore[misc]
        if selected:
            return (
                f"Included '{task.title}' because it is {task.priority.lower()} priority "
                f"and fits within today's time budget."
            )
        return (
            f"Skipped '{task.title}' because it did not fit within today's time budget "
            f"after scheduling higher-priority items."
        )


class PawPalBrain:
    """
    "Brain" that stores pets + tasks and provides cross-pet retrieval/organization.

    This is intentionally separate from the Scheduler so it can be used for:
    - CRUD of pets/tasks
    - aggregating tasks across multiple pets
    - selecting candidate tasks for scheduling
    """

    def __init__(self, owner: Owner):
        self.owner = owner

    def add_pet(self, pet: Pet) -> None:
        self.owner.add_pet(pet)

    def add_task_to_pet(self, pet_name: str, task: CareTask) -> None:
        self.owner.get_pet(pet_name).add_task(task)

    def pets(self) -> List[Pet]:
        return list(self.owner.pets)

    def tasks_for_pet(self, pet_name: str, *, include_completed: bool = True) -> List[CareTask]:
        return self.owner.get_pet(pet_name).list_tasks(include_completed=include_completed)

    def all_tasks(self, *, include_completed: bool = True) -> List[CareTask]:
        tasks: List[CareTask] = []
        for pet in self.owner.pets:
            tasks.extend(pet.list_tasks(include_completed=include_completed))
        return tasks

    def tasks_grouped_by_pet(self, *, include_completed: bool = True) -> Dict[str, List[CareTask]]:
        return {pet.name: pet.list_tasks(include_completed=include_completed) for pet in self.owner.pets}

