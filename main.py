from __future__ import annotations

from datetime import date

from pawpal_system import CareTask, DailyConstraint, Owner, PawPalBrain, Pet, Scheduler


def print_plan(*, label: str, plan) -> None:
    print()
    print(f"=== {label} ===")
    print(plan.summary())
    for task, reason in plan.iter_with_reasons():
        print(f"- {task.title} ({task.duration_minutes} min, {task.priority}): {reason}")
    if plan.skipped_tasks:
        print("Skipped:")
        for task in plan.skipped_tasks:
            print(f"- {task.title} ({task.duration_minutes} min, {task.priority})")


def main() -> None:
    owner = Owner(name="Ahnaf", preferences={})
    brain = PawPalBrain(owner)

    brain.add_pet(Pet(name="Mochi", species="Cat"))
    brain.add_pet(Pet(name="Buddy", species="Dog"))

    brain.add_task_to_pet(
        "Mochi",
        CareTask(
            id="mochi-feed",
            title="Feed Mochi",
            duration_minutes=5,
            priority="high",
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
        "Buddy",
        CareTask(
            id="buddy-walk",
            title="Walk Buddy",
            duration_minutes=25,
            priority="high",
        ),
    )
    brain.add_task_to_pet(
        "Buddy",
        CareTask(
            id="buddy-play",
            title="Play tug-of-war",
            duration_minutes=15,
            priority="low",
        ),
    )

    constraint = DailyConstraint(minutes_available=45, day=date.today())
    scheduler = Scheduler()

    print(f"Owner: {owner.name}")
    print(f"Today: {constraint.day.isoformat()} ({constraint.minutes_available} minutes available)")

    for pet in brain.pets():
        tasks = brain.tasks_for_pet(pet.name, include_completed=False)
        plan = scheduler.build_plan(owner, pet, tasks, constraint)
        print_plan(label=f"{pet.name}'s schedule", plan=plan)


if __name__ == "__main__":
    main()