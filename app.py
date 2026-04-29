"""
app.py - PawPal+ Streamlit UI
Run: streamlit run app.py
"""

import streamlit as st
from pawpal_system import Task, Pet, Owner, Scheduler
from ai_assistant import ask_assistant
from datetime import date

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Your smart daily pet care planner")

# ── Session state bootstrap ───────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar – Owner setup
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("👤 Owner Setup")
    owner_name = st.text_input("Your name", value="Jordan")
    available_minutes = st.number_input(
        "Daily time budget (min)", min_value=15, max_value=480, value=120, step=15
    )

    if st.button("Save owner", use_container_width=True):
        existing_pets = st.session_state.owner.pets if st.session_state.owner else []
        st.session_state.owner = Owner(name=owner_name, available_minutes=int(available_minutes))
        st.session_state.owner.pets = existing_pets
        st.success(f"Owner saved: {owner_name}")

    st.divider()

    st.header("🐶 Add a Pet")
    pet_name = st.text_input("Pet name", value="Mochi")
    species  = st.selectbox("Species", ["dog", "cat", "other"])
    breed    = st.text_input("Breed (optional)")
    age      = st.number_input("Age (years)", min_value=0.0, max_value=30.0, step=0.5, value=2.0)

    if st.button("Add pet", use_container_width=True):
        if st.session_state.owner is None:
            st.warning("Save your owner profile first.")
        else:
            existing_names = [p.name.lower() for p in st.session_state.owner.pets]
            if pet_name.lower() in existing_names:
                st.warning(f"A pet named '{pet_name}' already exists.")
            else:
                st.session_state.owner.add_pet(
                    Pet(name=pet_name, species=species, breed=breed, age_years=age)
                )
                st.success(f"Added {pet_name}!")

# ── Guard ─────────────────────────────────────────────────────────────────────
if st.session_state.owner is None:
    st.info("👈 Set up your owner profile in the sidebar to get started.")
    st.stop()

owner: Owner = st.session_state.owner

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_schedule, tab_tasks, tab_pets, tab_ai = st.tabs(
    ["📅 Daily Schedule", "➕ Manage Tasks", "🐾 My Pets", "🤖 AI Assistant"]
)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 – Daily Schedule
# ═════════════════════════════════════════════════════════════════════════════
with tab_schedule:
    st.subheader(f"Today's Plan for {owner.name}")

    if not owner.pets:
        st.info("Add a pet in the sidebar to get started.")
    else:
        scheduler = Scheduler(owner)
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            for w in conflicts:
                st.warning(w)

        schedule  = scheduler.build_daily_schedule()
        total_min = sum(t.duration_minutes for _, t in schedule)

        col_a, col_b = st.columns(2)
        col_a.metric("Tasks scheduled", len(schedule))
        col_b.metric("Time used", f"{total_min} / {owner.available_minutes} min")

        if not schedule:
            st.success("✅ No pending tasks — all done!")
        else:
            for pet, task in schedule:
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"**{task.time}** &nbsp; [{pet.name}] &nbsp; {task.title}")
                badge = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
                c1.caption(f"{badge} {task.priority} · {task.duration_minutes} min · {task.frequency}")
                if task.notes:
                    c1.caption(f"📝 {task.notes}")
                if c2.button("✓ Done", key=f"done_{pet.name}_{task.title}_{task.time}"):
                    successor = scheduler.complete_task(pet, task)
                    if successor:
                        st.toast(f"Next '{task.title}' scheduled for {successor.due_date}")
                    else:
                        st.toast(f"'{task.title}' marked complete.")
                    st.rerun()
                st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 – Manage Tasks
# ═════════════════════════════════════════════════════════════════════════════
with tab_tasks:
    st.subheader("Add a Task")

    if not owner.pets:
        st.info("Add a pet first.")
    else:
        pet_names = [p.name for p in owner.pets]

        with st.form("add_task_form", clear_on_submit=True):
            selected_pet = st.selectbox("Pet", pet_names)
            t_title      = st.text_input("Task title", value="Morning walk")
            t_time       = st.text_input("Time (HH:MM)", value="07:30")
            t_duration   = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
            t_priority   = st.selectbox("Priority", ["high", "medium", "low"], index=1)
            t_frequency  = st.selectbox("Frequency", ["daily", "weekly", "once"])
            t_notes      = st.text_input("Notes (optional)")
            submitted    = st.form_submit_button("Add task")

        if submitted:
            try:
                h, m = t_time.split(":")
                assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
            except Exception:
                st.error("Time must be in HH:MM format (e.g. 07:30).")
            else:
                target_pet = next(p for p in owner.pets if p.name == selected_pet)
                target_pet.add_task(Task(
                    title=t_title,
                    duration_minutes=int(t_duration),
                    time=t_time,
                    priority=t_priority,
                    frequency=t_frequency,
                    notes=t_notes,
                ))
                st.success(f"Added '{t_title}' for {selected_pet}!")

        st.divider()
        st.subheader("All Tasks")
        for pet in owner.pets:
            with st.expander(f"{pet.name} — {len(pet.tasks)} task(s)"):
                if not pet.tasks:
                    st.caption("No tasks yet.")
                else:
                    for task in pet.tasks:
                        status = "✅" if task.completed else "⏳"
                        st.markdown(f"{status} **{task.time}** &nbsp; {task.title} &nbsp; _{task.duration_minutes} min_")
                    if st.button(f"Remove last task for {pet.name}", key=f"rm_{pet.name}"):
                        if pet.tasks:
                            removed = pet.tasks.pop()
                            st.toast(f"Removed '{removed.title}'")
                            st.rerun()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 – My Pets
# ═════════════════════════════════════════════════════════════════════════════
with tab_pets:
    st.subheader("Registered Pets")

    if not owner.pets:
        st.info("No pets yet. Add one in the sidebar.")
    else:
        for pet in owner.pets:
            with st.container():
                st.markdown(f"### {pet.name}")
                cols = st.columns(3)
                cols[0].metric("Species", pet.species)
                cols[1].metric("Breed", pet.breed or "—")
                cols[2].metric("Age", f"{pet.age_years} yr")
                st.caption(f"{len(pet.get_pending_tasks())} pending · {len(pet.tasks)} total")
                if st.button(f"Remove {pet.name}", key=f"rmpet_{pet.name}"):
                    owner.remove_pet(pet.name)
                    st.toast(f"Removed {pet.name}.")
                    st.rerun()
                st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 – AI Assistant
# ═════════════════════════════════════════════════════════════════════════════
with tab_ai:
    st.subheader("🤖 Ask PawPal+ AI")
    st.caption(
        "Ask anything about your pets or today's schedule. "
        "The AI has access to your current pet and task data."
    )

    # Display chat history
    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(turn["user"])
        with st.chat_message("assistant"):
            st.markdown(turn["assistant"])
            conf = turn.get("confidence", 0.5)
            color = "green" if conf >= 0.8 else "orange" if conf >= 0.5 else "red"
            st.caption(f"Confidence: :{color}[{conf:.2f}]")

    # Input
    user_input = st.chat_input("Ask about your pets or schedule...")

    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = ask_assistant(
                    user_input,
                    owner,
                    st.session_state.chat_history,
                )

            if result["error"]:
                st.error(result["response"])
            elif result["blocked"]:
                st.warning(result["response"])
            else:
                st.markdown(result["response"])
                conf = result["confidence"]
                color = "green" if conf >= 0.8 else "orange" if conf >= 0.5 else "red"
                st.caption(f"Confidence: :{color}[{conf:.2f}]")

                # Save to history
                st.session_state.chat_history.append({
                    "user": user_input,
                    "assistant": result["response"],
                    "confidence": conf,
                })

    # Clear chat button
    if st.session_state.chat_history:
        if st.button("🗑️ Clear chat"):
            st.session_state.chat_history = []
            st.rerun()