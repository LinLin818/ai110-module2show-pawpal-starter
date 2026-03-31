"""
PawPal+ — Streamlit UI
app.py

Run with:  streamlit run app.py
"""

import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

# ---------------------------------------------------------------------------
# Session state vault — runs once, persists across re-runs
# ---------------------------------------------------------------------------

if "owner" not in st.session_state:
    st.session_state.owner = None          # set during onboarding

if "scheduler" not in st.session_state:
    st.session_state.scheduler = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_owner() -> Owner | None:
    return st.session_state.owner


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Your daily pet care planner")


# ---------------------------------------------------------------------------
# Section 1 — Owner setup
# ---------------------------------------------------------------------------

st.header("1. Owner Setup")

if get_owner() is None:
    with st.form("owner_form"):
        name        = st.text_input("Your name")
        daily_hours = st.slider("Hours available for pet care today", 0.5, 8.0, 2.0, 0.5)
        pref_times  = st.multiselect(
            "Preferred times",
            ["morning", "afternoon", "evening"],
            default=["morning"],
        )
        submitted = st.form_submit_button("Save Owner Profile")

    if submitted:
        if not name.strip():
            st.warning("Please enter your name.")
        else:
            # Wired to Owner() constructor — persisted in session state
            st.session_state.owner = Owner(
                name=name.strip(),
                daily_hours=daily_hours,
                preferred_times=pref_times,
            )
            st.rerun()
else:
    owner = get_owner()
    st.success(
        f"**{owner.name}** — {owner.daily_hours}h available "
        f"| preferred: {', '.join(owner.preferred_times) or 'any'}"
    )
    if st.button("Reset owner profile"):
        st.session_state.owner     = None
        st.session_state.scheduler = None
        st.rerun()


# ---------------------------------------------------------------------------
# Section 2 — Add a pet
# ---------------------------------------------------------------------------

if get_owner() is not None:
    st.header("2. Your Pets")
    owner = get_owner()

    with st.form("pet_form"):
        col1, col2, col3 = st.columns(3)
        pet_name    = col1.text_input("Pet name")
        pet_species = col2.text_input("Species (e.g. Dog, Cat)")
        pet_age     = col3.number_input("Age (years)", min_value=0, max_value=30, value=1)
        add_pet = st.form_submit_button(" Add Pet")

    if add_pet:
        if not pet_name.strip() or not pet_species.strip():
            st.warning("Please fill in both name and species.")
        else:
            # Wired to owner.add_pet() — Pet object stored inside Owner
            new_pet = Pet(
                name=pet_name.strip(),
                species=pet_species.strip(),
                age=int(pet_age),
            )
            owner.add_pet(new_pet)
            st.success(f"Added {new_pet.name} the {new_pet.species}!")
            st.rerun()

    # Show current pets
    if owner.pets:
        for pet in owner.pets:
            pending = len(pet.get_pending_tasks())
            st.markdown(f"- **{pet.name}** ({pet.species}, age {pet.age}) — {pending} pending task(s)")
    else:
        st.info("No pets added yet.")


# ---------------------------------------------------------------------------
# Section 3 — Add tasks
# ---------------------------------------------------------------------------

if get_owner() is not None and get_owner().pets:
    st.header("3. Add Tasks")
    owner = get_owner()

    pet_names = [p.name for p in owner.pets]

    with st.form("task_form"):
        selected_pet  = st.selectbox("Assign to pet", pet_names)
        task_name     = st.text_input("Task name (e.g. Morning walk)")
        col1, col2    = st.columns(2)
        duration      = col1.number_input("Duration (mins)", min_value=1, max_value=120, value=15)
        priority      = col2.slider("Priority", 1, 5, 3)
        col3, col4    = st.columns(2)
        time_window   = col3.selectbox("Time window", ["morning", "afternoon", "evening", "any"])
        frequency     = col4.selectbox("Frequency", ["daily", "weekly", "as_needed"])
        add_task      = st.form_submit_button("➕ Add Task")

    if add_task:
        if not task_name.strip():
            st.warning("Please enter a task name.")
        else:
            # Wired to pet.add_task() — Task object stored inside Pet
            pet = next(p for p in owner.pets if p.name == selected_pet)
            new_task = Task(
                name=task_name.strip(),
                duration_mins=int(duration),
                priority=priority,
                time_window=time_window,
                frequency=frequency,
            )
            pet.add_task(new_task)
            st.success(f"Added '{new_task.name}' to {pet.name}'s task list.")
            st.rerun()

    # Show all tasks per pet
    for pet in owner.pets:
        if pet.tasks:
            st.markdown(f"**{pet.name}'s tasks:**")
            for t in pet.tasks:
                status = "checked" if t.completed else "⬜"
                st.markdown(
                    f"&nbsp;&nbsp;{status} {t.name} — "
                    f"{t.duration_mins} min | priority {t.priority} | {t.time_window}",
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# ---------------------------------------------------------------------------

if get_owner() is not None and get_owner().pets:
    st.header("4. Today's Schedule")
    owner = get_owner()

    if st.button("🗓 Generate Plan"):
        #  Wired to Scheduler.generate_plan()
        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()
        st.session_state.scheduler = scheduler

    if st.session_state.scheduler is not None:
        plan = st.session_state.scheduler.plan

        if not plan:
            st.warning("No tasks could be scheduled — check your budget or add more tasks.")
        else:
            total_mins = sum(i.task.duration_mins for i in plan)
            st.success(f"Scheduled {len(plan)} tasks · {total_mins} min used of {owner.get_available_minutes()} min budget")

            for item in plan:
                with st.expander(f"{item.format_slot()} — {item.pet.name}: {item.task.name}"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Priority", "★" * item.task.priority)
                    col2.metric("Duration", f"{item.task.duration_mins} min")
                    col3.metric("Window", item.task.time_window.capitalize())
                    st.caption(f"💡 {item.reason}")

                    # Wired to task.mark_complete()
                    if not item.task.completed:
                        if st.button(f"Mark complete", key=item.task.task_id):
                            item.task.mark_complete()
                            st.rerun()
                    else:
                        st.success("Completed")