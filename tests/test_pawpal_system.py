from datetime import date

import pytest

from pawpal_system import (
    CareTask,
    DailyConstraint,
    Owner,
    PawPalBrain,
    Pet,
    Scheduler,
    TaskFrequency,
)


def test_task_defaults_and_completion_status():
    t = CareTask(title="Feed", duration_minutes=5, priority="high", id="t1")
    assert t.frequency == TaskFrequency.once
    assert t.completed is False
    assert t.last_completed_day is None

    d = date(2026, 3, 30)
    t.mark_completed(day=d)
    assert t.completed is True
    assert t.last_completed_day == d

    t.mark_incomplete()
    assert t.completed is False


def test_pet_stores_details_and_tasks():
    pet = Pet(name="Mochi", species="cat", details={"age": 2, "breed": "DSH"})
    assert pet.details["age"] == 2

    t1 = CareTask(title="Play", duration_minutes=10, priority="medium", id="play")
    pet.add_task(t1)
    assert pet.get_task("play") is t1
    assert pet.list_tasks(include_completed=True) == [t1]


def test_task_completion_default_day_and_pet_filters_completed():
    pet = Pet(name="Mochi", species="cat")
    done = CareTask(title="Feed", duration_minutes=5, priority="high", id="t1")
    todo = CareTask(title="Brush", duration_minutes=5, priority="low", id="t2")

    pet.add_task(done)
    pet.add_task(todo)

    done.mark_completed()
    assert done.completed is True
    assert done.last_completed_day == date.today()

    assert [t.id for t in pet.list_tasks(include_completed=False)] == ["t2"]


def test_pet_add_task_rejects_duplicate_id():
    pet = Pet(name="Mochi", species="cat")
    pet.add_task(CareTask(title="Feed", duration_minutes=5, priority="high", id="t1"))

    with pytest.raises(ValueError):
        pet.add_task(CareTask(title="Feed again", duration_minutes=5, priority="high", id="t1"))


def test_brain_add_task_to_missing_pet_raises_keyerror():
    owner = Owner(name="Ahnaf")
    brain = PawPalBrain(owner)

    with pytest.raises(KeyError):
        brain.add_task_to_pet("Nope", CareTask(title="Feed", duration_minutes=5, priority="high", id="t1"))


def test_owner_add_pet_rejects_duplicate_name():
    owner = Owner(name="Ahnaf")
    owner.add_pet(Pet(name="Mochi", species="cat"))

    with pytest.raises(ValueError):
        owner.add_pet(Pet(name="Mochi", species="cat"))


def test_owner_manages_multiple_pets_and_tasks():
    owner = Owner(name="Ahnaf")
    owner.add_pet(Pet(name="Mochi", species="cat"))
    owner.add_pet(Pet(name="Boba", species="dog"))

    brain = PawPalBrain(owner)
    brain.add_task_to_pet("Mochi", CareTask(title="Feed", duration_minutes=5, priority="high", id="m1"))
    brain.add_task_to_pet("Boba", CareTask(title="Walk", duration_minutes=20, priority="high", id="b1"))

    grouped = brain.tasks_grouped_by_pet()
    assert set(grouped.keys()) == {"Mochi", "Boba"}
    assert {t.id for t in brain.all_tasks()} == {"m1", "b1"}


def test_scheduler_builds_plan_and_skips_overflow():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)

    tasks = [
        CareTask(title="Groom", duration_minutes=30, priority="low", id="t3"),
        CareTask(title="Feed", duration_minutes=5, priority="high", id="t1"),
        CareTask(title="Play", duration_minutes=20, priority="medium", id="t2"),
    ]
    constraint = DailyConstraint(minutes_available=25, day=d)

    plan = Scheduler().build_plan(owner, pet, tasks, constraint)
    scheduled_ids = [item.task.id for item in plan.items]
    skipped_ids = [t.id for t in plan.skipped_tasks]

    assert scheduled_ids == ["t1", "t2"]
    assert skipped_ids == ["t3"]
    assert plan.total_minutes_used == 25
    assert plan.leftover_minutes == 0


def test_scheduler_filters_tasks_completed_today():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)

    done = CareTask(title="Feed", duration_minutes=5, priority="high", id="t1")
    done.mark_completed(day=d)
    todo = CareTask(title="Walk", duration_minutes=10, priority="high", id="t2")

    plan = Scheduler().build_plan(owner, pet, [done, todo], DailyConstraint(minutes_available=20, day=d))
    assert [item.task.id for item in plan.items] == ["t2"]


def test_scheduler_does_not_filter_completed_on_previous_day():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    today = date(2026, 3, 30)
    yesterday = date(2026, 3, 29)

    done_yesterday = CareTask(title="Feed", duration_minutes=5, priority="high", id="t1")
    done_yesterday.mark_completed(day=yesterday)

    plan = Scheduler().build_plan(
        owner,
        pet,
        [done_yesterday],
        DailyConstraint(minutes_available=10, day=today),
    )
    assert [item.task.id for item in plan.items] == ["t1"]

