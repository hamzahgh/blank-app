# streamlit_app.py

import streamlit as st
import json, os, time, re
import matplotlib.pyplot as plt
from datetime import datetime
import hashlib

# ───── Page Configuration ─────
st.set_page_config(
    page_title="Workout Optimizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ───── Helpers ─────

def load_json(path, default):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def ensure_session_state():
    for key, val in {
        "auto_adjust": "none",
        "settings": {},
        "current_profile": None,
        "profiles_list": []
    }.items():
        if key not in st.session_state:
            st.session_state[key] = val

def hash_password(pw: str):
    return hashlib.sha256(pw.encode()).hexdigest()

def calculate_volume(weight, reps, sets):
    return weight * reps * sets

def get_auto_adjust_level(sleep, stress, soreness, rpe):
    if rpe > 8 or stress > 7 or soreness > 6:
        return "reduce"
    elif sleep >= 8 and stress <= 4:
        return "boost"
    return "none"

def themed_header(label, color="#e3f2fd", icon="🧠"):
    st.markdown(f"""
    <div style='background-color:{color};padding:8px;border-radius:8px;'>
      <h4 style='margin:0;color:#1976d2'>{icon} {label}</h4>
    </div>""", unsafe_allow_html=True)

def start_rest_timer(seconds):
    # real-time rest timer
    with st.spinner(f"Resting for {seconds} seconds..."):
        for sec in range(seconds, 0, -1):
            st.write(f"⏱️ {sec}s remaining", end="\r")
            time.sleep(1)
        st.success("✅ Rest complete!")

# ───── Data Paths ─────
PROFILE_DIR = "profiles"
LOGS_DIR    = "logs"
STATS_PATH  = os.path.join(PROFILE_DIR, "muscle_stats.json")
EX_DB_PATH  = "exercise_db.json"

os.makedirs(PROFILE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ───── Load / Save Profiles ─────

def list_profiles():
    return [fn[:-5] for fn in os.listdir(PROFILE_DIR) if fn.endswith(".json")]

def load_profile(name):
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    return load_json(path, None)

def save_profile(name, data):
    path = os.path.join(PROFILE_DIR, f"{name}.json")
    save_json(path, data)

# ───── Load Exercise Database ─────
# (Make sure exercise_db.json contains the full expanded database)
exercise_db = load_json(EX_DB_PATH, [])

# ───── Profile UI ─────

def render_profile_tab():
    st.sidebar.header("👤 Profile")
    profiles = list_profiles()
    choice = st.sidebar.selectbox("Select profile", ["<New Profile>"] + profiles)
    if choice == "<New Profile>":
        name = st.sidebar.text_input("Name", key="new_name")
        email = st.sidebar.text_input("Email", key="new_email")
        password = st.sidebar.text_input("Password", type="password", key="new_pw")
        age = st.sidebar.number_input("Age", min_value=10, max_value=100, key="new_age")
        height = st.sidebar.text_input("Height (e.g., 5'10)", key="new_height")
        weight = st.sidebar.number_input("Weight (lbs)", min_value=50, max_value=500, key="new_weight")
        gender = st.sidebar.selectbox("Gender", ["Male","Female","Other"], key="new_gender")
        goal = st.sidebar.selectbox("Goal", ["Strength","Hypertrophy","Endurance","Recomposition"], key="new_goal")
        equipment = st.sidebar.multiselect("Equipment Available",
            ["Barbell","Dumbbell","Machine","Cable","Bodyweight","Free Weight"], key="new_eq")
        if st.sidebar.button("Create Profile"):
            # validate & save
            try:
                feet,inches = map(int,re.match(r"^(\d+)['’](\d+)$",height).groups())
                height_in = feet*12+inches
                prof = {
                    "name": name, "email": email, "password": hash_password(password),
                    "age": age, "height": height_in, "weight": weight,
                    "gender": gender, "goal": goal,
                    "equipment": equipment,
                    "day_cycle": [],
                    "settings": {"theme":"Light","coaching":True,"warmup":True},
                    "custom_exercises": []
                }
                save_profile(name, prof)
                st.sidebar.success(f"Profile '{name}' created.")
                st.session_state.current_profile = name
            except:
                st.sidebar.error("Invalid height format.")
    else:
        prof = load_profile(choice)
        # ask password
        pw = st.sidebar.text_input("Password", type="password", key="load_pw")
        if st.sidebar.button("Login"):
            if prof and hash_password(pw)==prof["password"]:
                st.session_state.current_profile = choice
                st.session_state.settings = prof.get("settings",{})
                st.sidebar.success(f"Welcome back, {prof['name']}!")
            else:
                st.sidebar.error("Invalid password.")

# ───── “My Exercises” Tab ─────

def render_my_exercises_tab(prof):
    st.header("📝 My Custom Exercises")
    col1,col2 = st.columns(2)
    with col1:
        themed_header("Add a New Exercise")
        name = st.text_input("Name", key="ce_name")
        muscle = st.selectbox("Muscle Group", ["Chest","Back","Shoulders","Biceps","Triceps","Legs","Abs"], key="ce_muscle")
        sub = st.text_input("Sub-muscle", key="ce_sub")
        typ = st.selectbox("Type", ["Compound","Isolation","Functional","Bodyweight"], key="ce_type")
        lvl = st.selectbox("Level", ["Beginner","Intermediate","Advanced"], key="ce_lvl")
        eqp = st.multiselect("Equipment", ["Barbell","Dumbbell","Machine","Cable","Bodyweight","Free Weight"], key="ce_eq")
        vid = st.text_input("Video URL", key="ce_vid")
        img = st.text_input("Image URL", key="ce_img")
        desc= st.text_area("Description", key="ce_desc")
        if st.button("Add Exercise"):
            ce = {"name":name,"muscle":muscle,"submuscle":sub,
                  "type":typ,"level":lvl,"equipment":eqp,
                  "video_url":vid,"image_url":img,"description":desc}
            prof["custom_exercises"].append(ce)
            save_profile(st.session_state.current_profile, prof)
            st.success("Added!")
    with col2:
        themed_header("Existing Custom Exercises")
        exs = prof.get("custom_exercises",[])
        for i,ex in enumerate(exs):
            st.write(f"**{ex['name']}** ({ex['muscle']}–{ex['submuscle']})")
            if st.button("Delete", key=f"del_{i}"):
                exs.pop(i)
                save_profile(st.session_state.current_profile, prof)
                st.experimental_rerun()

# ───── Workout Tab ─────

def render_workout_tab(prof):
    st.header("🏋️ Today's Workout")
    # readiness
    themed_header("🧠 Daily Readiness Check")
    with st.expander("Rate your readiness"):
        sleep = st.slider("Sleep Quality (1–10)",1,10,7)
        stress= st.slider("Stress Level  (1–10)",1,10,4)
        sore = st.slider("Soreness Level(1–10)",1,10,3)
        rpe  = st.slider("RPE (1–10)",        1,10,6)
        st.session_state.auto_adjust = get_auto_adjust_level(sleep,stress,sore,rpe)
        if st.session_state.auto_adjust=="reduce":
            st.warning("⚠️ Scale down intensity today.")
        elif st.session_state.auto_adjust=="boost":
            st.success("✅ Great recovery — you can push a bit harder.")

    # merge built-in + custom
    all_ex = exercise_db + prof.get("custom_exercises",[])
    # filter by equipment
    all_ex = [e for e in all_ex if set(e["equipment"]) & set(prof["equipment"])]
    # plan logic: rotate through muscle groups by least-worked submuscle
    # (for brevity, we pick a random sample)
    import random
    todays = random.sample(all_ex, k=min(6,len(all_ex)))
    # display
    for ex in todays:
        with st.expander(f"**{ex['name']}**  [{ex['type']}]"):
            st.markdown(f"*Muscle:* {ex['muscle']} – {ex['submuscle']}  |  *Lvl:* {ex['level']}  |  *Equip:* {', '.join(ex['equipment'])}")
            st.write(ex["description"])
            if ex.get("video_url"):
                st.video(ex["video_url"])
            if ex.get("image_url"):
                st.image(ex["image_url"], width=300)
            # logging inputs
            sets = prof["settings"].get("warmup") and 5 or 4
            reps = {"Strength":5,"Hypertrophy":10,"Endurance":15,"Recomposition":8}[prof["goal"]]
            suggested = prof["exercise_weights"].get(ex["name"], 10.0)
            st.write(f"**Plan:** {sets} × {reps} @ {suggested} lbs")
            wt = st.number_input("Weight used (lbs)", value=suggested, key=f"wt_{ex['name']}")
            total_vol = 0
            actual_reps=[]
            for s in range(1,sets+1):
                r = st.number_input(f"Reps in set {s}", min_value=0, max_value=reps*2, key=f"r_{ex['name']}_{s}")
                actual_reps.append(r)
                total_vol += calculate_volume(wt,r,1)
                # rest
                if s<sets and st.button(f"Start rest for {prof['settings'].get('rest_interval',60)}s", key=f"rest_{ex['name']}_{s}"):
                    start_rest_timer(prof['settings'].get('rest_interval',60))
            # save log
            if st.button("Save Exercise Log", key=f"log_{ex['name']}"):
                log = load_json(os.path.join(LOGS_DIR,f"{prof['name']}_logs.json"),[])
                entry = {"date":datetime.now().isoformat(),"exercise":ex["name"],
                         "weight":wt,"reps":actual_reps,"volume":total_vol,
                         "adjust":st.session_state.auto_adjust}
                log.append(entry)
                save_json(os.path.join(LOGS_DIR,f"{prof['name']}_logs.json"), log)
                # update progression
                prof["exercise_weights"][ex["name"]] = suggested * (1+ (0.05 if prof["goal"]=="Strength" else 0.025 if prof["goal"]=="Hypertrophy" else 0.01))
                save_profile(prof["name"],prof)
                st.success("Logged!")
            st.write(f"**Volume:** {total_vol:.1f} lbs")

# ───── Progress Tab ─────

def render_progress_tab(prof):
    st.header("📈 Progress & Stats")
    logs = load_json(os.path.join(LOGS_DIR,f"{prof['name']}_logs.json"), [])
    if not logs:
        st.info("No logs yet.")
        return
    # DataFrame
    import pandas as pd
    df = pd.DataFrame(logs)
    # summary charts
    st.subheader("Total Volume by Muscle")
    vol_by_ex = df.groupby("exercise")["volume"].sum()
    fig,ax = plt.subplots()
    vol_by_ex.plot.bar(ax=ax)
    st.pyplot(fig)

    st.subheader("Adjustment Trends (Last 7 Sessions)")
    recent = df.tail(7)
    adj = recent["adjust"].value_counts().reindex(["reduce","none","boost"],fill_value=0)
    fig2,ax2 = plt.subplots()
    adj.plot.bar(color=["orange","gray","green"],ax=ax2)
    st.pyplot(fig2)

    st.subheader("Exercise Trends")
    ex_choice = st.selectbox("Select exercise", vol_by_ex.index)
    sub = df[df["exercise"]==ex_choice]
    fig3,ax3=plt.subplots()
    ax3.plot(pd.to_datetime(sub["date"]).dt.date, sub["weight"], marker="o")
    ax3.set_title(f"{ex_choice} Weight Over Time")
    st.pyplot(fig3)

# ───── Cycle Planner Tab ─────

def render_cycle_planner_tab(prof):
    st.header("📆 Cycle Planner")
    st.info("Under development: design multi-week phases, deload weeks, progression schemes.")

# ───── Settings Tab ─────

def render_settings_tab(prof):
    st.header("⚙️ Settings")
    s = prof["settings"]
    s["theme"] = st.selectbox("Theme", ["Light","Dark","Minimal"], index=["Light","Dark","Minimal"].index(s.get("theme","Light")))
    s["coaching"] = st.checkbox("Show AI tips", value=s.get("coaching",True))
    s["warmup"]   = st.checkbox("Include Warm-up Sets", value=s.get("warmup",True))
    s["rest_interval"] = st.slider("Default Rest (s)", 30,180,s.get("rest_interval",60))
    if st.button("Save Settings"):
        prof["settings"] = s
        save_profile(prof["name"],prof)
        st.success("Settings saved.")

# ───── Main ─────

ensure_session_state()
render_profile_tab()

if st.session_state.current_profile:
    prof = load_profile(st.session_state.current_profile)
    tabs = st.tabs(["Profile","My Exercises","Workout","Progress","Cycle Planner","Settings"])
    with tabs[0]:
        st.write(f"**Name:** {prof['name']}  |  **Goal:** {prof['goal']}  |  **Equipment:** {', '.join(prof['equipment'])}")
    with tabs[1]:
        render_my_exercises_tab(prof)
    with tabs[2]:
        render_workout_tab(prof)
    with tabs[3]:
        render_progress_tab(prof)
    with tabs[4]:
        render_cycle_planner_tab(prof)
    with tabs[5]:
        render_settings_tab(prof)
