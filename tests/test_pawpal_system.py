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
    sort_tasks_by_time,
)


def test_task_defaults_and_completion_status():
    t = CareTask(title="Feed", duration_minutes=5, priority="high", id="t1")
    assert t.frequency == TaskFrequency.once
    assert t.due_day is None
    assert t.completed is False
    assert t.last_completed_day is None

    d = date(2026, 3, 30)
    spawned = t.mark_completed(day=d)
    assert t.completed is True
    assert t.last_completed_day == d
    assert spawned is None

    t.mark_incomplete()
    assert t.completed is False


def test_pet_stores_details_and_tasks():
    pet = Pet(name="Mochi", species="cat", details={"age": 2, "breed": "DSH"})
    assert pet.details["age"] == 2

    t1 = CareTask(title="Play", duration_minutes=10, priority="medium", id="play")
    pet.add_task(t1)
    assert pet.get_task("play") is t1
    assert pet.list_tasks(include_completed=True) == [t1]


def test_pet_remove_task_by_id():
    pet = Pet(name="Mochi", species="cat")
    pet.add_task(CareTask(title="Feed", duration_minutes=5, priority="high", id="t1"))
    assert pet.remove_task("t1") is True
    assert pet.tasks == []
    assert pet.remove_task("t1") is False


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


def test_as_needed_task_completion_does_not_spawn():
    d = date(2026, 3, 30)
    t = CareTask(
        title="Groom",
        duration_minutes=10,
        priority="medium",
        id="a1",
        frequency=TaskFrequency.as_needed,
    )
    spawned = t.mark_completed(day=d)
    assert spawned is None


def test_empty_tasks_list_produces_empty_plan():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)
    plan = Scheduler().build_plan(owner, pet, [], DailyConstraint(minutes_available=30, day=d))
    assert plan.items == []
    assert plan.total_minutes_used == 0
    assert plan.leftover_minutes == 30


def test_zero_minute_budget_schedules_nothing_with_positive_duration():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)
    tasks = [CareTask(title="Feed", duration_minutes=5, priority="high", id="t1")]
    plan = Scheduler().build_plan(owner, pet, tasks, DailyConstraint(minutes_available=0, day=d))
    assert plan.items == []
    assert plan.skipped_tasks == tasks


def test_negative_duration_task_is_skipped_not_selected():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)
    bad = CareTask(title="Bad", duration_minutes=-5, priority="high", id="b1")
    good = CareTask(title="Good", duration_minutes=5, priority="low", id="g1")
    plan = Scheduler().build_plan(owner, pet, [bad, good], DailyConstraint(minutes_available=10, day=d))
    assert [item.task.id for item in plan.items] == ["g1"]
    assert bad in plan.skipped_tasks


def test_daily_constraint_rejects_negative_minutes():
    with pytest.raises(ValueError, match="non-negative"):
        DailyConstraint(minutes_available=-1, day=date.today())


def test_daily_task_completion_spawns_next_instance_with_due_date():
    d = date(2026, 3, 30)
    t = CareTask(
        title="Feed",
        duration_minutes=5,
        priority="high",
        id="t1",
        frequency=TaskFrequency.daily,
    )

    spawned = t.mark_completed(day=d)
    assert spawned is not None
    assert spawned.completed is False
    assert spawned.last_completed_day is None
    assert spawned.frequency == TaskFrequency.daily
    assert spawned.due_day == date(2026, 3, 31)
    assert spawned.id == "t1:2026-03-31"


def test_weekly_task_completion_spawns_next_instance_with_due_date():
    d = date(2026, 3, 30)
    t = CareTask(
        title="Deep clean bowl",
        duration_minutes=10,
        priority="medium",
        id="w1",
        frequency=TaskFrequency.weekly,
    )

    spawned = t.mark_completed(day=d)
    assert spawned is not None
    assert spawned.due_day == date(2026, 4, 6)
    assert spawned.id == "w1:2026-04-06"


def test_scheduler_filters_out_tasks_not_due_yet():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)

    future = CareTask(
        title="Future task",
        duration_minutes=5,
        priority="high",
        id="f1",
        frequency=TaskFrequency.once,
        due_day=date(2026, 3, 31),
    )
    due_today = CareTask(
        title="Due today",
        duration_minutes=5,
        priority="high",
        id="t1",
        frequency=TaskFrequency.once,
        due_day=d,
    )

    plan = Scheduler().build_plan(owner, pet, [future, due_today], DailyConstraint(minutes_available=30, day=d))
    assert [item.task.id for item in plan.items] == ["t1"]

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


def test_sort_tasks_by_time_orders_valid_times_and_puts_invalid_last():
    tasks = [
        CareTask(title="No time", duration_minutes=5, priority="low", id="t0", time=""),
        CareTask(title="Morning", duration_minutes=5, priority="low", id="t1", time="09:00"),
        CareTask(title="Bad format", duration_minutes=5, priority="low", id="t2", time="9am"),
        CareTask(title="Earlier", duration_minutes=5, priority="low", id="t3", time="07:30"),
        CareTask(title="Impossible", duration_minutes=5, priority="low", id="t4", time="24:00"),
        CareTask(title="Later", duration_minutes=5, priority="low", id="t5", time="18:15"),
    ]

    sorted_ids = [t.id for t in sort_tasks_by_time(tasks)]

    # Valid 'HH:MM' values should be in chronological order.
    assert sorted_ids[:3] == ["t3", "t1", "t5"]
    # Invalid/missing times should be pushed to the end (order among them is not important here).
    assert set(sorted_ids[3:]) == {"t0", "t2", "t4"}


def test_daily_recurrence_spawn_is_not_due_until_next_day_for_scheduler():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    scheduler = Scheduler()
    d = date(2026, 3, 30)

    t = CareTask(
        title="Feed",
        duration_minutes=5,
        priority="high",
        id="t1",
        frequency=TaskFrequency.daily,
    )
    spawned = t.mark_completed(day=d)
    assert spawned is not None

    # Original task is completed today => excluded today.
    plan_today = scheduler.build_plan(owner, pet, [t, spawned], DailyConstraint(minutes_available=30, day=d))
    assert [item.task.id for item in plan_today.items] == []

    # Spawned task becomes due tomorrow => included tomorrow.
    tomorrow = date(2026, 3, 31)
    plan_tomorrow = scheduler.build_plan(owner, pet, [t, spawned], DailyConstraint(minutes_available=30, day=tomorrow))
    # Note: current logic allows tasks completed on previous days to be scheduled again.
    # If the caller keeps the original task AND the spawned next instance, both can appear.
    assert [item.task.id for item in plan_tomorrow.items] == ["t1", "t1:2026-03-31"]


def test_scheduler_emits_warning_for_same_time_conflict_and_ignores_invalid_times():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)

    # Both should be selected and both share a valid HH:MM time => warning.
    t1 = CareTask(title="Feed", duration_minutes=5, priority="high", id="t1", time="09:00")
    t2 = CareTask(title="Meds", duration_minutes=5, priority="high", id="t2", time="09:00")
    # Invalid time should not be considered for conflicts.
    t3 = CareTask(title="Bad time", duration_minutes=5, priority="high", id="t3", time="9am")

    plan = Scheduler().build_plan(owner, pet, [t1, t2, t3], DailyConstraint(minutes_available=20, day=d))
    assert {item.task.id for item in plan.items} == {"t1", "t2", "t3"}
    assert any("Time conflict at 09:00" in w for w in plan.warnings)
    assert not any("Time conflict at 9am" in w for w in plan.warnings)


def test_scheduler_time_conflict_normalizes_whitespace_in_time_strings():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)
    t1 = CareTask(title="Feed", duration_minutes=5, priority="high", id="t1", time="09:00 ")
    t2 = CareTask(title="Meds", duration_minutes=5, priority="high", id="t2", time=" 09:00")
    plan = Scheduler().build_plan(owner, pet, [t1, t2], DailyConstraint(minutes_available=20, day=d))
    assert len(plan.items) == 2
    assert any("Time conflict at 09:00" in w for w in plan.warnings)


def test_brain_filter_tasks_skips_completed_when_requested():
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    owner.add_pet(pet)
    brain = PawPalBrain(owner)
    done = CareTask(title="Feed", duration_minutes=5, priority="high", id="d1")
    done.mark_completed(day=date(2026, 3, 30))
    todo = CareTask(title="Walk", duration_minutes=10, priority="high", id="w1")
    pet.add_task(done)
    pet.add_task(todo)
    incomplete = brain.filter_tasks(completed=False, pet_name="Mochi")
    assert [t.id for t in incomplete] == ["w1"]
    complete_only = brain.filter_tasks(completed=True, pet_name="Mochi")
    assert [t.id for t in complete_only] == ["d1"]


# --- Tests for code review coverage gaps ---


def test_normalized_valid_hhmm_handles_none_time():
    """Issue 1: _normalized_valid_hhmm must not crash when task.time is None."""
    from pawpal_system import _normalized_valid_hhmm

    assert _normalized_valid_hhmm(None) is None


def test_scheduler_handles_none_time_in_conflict_detection():
    """Issue 1 (end-to-end): scheduler should not crash when a task has time=None."""
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)
    t = CareTask(title="Feed", duration_minutes=5, priority="high", id="t1")
    t.time = None  # Explicitly set to None (bypasses dataclass default)
    plan = Scheduler().build_plan(owner, pet, [t], DailyConstraint(minutes_available=30, day=d))
    assert len(plan.items) == 1


def test_strict_hhmm_rejects_non_zero_padded_times():
    """Issue 2: Non-zero-padded times like '1:2' or '9:05' should be treated as invalid."""
    bad_times = ["1:2", "9:05", "12:5", "1:30"]
    for time_str in bad_times:
        t = CareTask(title="Test", duration_minutes=5, priority="high", id="t", time=time_str)
        assert sort_tasks_by_time([t])[0].time == time_str  # still in list
        from pawpal_system import _hhmm_sort_key
        assert _hhmm_sort_key(time_str) == (99, 99), f"{time_str} should be invalid"


def test_empty_owner_name_raises():
    """Issue 5: Owner name cannot be empty."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Owner(name="")
    with pytest.raises(ValueError, match="cannot be empty"):
        Owner(name="   ")


def test_empty_pet_name_raises():
    """Issue 5: Pet name cannot be empty."""
    with pytest.raises(ValueError, match="cannot be empty"):
        Pet(name="", species="cat")
    with pytest.raises(ValueError, match="cannot be empty"):
        Pet(name="   ", species="dog")


def test_empty_task_title_raises():
    """Issue 6: Task title cannot be empty."""
    with pytest.raises(ValueError, match="title cannot be empty"):
        CareTask(title="", duration_minutes=5, priority="high")
    with pytest.raises(ValueError, match="title cannot be empty"):
        CareTask(title="   ", duration_minutes=5, priority="high")


def test_unknown_priority_raises():
    """Issue 10: Unknown priority values should raise ValueError."""
    with pytest.raises(ValueError, match="Unknown priority"):
        CareTask(title="Walk", duration_minutes=10, priority="urgent")
    with pytest.raises(ValueError, match="Unknown priority"):
        CareTask(title="Walk", duration_minutes=10, priority="critical")


def test_mark_completed_on_as_needed_task_returns_none():
    """Coverage gap: as_needed tasks should not spawn a new instance."""
    t = CareTask(
        title="Nail trim",
        duration_minutes=15,
        priority="low",
        id="an1",
        frequency=TaskFrequency.as_needed,
    )
    assert t.mark_completed(day=date(2026, 3, 30)) is None
    assert t.completed is True


def test_filter_tasks_all_parameter_combinations():
    """Coverage gap: exercise all filter_tasks parameter combos."""
    owner = Owner(name="Ahnaf")
    mochi = Pet(name="Mochi", species="cat")
    boba = Pet(name="Boba", species="dog")
    owner.add_pet(mochi)
    owner.add_pet(boba)
    brain = PawPalBrain(owner)

    done_m = CareTask(title="Feed Mochi", duration_minutes=5, priority="high", id="dm")
    done_m.mark_completed(day=date(2026, 3, 30))
    mochi.add_task(done_m)

    todo_m = CareTask(title="Play Mochi", duration_minutes=10, priority="medium", id="tm")
    mochi.add_task(todo_m)

    todo_b = CareTask(title="Walk Boba", duration_minutes=20, priority="high", id="tb")
    boba.add_task(todo_b)

    # All tasks, no filter
    all_tasks = brain.filter_tasks()
    assert len(all_tasks) == 3

    # Completed only, all pets
    completed_all = brain.filter_tasks(completed=True)
    assert [t.id for t in completed_all] == ["dm"]

    # Incomplete only, all pets
    incomplete_all = brain.filter_tasks(completed=False)
    assert {t.id for t in incomplete_all} == {"tm", "tb"}

    # Specific pet, all statuses
    mochi_all = brain.filter_tasks(pet_name="Mochi")
    assert len(mochi_all) == 2

    # Specific pet, completed only
    mochi_done = brain.filter_tasks(completed=True, pet_name="Mochi")
    assert [t.id for t in mochi_done] == ["dm"]

    # Specific pet, incomplete only
    mochi_todo = brain.filter_tasks(completed=False, pet_name="Mochi")
    assert [t.id for t in mochi_todo] == ["tm"]

    # Sort by time
    sorted_tasks = brain.filter_tasks(sort_by_time=True)
    assert len(sorted_tasks) == 3


def test_build_plan_with_zero_tasks_returns_clean_empty_plan():
    """Coverage gap: build_plan with empty task list."""
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)
    plan = Scheduler().build_plan(owner, pet, [], DailyConstraint(minutes_available=30, day=d))
    assert plan.items == []
    assert plan.skipped_tasks == []
    assert plan.skip_reasons == []
    assert plan.warnings == []
    assert plan.total_minutes_used == 0
    assert plan.leftover_minutes == 30


def test_pet_add_task_always_overwrites_pet_name():
    """Issue 4: pet_name should always be set to the owning pet."""
    pet = Pet(name="Mochi", species="cat")
    task = CareTask(title="Feed", duration_minutes=5, priority="high", id="t1", pet_name="Buddy")
    pet.add_task(task)
    assert task.pet_name == "Mochi"


def test_remove_spawned_instance_by_id():
    """Issue 11: Pet.remove_spawned_instance should find and remove the next instance."""
    pet = Pet(name="Mochi", species="cat")
    original = CareTask(
        title="Feed", duration_minutes=5, priority="high", id="t1", frequency=TaskFrequency.daily
    )
    pet.add_task(original)
    spawned = original.mark_completed(day=date(2026, 3, 30))
    pet.add_task(spawned)
    assert len(pet.tasks) == 2

    removed = pet.remove_spawned_instance(original, date(2026, 3, 31))
    assert removed is True
    assert len(pet.tasks) == 1
    assert pet.tasks[0].id == "t1"


def test_remove_spawned_instance_by_fallback_when_no_id():
    """Issue 11: fallback removal when original task has no stable id."""
    pet = Pet(name="Mochi", species="cat")
    original = CareTask(
        title="Feed", duration_minutes=5, priority="high", id="", frequency=TaskFrequency.daily
    )
    pet.add_task(original)
    spawned = original.mark_completed(day=date(2026, 3, 30))
    pet.add_task(spawned)
    assert len(pet.tasks) == 2

    removed = pet.remove_spawned_instance(original, date(2026, 3, 31))
    assert removed is True
    assert len(pet.tasks) == 1


def test_build_plan_generates_skip_reasons():
    """Issue 8: skipped tasks should have corresponding skip reasons."""
    owner = Owner(name="Ahnaf")
    pet = Pet(name="Mochi", species="cat")
    d = date(2026, 3, 30)
    tasks = [
        CareTask(title="Feed", duration_minutes=5, priority="high", id="t1"),
        CareTask(title="Groom", duration_minutes=30, priority="low", id="t2"),
    ]
    plan = Scheduler().build_plan(owner, pet, tasks, DailyConstraint(minutes_available=10, day=d))
    assert len(plan.items) == 1
    assert len(plan.skipped_tasks) == 1
    assert len(plan.skip_reasons) == 1
    assert "Skipped" in plan.skip_reasons[0]
    assert "Groom" in plan.skip_reasons[0]