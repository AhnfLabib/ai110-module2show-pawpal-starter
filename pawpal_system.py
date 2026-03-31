"""
PawPal+ logic layer — domain model and scheduling API.

Pure Python (no Streamlit): build objects here, call Scheduler.build_plan from the UI or tests.
See CLASS_DIAGRAM.md for the intended relationships and method contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any, Iterator, Optional, Sequence


def _hhmm_sort_key(value: str) -> tuple[int, int]:
    """
    Convert a 'HH:MM' string to a sortable (hour, minute) tuple.

    Invalid or missing values sort last.
    """
    if not value:
        return (99, 99)
    try:
        parts = value.strip().split(":")
        if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2:
            return (99, 99)
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return (99, 99)
        return (hour, minute)
    except (TypeError, ValueError):
        return (99, 99)


def _normalized_valid_hhmm(raw: str) -> str | None:
    """Return stripped 'HH:MM' if valid, else None (invalid/missing times are excluded)."""
    if raw is None:
        return None
    s = raw.strip()
    if _hhmm_sort_key(s) == (99, 99):
        return None
    return s


@dataclass
class Owner:
    name: str
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Owner name cannot be empty.")

    def add_pet(self, pet: Pet) -> None:
        if any(p.name == pet.name for p in self.pets):
            raise ValueError(f"Pet with name '{pet.name}' already exists for owner '{self.name}'.")
        self.pets.append(pet)

    def get_pet(self, name: str) -> Pet:
        for pet in self.pets:
            if pet.name == name:
                return pet
        raise KeyError(f"No pet named '{name}' for owner '{self.name}'.")

    def all_tasks(self) -> list[CareTask]:
        tasks: list[CareTask] = []
        for pet in self.pets:
            tasks.extend(pet.tasks)
        return tasks

    def __str__(self) -> str:
        return self.name


@dataclass
class Pet:
    name: str
    species: str
    details: dict[str, Any] = field(default_factory=dict)
    tasks: list[CareTask] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Pet name cannot be empty.")

    def add_task(self, task: CareTask) -> None:
        if task.id and any(t.id == task.id for t in self.tasks):
            raise ValueError(f"Task with id '{task.id}' already exists for pet '{self.name}'.")
        task.pet_name = self.name
        self.tasks.append(task)

    def get_task(self, task_id: str) -> CareTask:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise KeyError(f"No task with id '{task_id}' for pet '{self.name}'.")

    def list_tasks(self, *, include_completed: bool = True) -> list[CareTask]:
        if include_completed:
            return list(self.tasks)
        return [t for t in self.tasks if not t.completed]

    def remove_spawned_instance(self, original_task: CareTask, next_due: date) -> bool:
        """Remove the auto-spawned recurring instance that would have been created by mark_completed."""
        base_id = (original_task.id or "").strip()
        expected_id = f"{base_id}:{next_due.isoformat()}" if base_id else ""
        if expected_id:
            return self.remove_task(expected_id)
        for idx, candidate in enumerate(self.tasks):
            if (
                candidate.title == original_task.title
                and candidate.frequency == original_task.frequency
                and candidate.due_day == next_due
                and not candidate.completed
                and candidate.last_completed_day is None
            ):
                self.tasks.pop(idx)
                return True
        return False

    def remove_task(self, task_id: str) -> bool:
        for idx, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(idx)
                return True
        return False

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
    - time -> time (optional 'HH:MM' start time)
    - duration/time needed -> duration_minutes
    - frequency -> frequency
    - completion status -> completed (+ optional last_completed_day)
    """

    title: str
    duration_minutes: int
    priority: str
    time: str = ""
    # Lightweight provenance so conflicts can reference the correct pet when scheduling
    # across multiple pets. Auto-populated by Pet.add_task().
    pet_name: str = ""
    id: str = ""
    notes: str = ""
    frequency: TaskFrequency = TaskFrequency.once
    # Optional: when set, the task is considered "due" on/after this day (until completed).
    due_day: Optional[date] = None
    completed: bool = False
    last_completed_day: Optional[date] = None

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("Task title cannot be empty.")
        valid_priorities = {"low", "medium", "high"}
        if self.priority.lower() not in valid_priorities:
            raise ValueError(
                f"Unknown priority '{self.priority}'. Must be one of: {', '.join(sorted(valid_priorities))}."
            )

    def is_due_on(self, day: date) -> bool:
        """
        Return True if this task should be considered a scheduling candidate on `day`.

        Notes:
        - This intentionally implements the repo's current "completed today" behavior:
          tasks completed on previous days can be considered again (see tests).
        - `due_day` acts as a simple not-before gate: tasks with a future `due_day`
          are not candidates yet.
        """
        if self.due_day is not None and self.due_day > day:
            return False
        if self.completed and self.last_completed_day == day:
            return False
        return True

    def mark_completed(self, *, day: Optional[date] = None) -> Optional[CareTask]:
        self.completed = True
        completed_day = day or date.today()
        self.last_completed_day = completed_day

        if self.frequency == TaskFrequency.daily:
            next_due = completed_day + timedelta(days=1)
            return self._spawn_next_instance(due_day=next_due)

        if self.frequency == TaskFrequency.weekly:
            next_due = completed_day + timedelta(days=7)
            return self._spawn_next_instance(due_day=next_due)

        return None

    def _spawn_next_instance(self, *, due_day: date) -> CareTask:
        base_id = self.id.strip()
        next_id = f"{base_id}:{due_day.isoformat()}" if base_id else ""
        return CareTask(
            id=next_id,
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            time=self.time,
            pet_name=self.pet_name,
            notes=self.notes,
            frequency=self.frequency,
            due_day=due_day,
            completed=False,
            last_completed_day=None,
        )

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

    def __post_init__(self) -> None:
        if self.minutes_available < 0:
            raise ValueError("minutes_available must be non-negative.")

    def __str__(self) -> str:
        return f"{self.day.isoformat()}: {self.minutes_available} min available"


@dataclass
class PlanItem:
    """
    One entry in a daily schedule.

    order_index: execution order in the plan (0-based), matching greedy pack sequence.
    start_minute_optional: reserved for future time-of-day scheduling; unused by current packer.
    """

    task: CareTask
    reason: str
    order_index: int
    start_minute_optional: Optional[int] = None


@dataclass
class DailyPlan:
    """Result of scheduling: ordered plan items, totals, skipped tasks, and non-fatal warnings."""
    items: list[PlanItem] = field(default_factory=list)
    total_minutes_used: int = 0
    leftover_minutes: int = 0
    skipped_tasks: list[CareTask] = field(default_factory=list)
    skip_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

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

    def preview(
        self,
        *,
        owner: Owner,
        pet: Pet,
        tasks: Sequence[CareTask],
        constraint: DailyConstraint,
    ) -> dict[str, Any]:
        """
        Non-mutating helper for UIs:
        - shows which tasks are considered "due" for the day,
        - shows the sorted candidate order,
        - estimates what would be skipped under the time budget.

        Returns a dict to keep the UI lightweight and avoid introducing new public dataclasses.
        """

        candidates = self._sort_candidates(list(tasks), constraint=constraint)
        filtered_out = [t for t in tasks if t not in candidates]

        selected, skipped, used = self._pack_into_budget(candidates, constraint.minutes_available)
        invalid_duration = [t for t in candidates if t.duration_minutes <= 0]
        skipped_for_budget = [t for t in skipped if t.duration_minutes > 0]

        return {
            "candidates": candidates,
            "filtered_out": filtered_out,
            "selected_preview": selected,
            "skipped_preview": skipped,
            "skipped_for_budget": skipped_for_budget,
            "invalid_duration": invalid_duration,
            "minutes_used_preview": used,
        }

    def build_plan(
        self,
        owner: Owner,
        pet: Pet,
        tasks: Sequence[CareTask],
        constraint: DailyConstraint,
    ) -> DailyPlan:
        candidates = self._sort_candidates(list(tasks), constraint=constraint)
        selected, skipped, used = self._pack_into_budget(candidates, constraint.minutes_available)

        items: list[PlanItem] = []
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

        skip_reasons = [
            self._explain_choice(
                task,
                {"selected": False, "owner": owner, "pet": pet, "constraint": constraint},
            )
            for task in skipped
        ]

        plan = DailyPlan(
            items=items,
            total_minutes_used=used,
            leftover_minutes=max(constraint.minutes_available - used, 0),
            skipped_tasks=list(skipped),
            skip_reasons=skip_reasons,
            warnings=self._detect_time_conflicts(items, default_pet_name=pet.name),
        )
        return plan

    def _detect_time_conflicts(self, items: Sequence[PlanItem], *, default_pet_name: str) -> list[str]:
        """
        Lightweight conflict detection:
        - If 2+ scheduled tasks share the same valid 'HH:MM' start time, emit a warning.
        - Never raises; only returns warning strings for display/logging.
        """
        by_time: dict[str, list[CareTask]] = {}
        for item in items:
            t = item.task
            key = _normalized_valid_hhmm(t.time)
            if key is None:
                continue
            by_time.setdefault(key, []).append(t)

        warnings: list[str] = []
        for hhmm, tasks_at_time in sorted(by_time.items(), key=lambda kv: _hhmm_sort_key(kv[0])):
            if len(tasks_at_time) < 2:
                continue
            pet_names = [(t.pet_name or default_pet_name).strip() or "Unknown pet" for t in tasks_at_time]
            same_pet = len(set(pet_names)) == 1

            task_labels = ", ".join([f"'{t.title}' ({(t.pet_name or default_pet_name).strip()})" for t in tasks_at_time])
            scope = "same pet" if same_pet else "different pets"
            warnings.append(
                f"Time conflict at {hhmm}: {len(tasks_at_time)} task(s) are scheduled at the same time ({scope}): {task_labels}."
            )

        return warnings

    def _sort_candidates(
        self,
        tasks: list[CareTask],
        *,
        constraint: DailyConstraint,
    ) -> list[CareTask]:
        """Order tasks before packing (e.g. by priority, preferences)."""
        candidates = [t for t in tasks if t.is_due_on(constraint.day)]

        # Sort key is ascending; use negative priority_score to put higher priorities first.
        def sort_key(t: CareTask) -> tuple[int, int, str]:
            return (-t.priority_score(), t.duration_minutes, t.title.lower())

        return sorted(candidates, key=sort_key)

    def _pack_into_budget(
        self, tasks: Sequence[CareTask], minutes: int
    ) -> tuple[list[CareTask], list[CareTask], int]:
        """Return (selected_in_order, skipped, total_minutes_used)."""
        selected: list[CareTask] = []
        skipped: list[CareTask] = []
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

    def _explain_choice(self, task: CareTask, context: dict[str, Any]) -> str:
        """Explain why a task was included or skipped."""
        selected = bool(context.get("selected", True))
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

    def pets(self) -> list[Pet]:
        return list(self.owner.pets)

    def tasks_for_pet(self, pet_name: str, *, include_completed: bool = True) -> list[CareTask]:
        return self.owner.get_pet(pet_name).list_tasks(include_completed=include_completed)

    def all_tasks(self, *, include_completed: bool = True) -> list[CareTask]:
        tasks: list[CareTask] = []
        for pet in self.owner.pets:
            tasks.extend(pet.list_tasks(include_completed=include_completed))
        return tasks

    def tasks_grouped_by_pet(self, *, include_completed: bool = True) -> dict[str, list[CareTask]]:
        return {pet.name: pet.list_tasks(include_completed=include_completed) for pet in self.owner.pets}

    def filter_tasks(
        self,
        *,
        completed: Optional[bool] = None,
        pet_name: Optional[str] = None,
        sort_by_time: bool = False,
    ) -> list[CareTask]:
        """
        Filter tasks by completion status and/or pet name.

        - completed=None returns both completed and incomplete
        - pet_name=None returns tasks across all pets
        - sort_by_time=True sorts by CareTask.time ('HH:MM') using a lambda key
        """
        include_completed = completed is not False
        if pet_name is None:
            tasks = self.all_tasks(include_completed=include_completed)
        else:
            tasks = self.tasks_for_pet(pet_name, include_completed=include_completed)
        if completed is True:
            tasks = [t for t in tasks if t.completed]

        if sort_by_time:
            tasks = sorted(tasks, key=lambda t: _hhmm_sort_key(t.time))

        return tasks


def sort_tasks_by_time(tasks: Sequence[CareTask]) -> list[CareTask]:
    """
    Convenience helper: sort tasks by their `time` field ('HH:MM').

    Uses a lambda key so plain string 'HH:MM' values sort chronologically.
    Invalid/missing times sort last.
    """
    return sorted(tasks, key=lambda t: _hhmm_sort_key(t.time))
