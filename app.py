import streamlit as st

from datetime import date
from datetime import timedelta
from uuid import uuid4

from pawpal_system import CareTask, DailyConstraint, Owner, Pet, Scheduler, TaskFrequency

SCOPE_ACTIVE_PET = "Active pet"
SCOPE_ALL_PETS = "All pets"

SPECIES_OPTIONS = ["dog", "cat", "other"]


def _fmt_dash(value: str | None) -> str:
    s = (value or "").strip()
    return s if s else "—"


def _fmt_due(due: date | None) -> str:
    return due.isoformat() if due else "—"


def _task_frequency_label(task: CareTask) -> str:
    f = task.frequency
    return f.value if hasattr(f, "value") else str(f)


def _priority_badge_md(priority: str) -> str:
    pl = (priority or "").lower()
    if pl == "high":
        return ":red[**High**]"
    if pl == "medium":
        return ":orange[**Medium**]"
    if pl == "low":
        return ":green[**Low**]"
    return f"**{priority}**"


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.caption("Plan pet care under a time budget — priorities, optional times, recurring tasks, and plain-English reasons. See README.md for the full scenario and success criteria.")

with st.expander("Project scenario (summary)", expanded=False):
    st.markdown(
        """
- Track care tasks with duration, priority, and optional start time (`HH:MM`).
- Set how many minutes you have today; the scheduler builds a **DailyPlan** and explains inclusions and skips.
- Recurring **daily** / **weekly** tasks spawn the next instance when you mark them completed today.

Details, setup, and tests: **README.md**.
"""
    )


def get_or_init_owner(*, owner_name: str) -> Owner:
    owner_name = owner_name.strip()
    if not owner_name:
        raise ValueError("Owner name cannot be empty.")
    existing = st.session_state.get("owner")
    if isinstance(existing, Owner):
        existing.name = owner_name
        return existing
    owner = Owner(name=owner_name)
    st.session_state.owner = owner
    return owner


def get_or_init_pet(*, owner: Owner, pet_name: str, species: str) -> Pet:
    for p in owner.pets:
        if p.name == pet_name:
            p.species = species
            return p
    pet = Pet(name=pet_name, species=species)
    owner.add_pet(pet)
    return pet


st.subheader("Owner & pets")
owner_name = st.text_input("Owner name", value="Jordan", help="Updates the `Owner` used for scheduling and session state.")
owner_name_clean = owner_name.strip()
if not owner_name_clean:
    st.error("Owner name cannot be empty.")
    existing_owner = st.session_state.get("owner")
    if isinstance(existing_owner, Owner):
        owner = existing_owner
    else:
        st.stop()
else:
    owner = get_or_init_owner(owner_name=owner_name_clean)

with st.form("add_pet_form", clear_on_submit=False):
    c1, c2 = st.columns(2)
    with c1:
        new_pet_name = st.text_input("Pet name (add to your household)", value="Mochi").strip()
    with c2:
        new_species = st.selectbox("Species", SPECIES_OPTIONS, index=0)
    add_pet_submitted = st.form_submit_button("Add pet")

if add_pet_submitted:
    if not new_pet_name:
        st.error("Enter a pet name.")
    else:
        try:
            get_or_init_pet(owner=owner, pet_name=new_pet_name, species=new_species)
            st.success(f"Added pet: {new_pet_name} ({new_species})")
        except ValueError as e:
            st.error(str(e))

pet_names = [p.name for p in owner.pets]
if not pet_names:
    st.info("Add at least one pet above to create tasks and generate a schedule.")
    selected_pet_name: str | None = None
else:
    if "selected_pet_name" not in st.session_state or st.session_state.selected_pet_name not in pet_names:
        st.session_state.selected_pet_name = pet_names[0]
    selected_pet_name = st.selectbox(
        "Pet you’re planning for (tasks below)",
        options=pet_names,
        key="selected_pet_name",
    )

active_pet: Pet | None = None
if selected_pet_name:
    try:
        active_pet = owner.get_pet(selected_pet_name)
    except KeyError:
        st.error(f"Pet '{selected_pet_name}' no longer exists.")
        active_pet = None

st.divider()
st.subheader("Care tasks")

if not active_pet:
    st.info("Add a pet first, then add tasks here.")
else:
    st.markdown(f"##### Tasks for {active_pet.name}")

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        task_time = st.text_input("Start time (optional, HH:MM)", value="").strip()

    col4, col5 = st.columns(2)
    with col4:
        frequency = st.selectbox("Frequency", ["once", "daily", "weekly", "as_needed"], index=0)
    with col5:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    task_notes = st.text_input("Notes (optional)", value="")

    if st.button("Add task", type="primary"):
        task_title_stripped = str(task_title).strip()
        if not task_title_stripped:
            st.error("Task title cannot be empty.")
        else:
            try:
                active_pet.add_task(
                    CareTask(
                        id=str(uuid4()),
                        title=task_title_stripped,
                        duration_minutes=int(duration),
                        priority=str(priority),
                        time=str(task_time),
                        notes=str(task_notes),
                        frequency=TaskFrequency(str(frequency)),
                    )
                )
                st.success(f"Added task to {active_pet.name}.")
            except ValueError as e:
                st.error(str(e))

    if active_pet.tasks:
        st.caption("Check **Done today** to record completion (daily/weekly tasks spawn the next due instance automatically).")

        today = date.today()
        for idx, t in enumerate(active_pet.list_tasks(include_completed=True)):
            with st.container(border=True):
                completed_today_key = f"completed_today::{active_pet.name}::{idx}"
                default_completed_today = bool(t.completed and t.last_completed_day == today)

                head_l, head_r = st.columns([0.22, 0.78])
                with head_l:
                    completed_today = st.checkbox(
                        "Done today",
                        key=completed_today_key,
                        value=default_completed_today,
                    )
                with head_r:
                    due = t.due_day
                    time_disp = _fmt_dash(t.time)
                    freq_disp = _task_frequency_label(t)
                    st.write(f"**{t.title}**")
                    st.markdown(
                        f"{_priority_badge_md(t.priority)} &nbsp;·&nbsp; **{t.duration_minutes} min** &nbsp;·&nbsp; "
                        f"Time **{time_disp}** &nbsp;·&nbsp; **{freq_disp}** &nbsp;·&nbsp; Due **{_fmt_due(due)}**"
                    )

                notes_text = (t.notes or "").strip()
                if notes_text:
                    with st.expander("Notes"):
                        st.write(notes_text)

            if completed_today and not default_completed_today:
                next_task = t.mark_completed(day=today)
                if next_task is not None:
                    try:
                        active_pet.add_task(next_task)
                    except ValueError as e:
                        st.warning(f"Could not schedule next instance: {e}")
                st.toast(f"Marked completed: {t.title}")

            if (not completed_today) and default_completed_today:
                freq = t.frequency
                next_due = None
                if freq == TaskFrequency.daily:
                    next_due = today + timedelta(days=1)
                elif freq == TaskFrequency.weekly:
                    next_due = today + timedelta(days=7)

                if next_due is not None:
                    active_pet.remove_spawned_instance(t, next_due)

                t.mark_incomplete()
                t.last_completed_day = None
                st.toast(f"Marked incomplete: {t.title}")

    else:
        st.info("No tasks yet. Add one above.")

st.divider()
st.subheader("Daily plan")
st.caption("Uses `Scheduler.preview` and `Scheduler.build_plan` with your time budget and today’s date.")

schedule_scope = st.radio(
    "Task set for scheduling",
    options=[SCOPE_ACTIVE_PET, SCOPE_ALL_PETS],
    index=0,
    horizontal=True,
    key="schedule_scope",
    help='"All pets" aggregates tasks across every pet for one combined plan (and cross-pet time warnings).',
)

minutes_available = st.number_input(
    "Minutes available today",
    min_value=5,
    max_value=24 * 60,
    value=60,
    step=5,
)

if st.button("Generate schedule"):
    if not owner.pets:
        st.error("Add at least one pet before generating a schedule.")
    elif schedule_scope == SCOPE_ACTIVE_PET and not active_pet:
        st.error("Select an active pet.")
    else:
        pet = active_pet if active_pet is not None else owner.pets[0]
        constraint = DailyConstraint(minutes_available=int(minutes_available), day=date.today())
        scheduler = Scheduler()

        if schedule_scope == SCOPE_ALL_PETS:
            all_tasks = owner.all_tasks()
        else:
            all_tasks = pet.list_tasks(include_completed=True)

        preview = scheduler.preview(owner=owner, pet=pet, tasks=all_tasks, constraint=constraint)

        candidates = list(preview.get("candidates", []))
        filtered_out = list(preview.get("filtered_out", []))
        skipped_for_budget = list(preview.get("skipped_for_budget", []))
        invalid_duration = list(preview.get("invalid_duration", []))

        if not candidates:
            st.error("No due tasks to schedule for today. Add tasks or adjust completion / due dates.")
            if filtered_out:
                st.warning("Some tasks were filtered out (not due or already completed for today).")
                st.table(
                    [
                        {
                            "title": t.title,
                            "priority": t.priority,
                            "duration_minutes": t.duration_minutes,
                            "time": t.time,
                            "due_day": t.due_day,
                            "completed": t.completed,
                        }
                        for t in filtered_out
                    ]
                )
        else:
            st.markdown("### Candidates (due today, scheduler order)")
            st.success(f"{len(candidates)} task(s) due today before packing.")

            st.table(
                [
                    {
                        "order": idx + 1,
                        "title": t.title,
                        "priority": t.priority,
                        "duration_minutes": t.duration_minutes,
                        "time": t.time,
                        "due_day": t.due_day,
                        "completed": t.completed,
                    }
                    for idx, t in enumerate(candidates)
                ]
            )

            if filtered_out:
                st.warning(
                    f"{len(filtered_out)} task(s) filtered out (not due yet, or already completed today)."
                )
                st.table(
                    [
                        {
                            "title": t.title,
                            "priority": t.priority,
                            "duration_minutes": t.duration_minutes,
                            "time": t.time,
                            "due_day": t.due_day,
                            "completed": t.completed,
                        }
                        for t in filtered_out
                    ]
                )

            if invalid_duration:
                st.warning(f"{len(invalid_duration)} task(s) have non-positive duration and will be skipped.")

            if skipped_for_budget:
                st.warning(
                    f"With a {constraint.minutes_available} minute budget, "
                    f"{len(skipped_for_budget)} due task(s) would be skipped after higher-priority packing."
                )
                st.table(
                    [
                        {
                            "title": t.title,
                            "priority": t.priority,
                            "duration_minutes": t.duration_minutes,
                            "time": t.time,
                        }
                        for t in skipped_for_budget
                    ]
                )

            plan = scheduler.build_plan(owner=owner, pet=pet, tasks=all_tasks, constraint=constraint)

            st.divider()
            st.subheader("Plan result")

            st.success(plan.summary())
            if plan.warnings:
                st.markdown("### Warnings")
                for w in plan.warnings:
                    st.warning(w)

            st.markdown("### Scheduled tasks (with reasons)")
            st.table(
                [
                    {
                        "order": idx + 1,
                        "title": task.title,
                        "duration_minutes": task.duration_minutes,
                        "priority": task.priority,
                        "time": task.time,
                        "reason": reason,
                    }
                    for idx, (task, reason) in enumerate(plan.iter_with_reasons())
                ]
            )

            if plan.skipped_tasks:
                st.markdown("### Skipped tasks (budget)")
                st.table(
                    [
                        {
                            "title": t.title,
                            "duration_minutes": t.duration_minutes,
                            "priority": t.priority,
                            "time": t.time,
                        }
                        for t in plan.skipped_tasks
                    ]
                )
