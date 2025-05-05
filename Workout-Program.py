### Debugged and Cleaned Streamlit Workout App

import streamlit as st
import json
import hashlib
import os
import time
from datetime import datetime, timedelta
import calendar
import random
import matplotlib.pyplot as plt
import numpy as np

# ----------- Setup ---------- #
st.set_page_config(page_title="Workout Optimizer", layout="centered")

# ----------- Constants ---------- #
training_split = ["chest_triceps", "back_biceps", "shoulders_abs", "legs", "rest"]

# ----------- Utilities ---------- #
def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

# ----------- User Profile Management ---------- #
def load_user_profile():
    profiles = load_json("user_profiles.json")
    profile_options = [f"{v['name']} ({k})" for k, v in profiles.items()]
    profile_keys = list(profiles.keys())
    selected_label = st.sidebar.selectbox("Select Profile", profile_options + ["+ Add New Profile"])
    if selected_label == "+ Add New Profile":
        selected_name = "+ Add New Profile"
    else:
        selected_index = profile_options.index(selected_label)
        selected_name = profile_keys[selected_index]

    if selected_name == "+ Add New Profile":
        st.sidebar.subheader("Create New Profile")
        email = st.sidebar.text_input("Email (used as login ID)", key="new_email")
        password = st.sidebar.text_input("Password", type="password", key="new_password")
        name = st.sidebar.text_input("Name", key="new_name")
        age = st.sidebar.number_input("Age", min_value=10, max_value=100, step=1, key="new_age")
        height = st.sidebar.text_input("Height (e.g., 5'10)", key="new_height")
        weight = st.sidebar.number_input("Weight (lbs)", min_value=50, max_value=400, key="new_weight")
        goal = st.sidebar.selectbox("Goal", ["Strength", "Hypertrophy", "Endurance"], key="new_goal")
        if st.sidebar.button("Create Profile") and name and height and email and password:
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            profiles[email] = {"name": name, "email": email, "password": hashed_pw, "age": age, "height": height, "weight": weight, "goal": goal, }
            save_json("user_profiles.json", profiles)
            st.success("Profile created! Please reload the app.")
            st.stop()
        return {}
    else:
        profile = profiles[selected_name]
        login_pass = st.sidebar.text_input("Enter password to access profile", type="password", key="login_pass")
        hashed_login = hashlib.sha256(login_pass.encode()).hexdigest()
        if hashed_login != profile.get("password"):
            st.error("Incorrect password. Access denied.")
            if st.sidebar.button("Reset Password"):
                new_pass = st.sidebar.text_input("Enter new password", type="password", key="reset_pass")
                if new_pass:
                    profile["password"] = hashlib.sha256(new_pass.encode()).hexdigest()
                    profiles[selected_name] = profile
                    save_json("user_profiles.json", profiles)
                    st.success("Password reset successfully. Please re-enter.")
                    st.stop()
            else:
                st.stop()
        
        st.session_state["current_profile_name"] = selected_name
        return profile

def save_user_profile(profile):
    profiles = load_json("user_profiles.json")
    if "current_profile_name" in st.session_state:
        profiles[st.session_state["current_profile_name"]] = profile
        save_json("user_profiles.json", profiles)
    save_json("user_profile.json", profile)

def profile_interface():
    def delete_profile(name):
        profiles = load_json("user_profiles.json")
        if name in profiles:
            del profiles[name]
            save_json("user_profiles.json", profiles)
            st.success(f"Deleted profile: {name}")
            st.rerun()

    def rename_profile(old_name, new_name):
        profiles = load_json("user_profiles.json")
        if old_name in profiles and new_name:
            profiles[new_name] = profiles.pop(old_name)
            save_json("user_profiles.json", profiles)
            st.session_state["current_profile_name"] = new_name
            st.success(f"Renamed profile: {old_name} ➜ {new_name}")
            st.rerun()
    st.session_state.clear()

    st.sidebar.title("👤 User Profile")
    profiles = load_json("user_profiles.json")
    if "current_profile_name" in st.session_state:
        current_name = st.session_state["current_profile_name"]
        with st.sidebar.expander(f"Manage Profile: {current_name}"):
            new_name = st.text_input("Rename profile", value=current_name)
            if st.button("Rename Profile"):
                rename_profile(current_name, new_name)
            if st.button("Delete Profile"):
                delete_profile(current_name)
    profile = load_user_profile()
    if not profile:
        st.sidebar.subheader("Set Up Your Profile")
        name = st.sidebar.text_input("Name")
        age = st.sidebar.number_input("Age", min_value=10, max_value=100, step=1)
        height = st.sidebar.text_input("Height (e.g., 5'10)")
        weight = st.sidebar.number_input("Weight (lbs)", min_value=50, max_value=400)
        goal = st.sidebar.selectbox("Goal", ["Strength", "Hypertrophy", "Endurance"])
        if st.sidebar.button("Save Profile") and name and height:
            profile = {"name": name, "age": age, "height": height, "weight": weight, "goal": goal, "day_counter": 0}
            save_user_profile(profile)
            st.success("Profile saved! Please reload the app.")
            st.stop()
    else:
        st.sidebar.markdown(f"**Name:** {profile['name']}")
        st.sidebar.markdown(f"**Age:** {profile['age']}")
        st.sidebar.markdown(f"**Height:** {profile['height']}")
        st.sidebar.markdown(f"**Weight:** {profile['weight']} lbs")
        st.sidebar.markdown(f"**Goal:** {profile['goal']}")
    return profile

# ----------- Cycle Tagging ---------- #
def get_cycle_tags():
    return load_json("cycle_tags.json")

def save_cycle_tag(date_key, name):
    tags = get_cycle_tags()
    tags[date_key] = name
    save_json("cycle_tags.json", tags)

def auto_tag_cycle(stats):
    total_volume = sum(stats.values())
    if total_volume > 1000:
        return "High Volume Week"
    elif total_volume > 500:
        return "Moderate Volume"
    elif total_volume > 0:
        return "Light Activity"
    else:
        return "Rest Week"

# ----------- Muscle Tracking and Logging ---------- #
def save_cumulative_stats():
    save_json("muscle_stats.json", muscle_hit_tracker)

muscle_hit_tracker = {}

def update_muscles_hit(exercise_list):
    for exercise in exercise_list:
        for muscle in muscle_map.get(exercise, []):
            muscle_hit_tracker[muscle] = muscle_hit_tracker.get(muscle, 0) + 1

def reset_muscle_tracker():
    global muscle_hit_tracker
    muscle_hit_tracker = {}

def get_muscles_least_hit(exercise_group):
    muscle_scores = {}
    for exercise in exercise_group:
        name = exercise[0]
        muscles = muscle_map.get(name, [])
        total_score = sum(muscle_hit_tracker.get(m, 0) for m in muscles)
        muscle_scores[name] = total_score
    sorted_exercises = sorted(exercise_group, key=lambda ex: muscle_scores[ex[0]])
    return sorted_exercises

def select_exercises_with_focus(split, k=5):
    pool = exercise_pool.get(split, [])
    focused = get_muscles_least_hit(pool)
    chosen = focused[:k]
    update_muscles_hit([ex[0] for ex in chosen])
    return chosen

def show_rest_timer(seconds=60, key=None):
    if st.button("Start Rest Timer", key=key):
        with st.empty():
            for remaining in range(seconds, 0, -1):
                st.markdown(f"⏳ Rest: {remaining} seconds remaining")
                time.sleep(1)
            st.success("Rest complete!")

# ----------- Visualization ---------- #
def radar_chart(data):
    labels = list(data.keys())
    stats = list(data.values())
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    stats += stats[:1]
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, stats, color='blue', linewidth=2)
    ax.fill(angles, stats, color='skyblue', alpha=0.4)
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10)
    st.pyplot(fig)

# ----------- Placeholder for Exercises & Muscles ---------- #
exercise_pool = {
    "chest_triceps": [
        ("Incline Barbell Press", 4, 10, 135),
        ("Flat Bench Press", 4, 10, 155),
        ("Decline Dumbbell Press", 4, 10, 50),
        ("Cable Crossover (High to Low)", 3, 15, 25),
        ("Dumbbell Flys", 3, 12, 30),
        ("Overhead Dumbbell Extension", 3, 12, 40),
        ("Skull Crushers", 3, 10, 40),
        ("Triceps Pushdown (Rope)", 3, 15, 30),
        ("Close-Grip Bench Press", 4, 8, 135),
        ("Dips (Weighted)", 3, 10, 20)
    ],
    "back_biceps": [
        ("Pull-ups", 3, 10, "Bodyweight"),
        ("Barbell Row", 4, 10, 135),
        ("Lat Pulldown (Wide)", 4, 12, 110),
        ("Seated Cable Row", 4, 10, 100),
        ("Deadlift", 3, 5, 225),
        ("Incline Dumbbell Curl", 3, 10, 30),
        ("Concentration Curl", 3, 10, 25),
        ("EZ Bar Curl", 3, 10, 50),
        ("Hammer Curl", 3, 12, 35),
        ("Preacher Curl", 3, 12, 45)
    ],
    "shoulders_abs": [
        ("Overhead Press", 4, 8, 95),
        ("Lateral Raises", 3, 15, 20),
        ("Rear Delt Fly", 3, 15, 20),
        ("Front Raises", 3, 12, 20),
        ("Arnold Press", 4, 10, 40),
        ("Hanging Leg Raises", 3, 15, "Bodyweight"),
        ("Russian Twists", 3, 20, "Bodyweight"),
        ("Cable Crunches", 3, 15, 50),
        ("Plank", 3, 60, "Seconds"),
        ("Bicycle Crunches", 3, 20, "Bodyweight")
    ],
    "legs": [
        ("Barbell Back Squat", 4, 10, 185),
        ("Romanian Deadlift", 4, 10, 135),
        ("Walking Lunges", 3, 12, 25),
        ("Leg Press", 4, 12, 200),
        ("Step-Ups", 3, 12, 30),
        ("Leg Extension", 3, 15, 80),
        ("Hamstring Curl", 3, 15, 70),
        ("Glute Bridges", 3, 15, 60),
        ("Seated Calf Raise", 3, 20, 90),
        ("Standing Calf Raise", 3, 20, 100)
    ]
}

muscle_map = {
    "Incline Barbell Press": ["Chest_Upper"],
    "Flat Bench Press": ["Chest_Mid"],
    "Decline Dumbbell Press": ["Chest_Lower"],
    "Cable Crossover (High to Low)": ["Chest_Lower"],
    "Dumbbell Flys": ["Chest_Inner"],
    "Overhead Dumbbell Extension": ["Triceps_Long"],
    "Skull Crushers": ["Triceps_Long"],
    "Triceps Pushdown (Rope)": ["Triceps_Lateral"],
    "Close-Grip Bench Press": ["Triceps_Medial"],
    "Dips (Weighted)": ["Chest_Lower", "Triceps_Medial"],
    "Pull-ups": ["Back_Upper"],
    "Barbell Row": ["Back_Mid"],
    "Lat Pulldown (Wide)": ["Back_Upper"],
    "Seated Cable Row": ["Back_Mid"],
    "Deadlift": ["Back_Lower"],
    "Incline Dumbbell Curl": ["Biceps_Long"],
    "Concentration Curl": ["Biceps_Short"],
    "EZ Bar Curl": ["Biceps_Short"],
    "Hammer Curl": ["Biceps_Brachialis"],
    "Preacher Curl": ["Biceps_Short"],
    "Overhead Press": ["Shoulder_Anterior"],
    "Lateral Raises": ["Shoulder_Lateral"],
    "Rear Delt Fly": ["Shoulder_Posterior"],
    "Front Raises": ["Shoulder_Anterior"],
    "Arnold Press": ["Shoulder_Anterior", "Shoulder_Lateral"],
    "Hanging Leg Raises": ["Abs_Lower"],
    "Russian Twists": ["Abs_Obliques"],
    "Cable Crunches": ["Abs_Upper"],
    "Plank": ["Abs_Core"],
    "Bicycle Crunches": ["Abs_Obliques"],
    "Barbell Back Squat": ["Quads", "Glutes"],
    "Romanian Deadlift": ["Hamstrings", "Glutes"],
    "Walking Lunges": ["Quads", "Glutes"],
    "Leg Press": ["Quads"],
    "Step-Ups": ["Quads"],
    "Leg Extension": ["Quads"],
    "Hamstring Curl": ["Hamstrings"],
    "Glute Bridges": ["Glutes"],
    "Seated Calf Raise": ["Calves"],
    "Standing Calf Raise": ["Calves"]
}

# ----------- Daily Logging ---------- #
def log_daily_workout(profile):
    today_split = st.selectbox("Choose today's workout split", training_split)
    st.header(f"Today's Split: {today_split.replace('_', ' ').title()}")

    if today_split == "rest":
        st.info("Today is a rest day. Get some good recovery!")
        return

    exercises = select_exercises_with_focus(today_split)
    st.markdown("### 🏋️‍♂️ Today's Exercises")
    for i, (name, sets, reps, weight) in enumerate(exercises):
        st.markdown(f"**{i+1}. {name}** — {sets} sets x {reps} reps @ {weight} lbs")

    if st.button("Start Workout"):
        session_log = {}
        st.markdown("---")
        st.subheader("📝 Log Workout Performance")
        for name, sets, reps, weight in exercises:
            used_weight = st.text_input(f"Actual weight used for {name}", value=str(weight), key=f"w_{name}")
            set_data = []
            for s in range(1, sets+1):
                reps_done = st.number_input(f"{name} - Set {s} reps", 0, 100, value=reps, key=f"{name}_set{s}")
                set_data.append({"set": s, "reps": reps_done})
                show_rest_timer(30, key=f"rest_timer_{name}_set{s}")
            session_log[name] = {"weight": used_weight, "sets": set_data}

        if st.button("Finish and Save Workout"):
            date_str = datetime.today().strftime("%Y%m%d")
            save_json(f"logs_{date_str}.json", session_log)
            save_user_profile(profile)
            save_cumulative_stats()
            st.success("Workout saved! Great job today 💪")
            st.rerun()

# ----------- Stats Display ---------- #
def display_cumulative_muscle_stats():
    st.markdown("### 📊 Cumulative Muscle Stats")
    stats = load_json("muscle_stats.json")
    if not stats:
        st.info("No muscle data yet.")
        return
    muscle_group_filter = st.multiselect(
        "Filter by muscle group",
        sorted(set(m.split('_')[0] for m in stats)),
        default=[]
    )
    filtered = {k.replace('_', ' '): v for k, v in stats.items() if not muscle_group_filter or k.split('_')[0] in muscle_group_filter}
    if filtered:
        st.bar_chart(filtered)
        st.markdown("#### Radar View of Muscle Engagement")
        radar_chart(filtered)
    else:
        st.info("No data matches the selected filter.")
    st.markdown("---")
    st.markdown("### 📆 Tag This Cycle")
    cycle_name = st.text_input("Name this training cycle")
    if st.button("Save Cycle Tag") or not cycle_name.strip():
        if not cycle_name.strip():
            cycle_name = auto_tag_cycle(stats)
        save_cycle_tag(datetime.today().strftime("%Y%m%d"), cycle_name)
        st.success(f"Cycle '{cycle_name}' saved!")

# ----------- Summaries ---------- #
def summarize_logs_by_period(days):
    summary = {}
    today = datetime.today()
    for file in os.listdir():
        if file.startswith("logs_") and file.endswith(".json"):
            date_str = file[5:13]
            try:
                date_obj = datetime.strptime(date_str, "%Y%m%d")
            except ValueError:
                continue
            if (today - date_obj).days <= days:
                with open(file, "r") as f:
                    data = json.load(f)
                for ex, ex_data in data.items():
                    for set_entry in ex_data["sets"]:
                        for muscle in muscle_map.get(ex, []):
                            summary[muscle] = summary.get(muscle, 0) + set_entry["reps"]
    return summary

def display_week_month_summary():
    st.markdown("---")
    st.markdown("### 🗓️ Weekly & Monthly Muscle Summary")
    st.markdown("#### Weekly Summary")
    week_summary = summarize_logs_by_period(7)
    if week_summary:
        st.bar_chart({k.replace('_', ' '): v for k, v in week_summary.items()})
    else:
        st.info("No data for this week.")
    st.markdown("#### Monthly Summary")
    month_summary = summarize_logs_by_period(30)
    if month_summary:
        st.bar_chart({k.replace('_', ' '): v for k, v in month_summary.items()})
    else:
        st.info("No data for this month.")

# ----------- Run App ---------- #
profile = profile_interface()
log_daily_workout(profile)
display_cumulative_muscle_stats()
display_week_month_summary()
