import streamlit as st

from datetime import date
from uuid import uuid4

from pawpal_system import CareTask, DailyConstraint, Owner, Pet, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
default_pet_name = st.text_input("Pet name", value="Mochi")
default_species = st.selectbox("Species", ["dog", "cat", "other"])

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

def get_or_init_owner(*, owner_name: str) -> Owner:
    existing = st.session_state.get("owner")
    if isinstance(existing, Owner):
        existing.name = owner_name
        return existing
    owner = Owner(name=owner_name)
    st.session_state.owner = owner
    return owner


def get_or_init_pet(*, owner: Owner, pet_name: str, species: str) -> Pet:
    # Keep pets on the Owner so they persist across reruns/pages.
    for p in owner.pets:
        if p.name == pet_name:
            p.species = species
            return p
    pet = Pet(name=pet_name, species=species)
    owner.add_pet(pet)
    return pet


owner = get_or_init_owner(owner_name=owner_name)

st.markdown("### Pets")
with st.form("add_pet_form", clear_on_submit=False):
    new_pet_name = st.text_input("New pet name", value=default_pet_name).strip()
    new_species = st.selectbox("New pet species", ["dog", "cat", "other"], index=["dog", "cat", "other"].index(default_species))
    add_pet_submitted = st.form_submit_button("Add pet")

if add_pet_submitted:
    try:
        get_or_init_pet(owner=owner, pet_name=new_pet_name, species=new_species)
        st.success(f"Added pet: {new_pet_name} ({new_species})")
    except ValueError as e:
        st.error(str(e))

pet_names = [p.name for p in owner.pets]
if not pet_names:
    st.info("No pets yet. Add one above.")
    selected_pet_name: str | None = None
else:
    # Persist selection across reruns.
    if "selected_pet_name" not in st.session_state or st.session_state.selected_pet_name not in pet_names:
        st.session_state.selected_pet_name = pet_names[0]
    selected_pet_name = st.selectbox("Active pet", options=pet_names, key="selected_pet_name")

active_pet: Pet | None = None
if selected_pet_name:
    active_pet = owner.get_pet(selected_pet_name)

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    if not active_pet:
        st.error("Add/select a pet before adding tasks.")
    else:
        try:
            active_pet.add_task(
                CareTask(
                    id=str(uuid4()),
                    title=str(task_title).strip() or "Untitled task",
                    duration_minutes=int(duration),
                    priority=str(priority),
                )
            )
            st.success(f"Added task to {active_pet.name}.")
        except ValueError as e:
            st.error(str(e))

if active_pet and active_pet.tasks:
    st.write(f"Current tasks for {active_pet.name}:")
    st.table(
        [
            {
                "id": t.id,
                "title": t.title,
                "duration_minutes": t.duration_minutes,
                "priority": t.priority,
                "completed": t.completed,
            }
            for t in active_pet.list_tasks(include_completed=True)
        ]
    )
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

minutes_available = st.number_input(
    "Minutes available today",
    min_value=5,
    max_value=24 * 60,
    value=60,
    step=5,
)

if st.button("Generate schedule"):
    if not active_pet:
        st.error("Add/select a pet before generating a schedule.")
    elif not active_pet.list_tasks(include_completed=False):
        st.error("Add at least one incomplete task before generating a schedule.")
    else:
        pet = active_pet
        tasks = pet.list_tasks(include_completed=False)

        constraint = DailyConstraint(minutes_available=int(minutes_available), day=date.today())
        scheduler = Scheduler()
        plan = scheduler.build_plan(owner=owner, pet=pet, tasks=tasks, constraint=constraint)

        st.success(plan.summary())
        if getattr(plan, "warnings", None):
            st.markdown("### Warnings")
            for w in plan.warnings:
                st.warning(w)

        st.markdown("### Scheduled tasks")
        for task, reason in plan.iter_with_reasons():
            st.markdown(f"- **{task.title}** ({task.duration_minutes} min, {task.priority}): {reason}")

        if plan.skipped_tasks:
            st.markdown("### Skipped tasks")
            st.table(
                [
                    {
                        "title": t.title,
                        "duration_minutes": t.duration_minutes,
                        "priority": t.priority,
                    }
                    for t in plan.skipped_tasks
                ]
            )
