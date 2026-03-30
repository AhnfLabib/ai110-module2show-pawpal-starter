from __future__ import annotations

from datetime import date, timedelta

from pawpal_system import CareTask, DailyConstraint, Owner, PawPalBrain, Pet, Scheduler, TaskFrequency


def print_task_list(*, label: str, tasks: list[CareTask]) -> None:
    print()
    print(f"--- {label} ({len(tasks)} task(s)) ---")
    for t in tasks:
        completed = "completed" if t.completed else "incomplete"
        hhmm = t.time.strip() if getattr(t, "time", "") else ""
        time_label = hhmm if hhmm else "(no-time)"
        due = t.due_day.isoformat() if getattr(t, "due_day", None) else "(no-due-day)"
        freq = getattr(t, "frequency", None)
        freq_label = freq.value if hasattr(freq, "value") else str(freq) if freq else "(no-frequency)"
        print(
            f"- {t.id or '(no-id)'} | {t.title} | {time_label} | {due} | {freq_label} | {t.duration_minutes} min | {t.priority} | {completed}"
        )


def print_plan(*, label: str, plan) -> None:
    print()
    print(f"=== {label} ===")
    print(plan.summary())
    if getattr(plan, "warnings", None):
        print("Warnings:")
        for w in plan.warnings:
            print(f"- {w}")
    for task, reason in plan.iter_with_reasons():
        print(f"- {task.title} ({task.duration_minutes} min, {task.priority}): {reason}")
    if plan.skipped_tasks:
        print("Skipped:")
        for task in plan.skipped_tasks:
            print(f"- {task.title} ({task.duration_minutes} min, {task.priority})")


def run_trial(*, title: str, brain: PawPalBrain, scheduler: Scheduler, owner: Owner, minutes: int, day: date) -> None:
    constraint = DailyConstraint(minutes_available=minutes, day=day)
    print()
    print("=" * 72)
    print(f"TRIAL: {title}")
    print(f"Day: {constraint.day.isoformat()} | Budget: {constraint.minutes_available} minutes")

    for pet in brain.pets():
        raw_tasks = brain.tasks_for_pet(pet.name, include_completed=True)
        visible_tasks = brain.tasks_for_pet(pet.name, include_completed=False)

        print_task_list(label=f"{pet.name} raw tasks (in insertion order)", tasks=raw_tasks)
        print_task_list(label=f"{pet.name} filtered tasks (include_completed=False)", tasks=visible_tasks)

        sorted_candidates = scheduler._sort_candidates(  # noqa: SLF001 (ok for a test ground script)
            list(raw_tasks),
            owner=owner,
            pet=pet,
            constraint=constraint,
        )
        print_task_list(label=f"{pet.name} scheduler-sorted candidates (after due/completed filters)", tasks=sorted_candidates)

        plan = scheduler.build_plan(owner, pet, raw_tasks, constraint)
        print_plan(label=f"{pet.name}'s schedule", plan=plan)


def main() -> None:
    owner = Owner(name="Ahnaf", preferences={})
    brain = PawPalBrain(owner)

    brain.add_pet(Pet(name="Mochi", species="Cat"))
    brain.add_pet(Pet(name="Buddy", species="Dog"))

    today = date.today()
    scheduler = Scheduler()

    # Add tasks intentionally out-of-order (mixed priority + duration),
    # and mark one as completed today to verify filtering works.
    brain.add_task_to_pet(
        "Mochi",
        CareTask(
            id="mochi-nails",
            title="Trim nails",
            duration_minutes=12,
            priority="low",
        ),
    )
    brain.add_task_to_pet(
        "Mochi",
        CareTask(
            id="mochi-litter",
            title="Clean litter box",
            duration_minutes=10,
            priority="medium",
        ),
    )
    brain.add_task_to_pet(
        "Mochi",
        CareTask(
            id="mochi-feed",
            title="Feed Mochi",
            duration_minutes=5,
            priority="high",
        ),
    )

    buddy_training = CareTask(
        id="buddy-training",
        title="Practice sit/stay training",
        duration_minutes=20,
        priority="medium",
    )
    buddy_training.mark_completed(day=today)

    brain.add_task_to_pet(
        "Buddy",
        CareTask(
            id="buddy-play",
            title="Play tug-of-war",
            time="09:00",
            duration_minutes=15,
            priority="low",
        ),
    )
    brain.add_task_to_pet("Buddy", buddy_training)
    brain.add_task_to_pet(
        "Buddy",
        CareTask(
            id="buddy-walk",
            title="Walk Buddy",
            time="09:00",
            duration_minutes=25,
            priority="high",
        ),
    )

    # Recurrence + due-day filter trial:
    # - Complete a daily task today -> spawn a new instance due tomorrow.
    # - Verify today's scheduler filters out the spawned instance (due_day in future).
    daily_vitamins = CareTask(
        id="buddy-vitamins",
        title="Give vitamins",
        time="08:30",
        duration_minutes=3,
        priority="high",
        frequency=TaskFrequency.daily,
    )
    brain.add_task_to_pet("Buddy", daily_vitamins)
    next_vitamins = daily_vitamins.mark_completed(day=today)
    if next_vitamins is not None:
        brain.add_task_to_pet("Buddy", next_vitamins)

    # Also add an explicitly future-due task (should be filtered out until due_day).
    brain.add_task_to_pet(
        "Mochi",
        CareTask(
            id="mochi-vet",
            title="Vet appointment (tomorrow)",
            time="10:00",
            duration_minutes=30,
            priority="high",
            due_day=today + timedelta(days=1),
        ),
    )

    print(f"Owner: {owner.name}")

    run_trial(
        title="Today (baseline budget) — checks priority sorting, completed-today filter, time conflict warnings, due_day filter",
        brain=brain,
        scheduler=scheduler,
        owner=owner,
        minutes=45,
        day=today,
    )
    run_trial(
        title="Today (tight budget) — checks greedy packing + skipped tasks",
        brain=brain,
        scheduler=scheduler,
        owner=owner,
        minutes=20,
        day=today,
    )
    run_trial(
        title="Tomorrow — checks due_day tasks become eligible",
        brain=brain,
        scheduler=scheduler,
        owner=owner,
        minutes=45,
        day=today + timedelta(days=1),
    )


if __name__ == "__main__":
    main()