import streamlit as st
from pawpal_system import CareTask, Pet, Owner, Planner

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    "A smart pet care planner — add tasks, detect conflicts, and generate a "
    "priority-based daily schedule that fits your time budget."
)

# --- Session state initialization ---
# These objects persist across Streamlit reruns so data isn't lost on every click.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes_per_day=60)

if "pet" not in st.session_state:
    pet = Pet(name="Mochi", species="dog")
    st.session_state.owner.add_pet(pet)
    st.session_state.pet = pet

if "planner" not in st.session_state:
    st.session_state.planner = Planner()

st.divider()

# --- Owner & Pet info ---
st.subheader("Owner & Pet Info")
owner_name = st.text_input("Owner name", value=st.session_state.owner.name)
available_minutes = st.number_input(
    "Available minutes per day", min_value=1, max_value=480,
    value=st.session_state.owner.available_minutes_per_day
)
st.session_state.owner.update_profile(name=owner_name, available_minutes=int(available_minutes))

pet_name = st.text_input("Pet name", value=st.session_state.pet.name)
species = st.selectbox("Species", ["dog", "cat", "other"],
                        index=["dog", "cat", "other"].index(st.session_state.pet.species))
st.session_state.pet.name = pet_name
st.session_state.pet.species = species

# --- Add a Task ---
st.markdown("### Add a Task")
PRIORITY_MAP = {"low": 1, "medium": 3, "high": 5}
CATEGORY_OPTIONS = ["Exercise", "Feeding", "Grooming", "Health", "Enrichment", "Other"]

col1, col2 = st.columns(2)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    priority_label = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with col2:
    category = st.selectbox("Category", CATEGORY_OPTIONS)
    task_time = st.text_input("Scheduled time (HH:MM)", value="", placeholder="e.g. 08:00")
    frequency = st.selectbox("Frequency", ["once", "daily", "weekly"])

if st.button("Add task"):
    new_task = CareTask(
        title=task_title,
        category=category,
        duration_minutes=int(duration),
        priority=PRIORITY_MAP[priority_label],
        time=task_time,
        frequency=frequency,
    )
    st.session_state.pet.add_care_task(new_task)
    st.success(f"Added '{task_title}'!")

# --- Task List with Sorting & Filtering ---
st.divider()
st.markdown("### Tasks")

planner = st.session_state.planner
all_tasks = st.session_state.pet.list_tasks()

if all_tasks:
    # Filter controls
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        status_filter = st.radio("Show tasks", ["All", "Incomplete", "Completed"], horizontal=True)
    with filter_col2:
        sort_option = st.radio("Sort by", ["Time", "Priority (high first)"], horizontal=True)

    # Apply filter
    if status_filter == "Incomplete":
        display_tasks = planner.filter_by_status(all_tasks, completed=False)
    elif status_filter == "Completed":
        display_tasks = planner.filter_by_status(all_tasks, completed=True)
    else:
        display_tasks = list(all_tasks)

    # Apply sort
    if sort_option == "Time":
        display_tasks = planner.sort_by_time(display_tasks)
    else:
        display_tasks = sorted(display_tasks, key=lambda t: t.priority, reverse=True)

    if display_tasks:
        st.table([
            {
                "Title": t.title,
                "Category": t.category,
                "Time": t.time or "—",
                "Duration": f"{t.duration_minutes} min",
                "Priority": t.priority,
                "Frequency": t.frequency,
                "Done": "Yes" if t.completed else "No",
            }
            for t in display_tasks
        ])
    else:
        st.info("No tasks match the current filter.")

    # --- Conflict Detection ---
    warnings = planner.detect_conflicts(all_tasks)
    if warnings:
        st.markdown("#### Schedule Conflicts")
        for w in warnings:
            st.warning(w)
    else:
        st.success("No scheduling conflicts detected.")

    # --- Mark Task Complete ---
    st.markdown("#### Mark a Task Complete")
    incomplete = planner.filter_by_status(all_tasks, completed=False)
    if incomplete:
        task_names = [t.title for t in incomplete]
        selected_title = st.selectbox("Select task to complete", task_names)
        if st.button("Mark complete"):
            for t in incomplete:
                if t.title == selected_title:
                    next_task = st.session_state.pet.mark_task_complete(t)
                    st.success(f"'{t.title}' marked complete!")
                    if next_task:
                        st.info(f"Next occurrence created for {next_task.due_date} ({next_task.frequency}).")
                    break
    else:
        st.info("All tasks are complete!")
else:
    st.info("No tasks yet. Add one above.")

# --- Schedule ---
st.divider()
st.subheader("Generate Daily Plan")

if st.button("Generate schedule"):
    plan = planner.build_daily_plan(
        st.session_state.owner, st.session_state.pet
    )
    explanation = planner.explain_plan(plan)

    if plan:
        st.success("Schedule generated!")

        # Show the plan sorted by time
        sorted_plan = planner.sort_by_time(plan)
        st.table([
            {
                "Title": t.title,
                "Category": t.category,
                "Time": t.time or "—",
                "Duration": f"{t.duration_minutes} min",
                "Priority": t.priority,
            }
            for t in sorted_plan
        ])
    else:
        st.warning("No tasks could be scheduled.")

    st.markdown("#### Plan Explanation")
    st.text(explanation)
